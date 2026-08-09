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
docker-compose up --build
```

3. Access:
- Web UI: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Services

- **api**: FastAPI backend (port 8000)
- **web**: Next.js frontend (port 3000)

## Data Persistence

Data is stored in Docker volumes:
- `api-data`: Database and ChromaDB
- `repos-data`: Cloned repositories
