# CodebaseQA

<div align="center">

**AI-Powered Codebase Understanding**

Understand any GitHub repository in minutes with natural language Q&A.

[Getting Started](#getting-started) • [Features](#features) • [Documentation](#documentation)

</div>

---

## ✨ Features

- 🔍 **Natural Language Q&A** - Ask questions about any codebase in plain English
- 🔎 **Semantic Code Search** - Find code using natural language, not just keywords
- 📚 **Learning Paths** - AI-generated guided tours through codebases
- 🏠 **Self-Hostable** - Run entirely on your own infrastructure
- 🔐 **BYOK** - Bring your own API keys (OpenAI, Anthropic, etc.)

## 🏗️ Architecture

```
codebaseqa/
├── apps/
│   ├── api/          # FastAPI backend (Python)
│   └── web/          # Next.js frontend (TypeScript)
├── cli/              # Command-line interface
├── docker/           # Docker deployment
└── packages/         # Shared packages
```

## 🚀 Getting Started

### Prerequisites

- Docker Desktop (recommended)
- OR: Node.js 20+ and Python 3.11+ for local dev

### Quick Start (Docker)

The easiest way to run CodebaseQA is with Docker:

```bash
# 1. Access the project
git clone https://github.com/your-username/codebaseqa.git
cd codebaseqa

# 2. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Start the application
./scripts/start-docker.sh
```

- Web UI: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Local Development

1. **Start the API:**
```bash
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

2. **Start the Frontend:**
```bash
cd apps/web
pnpm install
pnpm dev
```

## 📖 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/repos/` | POST | Index a repository |
| `/api/repos/` | GET | List repositories |
| `/api/repos/{id}` | GET | Get repository details |
| `/api/chat/sessions` | POST | Create chat session |
| `/api/search/` | POST | Semantic code search |

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 16, React 19, Tailwind CSS |
| Backend | FastAPI, Python 3.11+ |
| Parsing | Tree-sitter (Python, JS, TS, Go, etc.) |
| Vector Store | ChromaDB (Local/Docker) |
| LLM | OpenAI GPT-4o |
| Database | SQLite |

## 🔧 Configuration

All configuration via environment variables (`.env`):

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Required for embeddings and chat |
| `DATABASE_URL` | SQLite path (default: `sqlite:///./data/codebaseqa.db`) |
| `CHROMA_PERSIST_DIRECTORY` | Vector store path |
| `GITHUB_TOKEN` | Optional, for private repos |

## 📝 License

MIT