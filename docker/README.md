# Docker Deployment

## Quick Start

1. Create a `.env` file **in this directory** (`docker/.env`). Compose expands
   `${VAR}` from the file next to `docker-compose.yml`; a `.env` at the repo root is
   not used for that. See `.env.example` for the full set of supported variables.
```bash
OPENAI_API_KEY=sk-...
# optional: switch providers, clone private repos
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# GITHUB_TOKEN=ghp_...
```

2. Build and run:
```bash
docker compose up --build
```

3. Access:
- Web UI: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Services

- **api**: FastAPI backend (port 8000)
- **web**: Next.js frontend (port 3000)
- **redis**: cache and rate-limit backend (port 6379). `api` declares
  `depends_on: redis`, so it is not optional under compose.

Note that redis is published on 6379 with no password. That is fine on a laptop;
do not expose it on a shared or public host.

## Data Persistence

The `api` service **bind-mounts** the repo's `data/` directory:

```
../data  ->  /app/data
```

So the SQLite database, the ChromaDB directory and every cloned repository live in
`data/` in your working tree, not in a Docker-managed volume, and they survive
`docker compose down`. Two consequences worth knowing:

- The container runs as root, so files it creates under `data/` are root-owned on
  the host.
- `docker-compose.yml` also declares a named volume `data:` that nothing mounts.
  It has no effect; the bind mount above is what is actually used.

## Optional: Neo4j graph read model

Off by default. `code_dependencies` in SQLite stays authoritative; Neo4j is a projection
rebuilt at index time, and every read falls back to SQL if Neo4j is unreachable — so
turning this on cannot take the graph endpoint down.

```bash
docker compose up -d neo4j
# then in docker/.env
NEO4J_ENABLED=true
NEO4J_PASSWORD=<something>
```

Re-index a repository to populate it, then browse at http://localhost:7474.

The Cypher in this store is exercised against a real server by
apps/api/tests/integration/test_neo4j_live.py, which skips unless you point it at one:

```bash
docker run -d -p 7688:7687 -e NEO4J_AUTH=neo4j/verifypassword neo4j:5-community
NEO4J_TEST_URI=bolt://localhost:7688 NEO4J_TEST_PASSWORD=verifypassword pytest tests
```

Worth running after any change to neo4j_store.py: the fake-driver unit tests cannot catch
Cypher the server rejects, which is how a broken delete query once shipped green.

To confirm the projection matches SQL:

```cypher
MATCH (f:File {repo_id: $repo}) RETURN count(f);
MATCH (:File {repo_id: $repo})-[r:IMPORTS]->(:File) RETURN count(r);
```

Those two counts should equal `SELECT count(*) FROM code_files` and
`SELECT count(*) FROM code_dependencies` for the same repository.

**Do not point this at AuraDB Free for anything public.** A Free instance auto-pauses
after 72 hours idle, and a paused instance's hostname stops resolving — so the graph
would silently fall back to SQL until someone resumes it by hand. Free instances are
deleted after 30 days paused.

Degree and centrality use Cypher `COUNT {}` subqueries rather than Graph Data Science:
the in-database GDS plugin requires AuraDB Professional or above, and Aura Graph
Analytics sessions are an offline batch shape (2GB, one concurrent session, 30-minute
TTL) that does not fit a synchronous request.

## Using Azure OpenAI

Set these in `docker/.env` (compose forwards all of them):

```bash
LLM_PROVIDER=azure_openai
EMBEDDING_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=my-gpt4o-deployment
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=my-embedding-deployment
AZURE_OPENAI_TOKENIZER_MODEL=text-embedding-3-small
# match your deployed embedding model: 3-small is 1536, 3-large is 3072
OPENAI_EMBEDDING_DIMENSIONS=1536
```

Two Azure-specific gotchas, both handled but worth understanding:

- **Deployment names, not model ids.** Azure sends the deployment name where a model
  id normally goes, so `AZURE_OPENAI_DEPLOYMENT` is what reaches the API as `model`.
- **`/models` lists deployments.** Some Azure configurations do not expose that route
  at all. `/api/health` treats a 404 there as reachable (the endpoint answered) while
  still failing on 401/403, so a working deployment is not reported as down.

Authentication is API-key only. Entra ID / managed identity is not wired up — the
client accepts a callable token provider, but nothing here supplies one.

## Using Ollama from inside Docker

`OLLAMA_BASE_URL` defaults to `http://localhost:11434`, which is correct when you
run the API directly on your machine but **wrong inside a container** — there,
`localhost` is the container itself, not your host. If you set
`LLM_PROVIDER=ollama` or `EMBEDDING_PROVIDER=ollama` in `docker/.env`, also set:

```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

On Docker Desktop (macOS/Windows) that name resolves automatically. On Linux it
does not unless you add it to the `api` service:

```yaml
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Also pull the model first (`ollama pull nomic-embed-text`) — a missing model now
fails fast with a clear error rather than embedding your whole repository as zero
vectors.
