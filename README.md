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

- Node.js 20+
- Python 3.11+
- pnpm
- OpenAI API key

### Quick Start

1. **Clone and install:**
```bash
git clone https://github.com/your-username/codebaseqa.git
cd codebaseqa
pnpm install
```

2. **Set up environment:**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. **Start the API:**
```bash
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

4. **Start the frontend:**
```bash
cd apps/web
pnpm dev
```

5. **Open http://localhost:3000**

### Using Docker

```bash
cd docker
cp ../.env.example .env
# Edit .env with your API key
docker-compose up --build
```

## 🖥️ CLI Usage

```bash
cd cli
pip install -e .

# Index a repository
codebaseqa index https://github.com/expressjs/express

# List indexed repos
codebaseqa list

# Ask a question
codebaseqa ask <repo_id> "What is the main entry point?"

# Search code
codebaseqa search <repo_id> "middleware"
```

## 📖 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/repos/` | POST | Index a repository |
| `/api/repos/` | GET | List repositories |
| `/api/repos/{id}` | GET | Get repository details |
| `/api/repos/{id}` | DELETE | Delete repository |
| `/api/chat/sessions` | POST | Create chat session |
| `/api/chat/sessions/{id}/messages` | POST | Send message (SSE) |
| `/api/search/` | POST | Semantic code search |
| `/health` | GET | Health check |

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 16, React 19, Tailwind CSS |
| Backend | FastAPI, Python 3.11+ |
| Code Parsing | Tree-sitter (Python, JS, TS) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector Store | ChromaDB |
| LLM | OpenAI GPT-4o |
| Database | SQLite (SQLAlchemy) |

## 🔧 Configuration

All configuration via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `DATABASE_URL` | Database connection | `sqlite:///./data/codebaseqa.db` |
| `VECTOR_DB_TYPE` | Vector store type | `chroma` |
| `LLM_PROVIDER` | LLM provider | `openai` |
| `GITHUB_TOKEN` | For private repos | Optional |

## 📝 License

MIT