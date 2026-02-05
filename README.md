# CodebaseQA

<div align="center">

**AI-Powered Codebase Understanding & Learning Platform**

![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat&logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=nextdotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)

[Demo](#demo) • [Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Author](#author)

</div>

---

## Demo

<!-- TODO: Add a demo GIF here -->
<!-- Record with Loom, Kap, or similar and add: -->
<!-- ![CodebaseQA Demo](./docs/demo.gif) -->

> **Coming Soon:** Demo video showing the full workflow

---

## What is CodebaseQA?

CodebaseQA helps developers **understand unfamiliar codebases in minutes, not days**. 

Point it at any GitHub repository and get:
- **Natural Language Q&A** - Ask questions in plain English, get answers with code references
- **AI-Generated Learning Paths** - Personalized courses based on your role (New Hire, Auditor, Architect)
- **Interactive Dependency Graphs** - Visualize how components connect
- **Gamified Learning** - XP, achievements, and streaks to keep you motivated

Perfect for onboarding, code reviews, or exploring open-source projects.

---

## Features

| Feature | Description |
|---------|-------------|
| **Chat Q&A** | RAG-powered chat with query expansion and LLM reranking |
| **Semantic Search** | Hybrid search combining vector similarity + keyword matching |
| **Learning Paths** | 4 personas: New Hire, Security Auditor, Full Stack Dev, Archaeologist |
| **Interactive Lessons** | Markdown content, code references, Mermaid diagrams |
| **Quizzes & Challenges** | Bug hunt, code trace, fill-in-the-blank exercises |
| **Gamification** | XP system, 6 levels, streaks, 15+ achievements |
| **Dependency Graph** | Interactive visualization with hierarchy, radial, and tree layouts |
| **CLI Tool** | Terminal-based workflow for power users |
| **CodeTour Export** | Export lessons as VS Code CodeTour files |

---

## Quick Start

### Prerequisites

- Docker Desktop (recommended)
- OR: Node.js 20+ and Python 3.11+ for local dev
- OpenAI API key

### One-Command Setup (Docker)

```bash
# Clone the repository
git clone https://github.com/ShreeBohara/codebaseqa.git
cd codebaseqa

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start the application
./scripts/start-docker.sh
```

- **Web UI:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

### Local Development

```bash
# Terminal 1: Start the API
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload

# Terminal 2: Start the Frontend
cd apps/web
pnpm install
pnpm dev
```

---

## Architecture

```
codebaseqa/
├── apps/
│   ├── api/          # FastAPI backend (Python)
│   │   ├── src/
│   │   │   ├── core/         # RAG pipeline, embeddings, LLM
│   │   │   ├── services/     # Indexing, learning, gamification
│   │   │   └── api/routes/   # REST endpoints
│   │   └── tests/
│   └── web/          # Next.js frontend (TypeScript)
│       └── src/
│           ├── app/          # Pages and routing
│           ├── components/   # React components
│           └── lib/          # API client, utilities
├── cli/              # Command-line interface
├── docker/           # Docker deployment
└── docs/             # Documentation
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 16, React 19, TailwindCSS, Framer Motion, xyflow |
| **Backend** | FastAPI, Python 3.11, SQLAlchemy |
| **Code Parsing** | Tree-sitter (Python, JavaScript, TypeScript) |
| **Vector Store** | ChromaDB with hybrid search |
| **LLM** | OpenAI GPT-4o (BYOK - Bring Your Own Key) |
| **Database** | SQLite (easy setup, no external deps) |

### Architecture Highlights

1. **RAG Pipeline with Query Expansion**
   - Expands user queries with synonyms and related terms
   - Multi-query retrieval for better coverage
   - LLM-based reranking for precision

2. **Semantic Code Parsing**
   - Tree-sitter for AST-based chunking (not regex!)
   - Preserves function/class boundaries
   - Extracts docstrings and signatures

3. **Hybrid Search Strategy**
   - Vector similarity for semantic understanding
   - Keyword matching for exact variable names
   - Best of both worlds for code search

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/repos/` | POST | Index a GitHub repository |
| `/api/repos/` | GET | List all repositories |
| `/api/repos/{id}` | GET | Get repository details |
| `/api/chat/sessions` | POST | Create a chat session |
| `/api/chat/sessions/{id}/messages` | POST | Send message (streaming) |
| `/api/search/` | POST | Semantic code search |
| `/api/learning/{repo_id}/curriculum` | POST | Generate learning syllabus |
| `/api/learning/{repo_id}/lessons/{id}` | POST | Generate lesson content |

---

## Configuration

All configuration via environment variables (`.env`):

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `DATABASE_URL` | SQLite path | No (default: `sqlite:///./data/codebaseqa.db`) |
| `CHROMA_PERSIST_DIRECTORY` | Vector store path | No (default: `./data/chroma`) |
| `GITHUB_TOKEN` | For private repositories | No |

---

## CLI Usage

```bash
# Install CLI
cd cli && pip install -e .

# Index a repository
codebaseqa index https://github.com/expressjs/express

# Ask a question
codebaseqa ask <repo-id> "What is the main entry point?"

# Search code
codebaseqa search <repo-id> "authentication middleware"

# List repositories
codebaseqa list

# Export lesson as CodeTour
codebaseqa export-tour <repo-id> <lesson-id>
```

---

## Limitations & Recommended Repos

### Current Limitations

This project is optimized for **small to medium repositories** (under 500 files). Large repos like React, Next.js, or FastAPI may:
- Take a long time to index
- Hit OpenAI API token limits
- Use significant API credits

### Recommended Test Repositories

| Repository | Files | Description |
|------------|-------|-------------|
| `tiangolo/sqlmodel` | ~50 | SQL + Pydantic models |
| `pallets/click` | ~40 | CLI framework |
| `encode/starlette` | ~80 | ASGI framework |
| `psf/requests` | ~60 | HTTP library |
| `expressjs/express` | ~100 | Node.js web framework |

### Future Improvements

- [ ] **Smart file filtering** - Skip tests, docs, and examples
- [ ] **Subdirectory indexing** - Only index `src/` or specific folders
- [ ] **Incremental indexing** - Only re-index changed files
- [ ] **File prioritization** - Focus on entry points and core modules
- [ ] **Streaming embeddings** - Process in smaller batches for large repos
- [ ] **Multiple LLM providers** - Support Anthropic, local models (Ollama)

---

## Author

**Shree Bohara**

- GitHub: [@ShreeBohara](https://github.com/ShreeBohara)
- LinkedIn: [ShreeBohara](https://linkedin.com/in/ShreeBohara)

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**If you find this useful, please give it a star!**

</div>
