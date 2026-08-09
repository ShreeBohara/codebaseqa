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
