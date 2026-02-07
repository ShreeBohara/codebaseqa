# CodebaseQA

<div align="center">

**AI-Powered Codebase Understanding & Learning Platform**

![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat&logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=nextdotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)

[Features](#features) • [Quick Start](#quick-start) • [Configuration](#configuration) • [API](#api-endpoints) • [CLI](#cli-usage)

</div>

---

## What is CodebaseQA?

CodebaseQA helps developers understand unfamiliar repositories quickly with:

- **Chat Q&A over real code context** (RAG + source citations)
- **Learning paths** tailored by persona
- **Interactive lessons** with file-linked references and Mermaid diagrams
- **Quizzes and coding challenges** (bug hunt, code trace, fill-in-the-blank)
- **Gamification** (XP, levels, streaks, achievements, activity heatmap)
- **Dependency graph visualization** with multiple layouts and PNG export

It supports both a web UI and a CLI workflow.

---

## Features

| Feature | Description |
|---------|-------------|
| **Repository Indexing** | Clone/index GitHub repos with progress states (pending, cloning, parsing, embedding, completed, failed) |
| **RAG Chat** | Streaming responses with query expansion, hybrid retrieval, and source snippets |
| **Semantic Search** | Vector + keyword hybrid search with language/file filters |
| **Learning Personas** | New Hire, Security Auditor, Full Stack Dev, Archaeologist |
| **Lesson Generation** | AI-generated lesson markdown, code references, optional Mermaid diagram |
| **Quiz Generation** | Lesson-based multiple-choice quizzes |
| **Challenges** | Bug Hunt, Code Trace, Fill-in-the-Blank generation + validation |
| **Gamification** | XP rewards, 6 levels, streak tracking, achievements, dashboard analytics |
| **Dependency Graph** | Interactive graph with hierarchy/radial/tree layouts, search, regenerate, PNG export |
| **CodeTour Export** | Export lesson content as VS Code CodeTour (`.tour`) |
| **CLI Tooling** | Index, ask, search, list, lessons, and CodeTour export from terminal |
| **Demo Bootstrap** | Seed a demo repository via API/UI (`/api/repos/demo/seed`) |

---

## Quick Start

### Prerequisites

- Docker Desktop (recommended for fastest setup)
- Or local dev: Node.js 20+ and Python 3.11+
- At least one supported LLM provider (OpenAI, Anthropic, or Ollama)

### Docker Setup

```bash
git clone https://github.com/ShreeBohara/codebaseqa.git
cd codebaseqa
cp .env.example .env
# Edit .env and add provider credentials (typically OPENAI_API_KEY)

./scripts/start-docker.sh
# Optional demo seed:
# ./scripts/start-docker.sh --with-demo
```

Endpoints after startup:

- Web UI: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Local Development

```bash
# Install JS workspace deps once (from repo root)
pnpm install

# Terminal 1: API
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload

# Terminal 2: Web
cd apps/web
pnpm dev
```

---

## Configuration

CodebaseQA reads settings from environment variables (via `apps/api/src/config.py`).

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite:///./data/codebaseqa.db` |
| `CHROMA_PERSIST_DIR` | Chroma storage path | `./data/chroma` |
| `REPOS_DIR` | Cloned repository cache path | `./data/repos` |
| `GITHUB_TOKEN` | Needed for private repos / higher API limits | unset |
| `MAX_FILES_PER_REPO` | Indexing cap per repository | `5000` |
| `MAX_FILE_SIZE_KB` | Skip files larger than this | `500` |
| `DEBUG` | API debug mode | `false` |

### LLM & Embeddings

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | `openai`, `anthropic`, or `ollama` | `openai` |
| `EMBEDDING_PROVIDER` | `openai` or `ollama` | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | unset |
| `OPENAI_MODEL` | OpenAI chat model | `gpt-4o` |
| `OPENAI_EMBEDDING_MODEL` | OpenAI embedding model | `text-embedding-3-small` |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint override | unset |
| `ANTHROPIC_API_KEY` | Anthropic API key | unset |
| `ANTHROPIC_MODEL` | Anthropic model | `claude-sonnet-4-20250514` |
| `OLLAMA_BASE_URL` | Ollama host URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama generation model | `llama3.1` |
| `LOCAL_EMBEDDING_MODEL` | Ollama embedding model name | `nomic-ai/nomic-embed-text-v1.5` |

Notes:

- Docker compose currently passes `OPENAI_API_KEY` by default; if you want Anthropic/Ollama in Docker, add those env vars in `docker/docker-compose.yml`.
- For local development, all variables above can be set directly in your shell or `.env`.

---

## API Endpoints

### Repository & Indexing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/repos/` | Add repository and start background indexing |
| `GET` | `/api/repos/` | List repositories |
| `GET` | `/api/repos/{repo_id}` | Get repository details |
| `GET` | `/api/repos/{repo_id}/progress` | Stream indexing progress (SSE) |
| `DELETE` | `/api/repos/{repo_id}` | Delete repository and indexed data |
| `GET` | `/api/repos/{repo_id}/files/content` | Fetch file content by `path` query param |
| `POST` | `/api/repos/demo/seed` | Seed demo repository |

### Chat & Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat/sessions` | Create chat session |
| `GET` | `/api/chat/sessions/{session_id}` | Get session + messages |
| `POST` | `/api/chat/sessions/{session_id}/messages` | Stream assistant response (SSE) |
| `POST` | `/api/search/` | Hybrid semantic code search |

### Learning, Graph, Gamification, Challenges

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/learning/personas` | List available personas |
| `POST` | `/api/learning/{repo_id}/curriculum` | Generate syllabus |
| `POST` | `/api/learning/{repo_id}/lessons/{lesson_id}` | Generate lesson content |
| `POST` | `/api/learning/{repo_id}/lessons/{lesson_id}/quiz` | Generate quiz |
| `GET` | `/api/learning/{repo_id}/lessons/{lesson_id}/export/codetour` | Export lesson as CodeTour |
| `GET` | `/api/learning/{repo_id}/graph` | Generate dependency graph |
| `GET` | `/api/learning/{repo_id}/stats` | User XP/level/streak stats |
| `GET` | `/api/learning/{repo_id}/activity` | Activity heatmap data |
| `GET` | `/api/learning/{repo_id}/achievements` | Achievement list + unlock status |
| `GET` | `/api/learning/{repo_id}/progress` | Completed lessons |
| `POST` | `/api/learning/{repo_id}/lessons/{lesson_id}/complete` | Mark lesson complete + award XP |
| `POST` | `/api/learning/{repo_id}/lessons/{lesson_id}/quiz/result` | Submit quiz result + award XP |
| `POST` | `/api/learning/{repo_id}/challenges/complete` | Record challenge completion + award XP |
| `POST` | `/api/learning/{repo_id}/graph/viewed` | Record graph view event |
| `POST` | `/api/learning/{repo_id}/lessons/{lesson_id}/challenge` | Generate challenge |
| `POST` | `/api/learning/{repo_id}/challenges/validate/bug_hunt` | Validate bug hunt answer |
| `POST` | `/api/learning/{repo_id}/challenges/validate/code_trace` | Validate code trace answer |
| `POST` | `/api/learning/{repo_id}/challenges/validate/fill_blank` | Validate fill-blank answer |

### Platform Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health + dependency checks |
| `GET` | `/openapi.json` | OpenAPI JSON |
| `GET` | `/openapi.yaml` | OpenAPI YAML |
| `GET` | `/api/cache/stats` | LLM cache statistics |

---

## CLI Usage

Install:

```bash
cd cli
pip install -e .
```

Commands:

```bash
# Index repository
codebaseqa index https://github.com/expressjs/express

# List repositories
codebaseqa list

# Ask a question
codebaseqa ask <repo_id> "What is the main entry point?"

# Search code
codebaseqa search <repo_id> "authentication middleware"

# List generated lessons (default persona: new_hire)
codebaseqa lessons <repo_id>

# Export lesson as VS Code CodeTour
codebaseqa export-tour <repo_id> <lesson_id>
```

---

## Architecture (Monorepo)

```text
codebaseqa/
├── apps/
│   ├── api/        # FastAPI backend (RAG, indexing, learning, gamification)
│   └── web/        # Next.js frontend UI
├── cli/            # Python CLI client
├── docker/         # Dockerfiles + compose + entrypoint
├── docs/           # Architecture and design notes
└── scripts/        # Local helper scripts
```

Backend highlights:

- Tree-sitter semantic parsing for Python, JavaScript, TypeScript, Java
- Hybrid retrieval (vector + keyword) and query expansion
- LLM-based reranking for improved relevance
- SQLite metadata + Chroma vector persistence

---

## Testing & Checks

Backend:

```bash
cd apps/api
pytest tests/unit tests/integration
ruff check src tests
```

Frontend:

```bash
cd apps/web
pnpm lint
pnpm type-check
pnpm test
```

Workspace shortcuts:

```bash
pnpm lint
pnpm test
pnpm type-check
```

---

## Current Limitations

- Very large repositories can still be slow/expensive to index depending on provider/model choice.
- Lesson/challenge/graph generation quality depends on model capability and retrieved context.
- Docker setup is optimized for OpenAI defaults unless extra provider vars are explicitly wired.

---

## Author

**Shree Bohara**

- GitHub: [@ShreeBohara](https://github.com/ShreeBohara)
- LinkedIn: [ShreeBohara](https://linkedin.com/in/ShreeBohara)

---

## License

MIT
