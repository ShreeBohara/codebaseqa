# CodebaseQA Deep Technical Documentation

Generated on: 2026-02-15
Repository root: `/Users/shree/Desktop/codebaseqa`
Scope: Full repository analysis (architecture, every feature, core logic paths, deployment/tooling, and file-by-file appendix)

---

## 1) Purpose of This Document

This document is an end-to-end technical breakdown of the CodebaseQA monorepo. It is intentionally larger and deeper than `README.md` and is written to help you or any maintainer understand:

- What each major subsystem does.
- How requests flow from frontend to backend and back.
- How data is indexed, stored, retrieved, and rendered.
- How learning, graphing, gamification, and challenge systems work internally.
- Which files are responsible for which behavior.
- How to reason about deployment, CI, tests, and risk points.

---

## 2) Repository Snapshot

### 2.1 File and Codebase Size

- Total tracked files: 207
- README size: 451 lines
- Largest backend file: `apps/api/src/services/learning_service.py` (2360 lines)
- Largest frontend file: `apps/web/src/components/learning/graph-view.tsx` (908 lines)
- API client size: `apps/web/src/lib/api-client.ts` (769 lines)

### 2.2 Major Folder Line Counts

- `apps/api`: 17,737 lines
- `apps/web`: 16,561 lines
- `cli`: 406 lines
- `docs`: 38,631 lines (includes many media assets counted by line utility)
- `docker`: 192 lines
- `scripts`: 172 lines
- root-level files: 8,341 lines

### 2.3 High-Level Monorepo Layout

- `apps/api`: FastAPI backend (indexing, RAG chat, search, learning engine, graph generation, gamification)
- `apps/web`: Next.js frontend (landing, repo management, chat UI, learning workspace, dependency graph explorer)
- `cli`: Python terminal client
- `docker`: local containerized deployment
- `docs`: architecture, release notes, and media assets
- `scripts`: utility scripts (prewarm, CSS verification, docker startup)

---

## 3) Deployment and Runtime Topology

You mentioned FE is deployed to Vercel and BE to Render. The code structure supports exactly this split.

### 3.1 Frontend (Vercel)

- Framework: Next.js 16 + React 19 (`apps/web/package.json`)
- Runtime API target: `NEXT_PUBLIC_API_URL`
- Vercel config: `apps/web/vercel.json`
- Build characteristics:
  - standalone output enabled (`apps/web/next.config.ts`)
  - transpiles `lucide-react`

### 3.2 Backend (Render)

- Framework: FastAPI + Uvicorn (`apps/api/src/main.py`)
- Key dependencies:
  - SQLAlchemy for relational metadata
  - ChromaDB for embeddings
  - provider adapters for OpenAI / Anthropic / Ollama
- Environment-driven settings via Pydantic settings (`apps/api/src/config.py`)

### 3.3 Data Stores and Persistence

- Relational metadata:
  - default SQLite (`DATABASE_URL=sqlite:///./data/codebaseqa.db`)
  - holds repositories, files, chunks metadata, chat sessions/messages, learning caches, progress, XP, achievements, graph interactions
- Vector store:
  - Chroma persistent directory (`CHROMA_PERSIST_DIR`)
- Optional Redis:
  - distributed cache and rate limiting (fallback to in-memory if unavailable)

### 3.4 Runtime Startup Sequence

Implemented in FastAPI lifespan (`apps/api/src/main.py`):

1. Ensure data folders exist (`./data`, chroma path, repos path)
2. Initialize DB tables
3. Apply additive runtime migrations
4. Initialize vector store
5. Register routes and middleware
6. Serve API/docs/health endpoints

---

## 4) End-to-End Product Flows

## 4.1 Repository Import and Indexing

Main flow:

1. UI/CLI calls `POST /api/repos/`
2. Backend validates URL and checks duplicates
3. Background task starts indexing
4. Indexing service clones repo, scans files, parses/chunks, embeds, stores vectors
5. Repo status transitions from `pending` -> `cloning` -> `parsing` -> `embedding` -> `completed`

Core code:

- route orchestration: `apps/api/src/api/routes/repos.py`
- cloning/security/path access: `apps/api/src/core/github/repo_manager.py`
- parsing engine: `apps/api/src/core/parser/tree_sitter_parser.py`
- indexing pipeline: `apps/api/src/services/indexing_service.py`
- embedding/vector write: `apps/api/src/core/embeddings/*`, `apps/api/src/core/vectorstore/chroma_store.py`

Important implementation details:

- Full reindex is destructive-per-repo at start: stale SQL chunks/files and vector collection are cleared.
- Parser fallback strategy:
  - if no parser exists for a file type, raw indexing is used.
  - if parser throws, raw indexing is also used.
- Markdown is chunked by headings for better semantic recall.
- “Important files” (README/config/entry files) get additional `file_summary` chunks to improve retrieval quality.
- Trivial re-export summaries are filtered out to avoid polluting retrieval.

## 4.2 Chat Q&A (Streaming SSE)

Main flow:

1. UI creates session (`POST /api/chat/sessions`)
2. UI sends message (`POST /api/chat/sessions/{id}/messages`)
3. Backend persists user message, builds bounded history
4. RAG retrieve phase runs (intent + profile + expanded queries + hybrid search + optional rerank)
5. SSE emits event sequence:
   - `sources`
   - `meta` (if enabled)
   - multiple `content` chunks
   - `done`
6. Assistant response and retrieval metadata are persisted in DB

Core code:

- endpoint and SSE envelope: `apps/api/src/api/routes/chat.py`
- retrieval/generation pipeline: `apps/api/src/core/rag/pipeline.py`
- retrieval cache + answer cache: `apps/api/src/core/cache/chat_cache.py`
- provider adapters: `apps/api/src/core/llm/*`

Chat hardening features:

- per-repository semaphore to cap concurrent generations
- request timeout guard (`asyncio.timeout`)
- bounded history by message count + token approximation
- optional intent tiebreak via LLM
- docs-first profile for overview questions
- optional content reranking prompt over candidate chunks
- answer caching keyed by repo + intent + top chunk IDs + model

## 4.3 Semantic Search

Main flow:

1. UI calls `POST /api/search/`
2. Backend embeds query
3. Runs hybrid search in vector store
4. Applies optional language/file filters
5. Returns scored snippets with line ranges

Core code:

- route: `apps/api/src/api/routes/search.py`
- hybrid scoring: `apps/api/src/core/vectorstore/chroma_store.py`

Scoring logic combines:

- vector similarity
- keyword overlap
- file-path term match
- intent/profile-specific boosts (docs, manifest, location, error)
- penalties for trivial chunks

## 4.4 Learning Track and Lesson Generation

Main flow:

1. Persona list loaded (`GET /api/learning/personas`)
2. Curriculum generated (`POST/GET /api/learning/{repo_id}/curriculum`)
3. Lesson generated (`POST/GET /api/learning/{repo_id}/lessons/{lesson_id}`)
4. Quiz/challenge generated from lesson context
5. User progress and XP updated on completion endpoints

Core code:

- learning routes: `apps/api/src/api/routes/learning.py`
- learning logic (v1 + v2, caching, quality gates): `apps/api/src/services/learning_service.py`
- DB caches: `LearningSyllabus`, `LearningLesson`

Learning v2 characteristics:

- persona blueprints define retrieval query, tone, mission, pillar topics, relevance terms
- curriculum output validation enforces:
  - exactly 4 modules
  - lesson counts
  - unique lesson IDs
  - persona relevance threshold
- lesson output validation enforces:
  - required section headings
  - persona-term score threshold
  - minimum code references when files are available
- fallback content is generated when JSON/quality checks fail
- cached payloads include `cache_info` metadata and optional `quality_meta`

## 4.5 Dependency Graph (Graph v2/v2.1 behavior)

Main flow:

1. UI requests graph with query params: `granularity`, `scope`, `focus_node`, `hops`
2. Backend builds deterministic file graph from code imports and file inventory
3. Applies metrics/ranking/pruning/budgeting
4. Optionally aggregates to module graph in dense contexts
5. Returns nodes, edges, and rich `meta` object
6. Frontend renders with React Flow and local filtering/focus interactions

Core backend code:

- graph generation engine: `apps/api/src/services/learning_service.py` (`generate_graph` and helper suite)

Core frontend code:

- orchestrator: `apps/web/src/components/learning/graph-view.tsx`
- node visuals: `apps/web/src/components/learning/graph/CustomNode.tsx`
- edge visuals: `apps/web/src/components/learning/graph/CustomEdge.tsx`
- layout engine (ELK -> Dagre fallback): `apps/web/src/components/learning/graph/graph-layouts.ts`

Graph quality controls (backend):

- deterministic extraction from import patterns
- module key derivation and connectivity summaries
- adaptive recommended view (`file` vs `module`) by node/edge thresholds + cross-module signal
- scoped subgraph extraction by module
- focused neighborhood extraction by node and hops
- per-node edge budget and max edge caps
- optional orphan filtering
- short-lived in-memory graph cache with bounded entries

Graph UX controls (frontend):

- view switch (`file`/`module`) with dense-mode guard
- focus mode (`1-hop`/`2-hop`)
- zoom-sensitive edge budget
- type filters with legend
- minimap toggle
- node inspector panel with source preview and relationship lists
- export PNG via `html-to-image`

## 4.6 Challenges and Validation

Challenge types:

- bug hunt
- code trace
- fill in the blank

Generation flow:

- endpoint: `POST /api/learning/{repo}/lessons/{lesson}/challenge`
- generated by `ChallengeService`
- if no LLM or parsing fails, mock challenge payload is returned

Validation flow:

- dedicated endpoints per challenge type
- challenge answer checked server-side
- XP awarded only on correct responses
- hint usage affects “perfect” status and XP path

Core code:

- `apps/api/src/services/challenges.py`
- validation routes in `apps/api/src/api/routes/learning.py`

## 4.7 Gamification and Progress

Data tracked:

- total XP
- level
- streak and longest streak
- lessons/quizzes/challenges stats
- perfect quizzes
- unlocked achievements
- activity history

Core code:

- service: `apps/api/src/services/gamification.py`
- tables: `UserXP`, `LessonProgress`, `Achievement`, `GraphNodeInteraction`
- endpoints under `/api/learning/{repo_id}/...`

Behavior highlights:

- streak-aware bonus on selected reward types
- repeated lesson completion guarded against duplicate XP
- achievement unlocking can cascade via threshold checks
- graph exploration achievements unlocked by unique node count

## 4.8 Demo Mode and Public Guardrails

Core code:

- demo gating: `apps/api/src/core/demo_mode.py`
- soft throttling: `apps/api/src/core/rate_limit.py`

Demo mode behaviors:

- single featured repository access
- optional mutation lock (import/delete blocked)
- optional busy mode (503)
- per-bucket soft rate limits with `Retry-After`
- Redis-backed limiter when configured, memory fallback otherwise

---

## 5) Backend Deep Dive

## 5.1 Configuration Layer

File: `apps/api/src/config.py`

What it controls:

- provider selection (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`)
- provider-specific timeouts, retries, embedding batch/rate controls
- graph v2/v2.1/v2.2 feature and threshold flags
- learning v2 feature flags and cache TTL
- demo mode policy and traffic knobs
- chat retrieval/rerank/caching/timeout/concurrency knobs

Key design choice:

- `Settings` is centralized and cached via `lru_cache` so modules can read one source of truth.

## 5.2 Main App and Lifespan

File: `apps/api/src/main.py`

Responsibilities:

- app creation + CORS middleware
- router registration (`repos`, `chat`, `search`, `learning`, `platform`)
- startup/shutdown resource lifecycle
- health endpoint with checks for DB/vector/LLM/GitHub/demo repo readiness
- OpenAPI JSON/YAML endpoints
- cache/rate-limit stats endpoint
- global exception fallback

## 5.3 Dependency Injection

File: `apps/api/src/dependencies.py`

Injectables:

- DB engine/session factory/session
- vector store singleton
- embedding service singleton
- LLM service singleton
- learning service
- gamification service
- Redis client singleton with safe fallback
- chat cache singleton

## 5.4 Data Model (SQLAlchemy)

File: `apps/api/src/models/database.py`

Core entity graph:

- `Repository` <- `CodeFile` <- `CodeChunk`
- `Repository` <- `ChatSession` <- `ChatMessage`
- `Repository` <- `LearningSyllabus`
- `Repository` <- `LearningLesson`
- `Repository` <- `LessonProgress`
- `Repository` <- `UserXP`
- `Repository` <- `Achievement`
- `Repository` <- `GraphNodeInteraction`

Notable indexing and schema hardening:

- indexes on common query axes (repo, status, session timestamps, lesson lookup keys)
- lightweight runtime migrations in `apps/api/src/models/migrations.py` for additive compatibility

## 5.5 Route Surface (Backend API)

### Repository routes (`apps/api/src/api/routes/repos.py`)

- `POST /api/repos/`
- `GET /api/repos/`
- `GET /api/repos/{repo_id}`
- `GET /api/repos/{repo_id}/progress` (SSE)
- `DELETE /api/repos/{repo_id}`
- `GET /api/repos/{repo_id}/files/content`
- `POST /api/repos/demo/seed`

### Chat routes (`apps/api/src/api/routes/chat.py`)

- `POST /api/chat/sessions`
- `GET /api/chat/sessions/{session_id}`
- `POST /api/chat/sessions/{session_id}/messages` (SSE)

### Search routes (`apps/api/src/api/routes/search.py`)

- `POST /api/search/`

### Learning/gamification/challenges routes (`apps/api/src/api/routes/learning.py`)

- personas, curriculum, lessons, quiz generation, CodeTour export
- graph generation
- stats/activity/achievements/progress
- lesson/quiz/challenge completion
- graph viewed and node viewed events
- challenge generation and type-specific validation

### Platform route (`apps/api/src/api/routes/platform.py`)

- `GET /api/platform/config`

## 5.6 Core Retrieval and Answering Logic

File: `apps/api/src/core/rag/pipeline.py`

Major components:

- intent model (`overview`, `implementation`, `tech_stack`, `location`, `troubleshooting`)
- retrieval profile mapping (`docs_first`, `code_first`, `stack`, `location`, `error_focus`)
- query normalization and bounded expansion
- embedding cache lookup/population
- hybrid search calls across expanded queries
- retrieval candidate cache
- optional LLM rerank with strict JSON target
- context builder with max-char budget and grouped file sections
- history budget enforcement
- intent-specific system prompts
- answer cache for non-streaming and streaming paths

Why this is important:

- This file is the core quality engine for chat relevance and grounding confidence.

## 5.7 Vector Store Scoring Logic

File: `apps/api/src/core/vectorstore/chroma_store.py`

Notable logic:

- vector distance -> similarity conversion
- profile-specific weighting matrix
- keyword and file-path boosts
- docs/manifest boosts for feature and tech-stack questions
- location/error specific heuristics
- trivial-content penalties
- allowlist-based path filtering for context-constrained questions

## 5.8 Parsing Logic (Tree-sitter)

File: `apps/api/src/core/parser/tree_sitter_parser.py`

Capabilities:

- language-specific parser configs for Python/JS/TS/Java/Go/Rust/C#/C++/Ruby
- recursive traversal to extract classes/functions/methods
- import extraction
- python docstring extraction
- dedupe logic by chunk location/type/name
- module fallback chunk when semantic extraction is empty

## 5.9 Indexing Service Mechanics

File: `apps/api/src/services/indexing_service.py`

Stages:

1. hard reset prior index snapshot for repo
2. clone repository
3. discover candidate files (extensions + rails special filenames)
4. parse or raw-index each file
5. persist file/chunk metadata
6. embed all chunk content
7. write vectors to per-repo Chroma collection
8. update status/progress

Key resilience behavior:

- parse failures are non-fatal for whole repo
- raw indexing fallback prevents total loss on parser mismatch
- embedding and vector operations batched

## 5.10 Learning Service Mechanics

File: `apps/api/src/services/learning_service.py`

This is the most complex service. It contains:

- persona inventory and blueprint strategy
- curriculum generation v1/v2
- lesson generation v1/v2
- lesson/curriculum cache TTL policy
- JSON repair/parse helpers for LLM output
- quality scoring and fallback generation
- mermaid quality checks and fallback diagram construction
- quiz generation
- deterministic dependency graph builder
- graph pruning/metrics/ranking/cache logic
- optional LLM enrichment for node descriptions
- CodeTour export generation

Graph-specific helper families inside this file:

- path/module resolution
- import relation inference
- module aggregation
- scoped/focus subgraph extraction
- edge ranking and per-node budget enforcement
- connected-component and pruning logic

## 5.11 Gamification Service Mechanics

File: `apps/api/src/services/gamification.py`

Core responsibilities:

- XP award and level calculation
- streak update logic
- achievement unlock/check helpers
- lesson/quiz/challenge completion recorders
- graph node exploration tracking
- activity heatmap source aggregation

## 5.12 Challenge Service Mechanics

File: `apps/api/src/services/challenges.py`

Responsibilities:

- challenge prompt construction by type
- JSON extraction of LLM output
- deterministic mock fallback payloads
- answer validation for each challenge type

---

## 6) Frontend Deep Dive

## 6.1 App Entry and Route Surfaces

- Root layout: `apps/web/src/app/layout.tsx`
- Landing page: `apps/web/src/app/page.tsx`
- Repository page: `apps/web/src/app/repos/page.tsx`
- Chat page: `apps/web/src/app/repos/[repoId]/chat/page.tsx`
- Learning workspace page: `apps/web/src/app/repos/[repoId]/learn/page.tsx`

Learning page is the primary app-shell after import:

- tabbed workspace (`dashboard` / `syllabus` / `graph`)
- persona selection flow
- syllabus and lesson modals
- XP widget/toasts/popups
- achievement modal
- graph full-workspace view

## 6.2 API Client Contract Layer

File: `apps/web/src/lib/api-client.ts`

Responsibilities:

- all typed interfaces for repository/chat/search/learning/gamification/challenges/graph
- uniform error handling via `ApiError`
- SSE parsing for chat stream
- URL query shaping for optional params
- endpoint wrappers for every backend route used by UI

This file is the frontend-to-backend integration contract.

## 6.3 Chat Interface

File: `apps/web/src/components/chat/chat-interface.tsx`

Capabilities:

- local chat state and optimistic user message append
- streaming assistant message assembly from SSE chunks
- renders `sources` and `meta` sections per response
- markdown and syntax-highlighted code blocks with copy button
- starter prompts in empty state
- API error adaptation for demo rate-limit and busy mode states

## 6.4 Repository Management UI

File: `apps/web/src/components/repos/repo-list.tsx`

Capabilities:

- add repo form
- dynamic repository cards with status-dependent action availability
- periodic polling while any repo is indexing
- demo mode behavior:
  - feature repo banner
  - import/delete restrictions in UI
  - demo seed helper action

## 6.5 Learning UI System

Core components:

- persona chooser: `apps/web/src/components/learning/persona-selector.tsx`
- syllabus timeline: `apps/web/src/components/learning/syllabus-view.tsx`
- lesson workspace: `apps/web/src/components/learning/lesson-view.tsx`
- quiz modal: `apps/web/src/components/learning/quiz-view.tsx`
- challenge modal: `apps/web/src/components/learning/ChallengeView.tsx`
- mermaid renderer: `apps/web/src/components/learning/MermaidDiagram.tsx`

Lesson workspace behavior:

- left panel markdown content + diagram
- right panel code evidence viewer with reference tabs
- source-file fetch and line highlight
- actions: quiz, challenges, regenerate lesson, export CodeTour, finish lesson

## 6.6 Graph UI System

Primary orchestrator:

- `apps/web/src/components/learning/graph-view.tsx`

Supporting modules:

- node rendering: `graph/CustomNode.tsx`
- edge rendering: `graph/CustomEdge.tsx`
- filter legend: `graph/GraphLegend.tsx`
- action toolbar: `graph/GraphToolbar.tsx`
- inspector/details: `graph/NodeDetailPanel.tsx`
- layout engine: `graph/graph-layouts.ts`

Notable client-side graph mechanics:

- local file-type filtering + search
- focus neighborhood and selected-node neighborhood highlighting
- zoom-dependent edge density throttling
- top-ranked edge preservation under budget
- inspector-based source preview and relation traversal

## 6.7 Gamification Dashboard Components

- XP widget: `apps/web/src/components/learning/XPWidget.tsx`
- XP bars/popups: `apps/web/src/components/learning/XPBar.tsx`
- achievements panel/toast: `apps/web/src/components/learning/AchievementsPanel.tsx`
- dashboard page section: `apps/web/src/components/dashboard/dashboard-view.tsx`
- activity heatmap: `apps/web/src/components/dashboard/activity-heatmap.tsx`

---

## 7) CLI Deep Dive

Main file: `cli/codebaseqa/cli.py`

Commands:

- `index <github_url>`
- `ask <repo_id> <question>`
- `list`
- `search <repo_id> <query>`
- `lessons <repo_id>`
- `export-tour <repo_id> <lesson_id>`

Behavior:

- wraps backend HTTP routes
- streams SSE chat content in terminal
- prints source citations for chat
- provides curriculum listing and tour export for editor workflows

---

## 8) Testing and Quality Strategy

## 8.1 Backend Tests

Types:

- integration tests under `apps/api/tests/integration`
- unit tests under `apps/api/tests/unit`
- parser coverage in `apps/api/tests/test_parser.py`

What is explicitly tested:

- route behavior and payload shapes
- chat SSE event contract (`sources`, `meta`, `content`, `done`)
- intent routing and mode/context pass-through
- retrieval scoring profiles and allowlist filtering
- repo manager URL parsing and file path traversal protections
- indexing fallback behavior and extension handling
- learning v2 cache usage and fallback quality
- graph deterministic edge extraction/pruning/ranking/recommended entry logic
- embedding retry/spacing behavior

## 8.2 Frontend Tests

Files include:

- lesson, quiz, syllabus, challenge component tests
- shared code block test
- basic example test scaffold

Focus:

- interaction states and rendering behavior for core learning UX components

## 8.3 CI Pipeline

File: `.github/workflows/ci.yml`

Backend job:

- Python setup
- dependency install
- Ruff lint
- pytest with coverage
- codecov upload

Frontend job:

- pnpm install
- lint
- type-check
- build
- compiled CSS verification
- vitest

---

## 9) Security, Reliability, and Operational Notes

## 9.1 Security-positive patterns

- repository URL sanitization and segment validation
- file content endpoint prevents path traversal escapes
- demo mode mutation guardrail for public deployments
- optional private vulnerability reporting path documented

## 9.2 Reliability patterns

- retry logic in LLM and embedding providers
- fallback to in-memory caching/rate limiting when Redis unavailable
- parse failure fallback to raw indexing
- graph layout fallback from ELK to Dagre
- global exception handler to avoid uncaught crashes leaking raw exceptions

## 9.3 Operational observations

- `learning_service.py` and graph/chat modules are large and central risk surfaces for regression.
- many behavior flags exist in config; this is powerful but raises complexity and test matrix size.
- runtime migrations are additive and pragmatic, but long-term may benefit from formal migration tooling once schema evolves further.

---

## 10) Key API Contract Reference

| Domain | Endpoint | Request Highlights | Response Highlights |
|---|---|---|---|
| Repos | `POST /api/repos/` | `github_url`, optional `branch` | repository record with status |
| Repos | `GET /api/repos/{id}/progress` | SSE | status/progress updates |
| Chat | `POST /api/chat/sessions/{id}/messages` | `content`, optional `mode`, `context_files`, `debug` | SSE event stream (`sources/meta/content/done/error`) |
| Search | `POST /api/search/` | `repo_id`, `query`, optional filters | scored chunk list |
| Learning | `POST /api/learning/{repo}/curriculum` | `persona`, optional refresh/meta toggles | syllabus modules/lessons |
| Learning | `POST /api/learning/{repo}/lessons/{lesson}` | title + persona/module context | lesson markdown + code refs + mermaid |
| Graph | `GET /api/learning/{repo}/graph` | `granularity`, `scope`, `focus_node`, `hops` | nodes/edges/meta |
| Gamification | `POST /api/learning/{repo}/lessons/{lesson}/complete` | completion payload | XP gain + refreshed stats |
| Challenges | `POST /api/learning/{repo}/challenges/validate/*` | challenge + answer | correctness + XP when correct |

---

## 11) File-by-File Appendix

This appendix enumerates tracked files in this repository with line count and role summary, excluding promotional collateral per request.

### 11.1 Legend

- `Area`: logical subsystem
- `Purpose`: concise file responsibility
- `Type`: config/code/test/asset/etc

| File | Lines | Area | Type | Purpose |
|---|---:|---|---|---|
| `.env.example` | 133 | root | env template | Environment variable template covering providers, demo mode, graph/chat tuning. |
| `CODE_OF_CONDUCT.md` | 40 | root | docs | Documentation/guide markdown file. |
| `CONTRIBUTING.md` | 87 | root | docs | Documentation/guide markdown file. |
| `LICENSE` | 21 | root | license | Repository file (specialized role inferred from path/context). |
| `README.md` | 451 | root | docs | Primary project overview, setup, API and feature guide. |
| `SECURITY.md` | 36 | root | docs | Documentation/guide markdown file. |
| `SUPPORT.md` | 22 | root | docs | Documentation/guide markdown file. |
| `apps/api/Dockerfile` | 28 | backend | file | Repository file (specialized role inferred from path/context). |
| `apps/api/coverage.xml` | 4969 | backend | artifact | Repository file (specialized role inferred from path/context). |
| `apps/api/diagnose_chunk_size.py` | 81 | backend | python | Repository file (specialized role inferred from path/context). |
| `apps/api/diagnose_content.py` | 71 | backend | python | Repository file (specialized role inferred from path/context). |
| `apps/api/diagnose_fix.py` | 82 | backend | python | Repository file (specialized role inferred from path/context). |
| `apps/api/diagnose_load.py` | 50 | backend | python | Repository file (specialized role inferred from path/context). |
| `apps/api/pyproject.toml` | 23 | backend | config/data | Configuration file for tooling/workflows. |
| `apps/api/reproduce_ollama.py` | 61 | backend | python | Repository file (specialized role inferred from path/context). |
| `apps/api/requirements.txt` | 50 | backend | artifact | Repository file (specialized role inferred from path/context). |
| `apps/api/src/__init__.py` | 1 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/api/__init__.py` | 1 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/api/routes/__init__.py` | 3 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/api/routes/chat.py` | 307 | backend | python | Chat session endpoints and SSE streaming message endpoint with concurrency/timeout guards. |
| `apps/api/src/api/routes/learning.py` | 514 | backend | python | Learning, graph, progress, gamification, challenge generation/validation endpoints. |
| `apps/api/src/api/routes/platform.py` | 16 | backend | python | Runtime platform config endpoint for frontend feature flags/demo mode. |
| `apps/api/src/api/routes/repos.py` | 289 | backend | python | Repository CRUD/indexing endpoints, progress stream, file content, demo seeding. |
| `apps/api/src/api/routes/search.py` | 82 | backend | python | Semantic/hybrid search endpoint with optional file/language filters. |
| `apps/api/src/config.py` | 209 | backend | python | Centralized Pydantic settings for providers, graph/chat/learning/demo flags. |
| `apps/api/src/core/__init__.py` | 1 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/core/cache/__init__.py` | 4 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/core/cache/chat_cache.py` | 206 | backend | python | Embedding/retrieval/answer cache with Redis+memory fallback. |
| `apps/api/src/core/cache/llm_cache.py` | 73 | backend | python | Global in-memory cache for LLM message responses. |
| `apps/api/src/core/demo_mode.py` | 110 | backend | python | Demo access and mutation policy enforcement + platform payload builder. |
| `apps/api/src/core/embeddings/__init__.py` | 2 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/core/embeddings/base.py` | 22 | backend | python | Abstract embedding interface contract. |
| `apps/api/src/core/embeddings/factory.py` | 40 | backend | python | Embedding provider factory based on settings. |
| `apps/api/src/core/embeddings/ollama_embeddings.py` | 155 | backend | python | Ollama embeddings with retry/fail-open behavior. |
| `apps/api/src/core/embeddings/openai_embeddings.py` | 207 | backend | python | OpenAI embeddings with batching, pacing, and rate-limit retries. |
| `apps/api/src/core/github/__init__.py` | 2 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/core/github/repo_manager.py` | 195 | backend | python | GitHub URL parsing, clone/default-branch logic, safe local file retrieval. |
| `apps/api/src/core/llm/__init__.py` | 2 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/core/llm/anthropic_llm.py` | 96 | backend | python | Anthropic chat adapter with format conversion and streaming. |
| `apps/api/src/core/llm/base.py` | 23 | backend | python | Abstract LLM interface contract. |
| `apps/api/src/core/llm/factory.py` | 34 | backend | python | LLM provider factory based on settings. |
| `apps/api/src/core/llm/ollama_llm.py` | 98 | backend | python | Ollama chat adapter for local model usage. |
| `apps/api/src/core/llm/openai_llm.py` | 126 | backend | python | OpenAI chat adapter with retry and streaming behavior. |
| `apps/api/src/core/logging.py` | 38 | backend | python | Structlog logging configuration helpers. |
| `apps/api/src/core/parser/__init__.py` | 7 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/core/parser/tree_sitter_parser.py` | 357 | backend | python | Multi-language semantic parsing and chunk extraction via Tree-sitter. |
| `apps/api/src/core/rag/__init__.py` | 2 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/core/rag/pipeline.py` | 776 | backend | python | Intent-aware retrieval, reranking, context build, history budget, and answer generation. |
| `apps/api/src/core/rate_limit.py` | 177 | backend | python | Demo soft-throttling buckets with Redis backend and local fallback. |
| `apps/api/src/core/vectorstore/__init__.py` | 2 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/core/vectorstore/chroma_store.py` | 368 | backend | python | Chroma integration plus profile-aware hybrid scoring heuristics. |
| `apps/api/src/demo/__init__.py` | 1 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/demo/seed_demo.py` | 209 | backend | python | Script to seed/check/index featured demo repository. |
| `apps/api/src/dependencies.py` | 124 | backend | python | Dependency injection providers for DB, vector store, LLM, services, Redis, chat cache. |
| `apps/api/src/main.py` | 250 | backend | python | FastAPI app bootstrap, lifespan resource init, route registration, health and OpenAPI endpoints. |
| `apps/api/src/models/__init__.py` | 1 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/models/codetour_schemas.py` | 22 | backend | python | Pydantic schema for VS Code CodeTour export. |
| `apps/api/src/models/database.py` | 364 | backend | python | SQLAlchemy schema for repositories, code metadata, chat, learning cache/progress, XP, achievements. |
| `apps/api/src/models/learning.py` | 144 | backend | python | Learning domain schemas for personas, syllabus, lessons, quiz, dependency graph. |
| `apps/api/src/models/migrations.py` | 116 | backend | python | Lightweight additive runtime migrations and index hardening. |
| `apps/api/src/models/schemas.py` | 194 | backend | python | API request/response schemas for repository/chat/search/platform endpoints. |
| `apps/api/src/services/__init__.py` | 1 | backend | python | Package initializer for module exports/import resolution. |
| `apps/api/src/services/challenges.py` | 335 | backend | python | Challenge generation prompts, fallback mocks, and answer validation. |
| `apps/api/src/services/gamification.py` | 560 | backend | python | XP, levels, streaks, achievements, and progress recording logic. |
| `apps/api/src/services/indexing_service.py` | 582 | backend | python | Repository indexing pipeline: file discovery, parse/raw chunking, embedding and progress. |
| `apps/api/src/services/learning_service.py` | 2360 | backend | python | Learning v1/v2 generation, quality/fallback logic, graph generation, CodeTour export. |
| `apps/api/test_llm_factory.py` | 57 | backend | python | Repository file (specialized role inferred from path/context). |
| `apps/api/test_output.txt` | 321 | backend | artifact | Repository file (specialized role inferred from path/context). |
| `apps/api/tests/__init__.py` | 1 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/conftest.py` | 149 | backend | python | Shared pytest fixtures for API tests and sample code snippets. |
| `apps/api/tests/evals/chat_quality_cases.json` | 23 | backend | config/data | Golden chat evaluation fixtures focused on grounding quality. |
| `apps/api/tests/integration/test_api.py` | 88 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/integration/test_chat_pipeline.py` | 190 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/integration/test_demo_mode.py` | 57 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/integration/test_learning_challenges.py` | 98 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/integration/test_learning_v2_routes.py` | 191 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/test_parser.py` | 138 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/unit/test_indexing.py` | 168 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/unit/test_learning_graph_v2.py` | 231 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/unit/test_learning_v2_service.py` | 295 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/unit/test_openai_embeddings.py` | 98 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/unit/test_rag.py` | 45 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/unit/test_rag_intents.py` | 61 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/unit/test_rag_language_mapping.py` | 31 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/unit/test_repo_manager.py` | 79 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/tests/unit/test_retrieval_scoring.py` | 86 | backend | python | Backend test file covering specific route/service behavior or regression. |
| `apps/api/verify_all.py` | 71 | backend | python | Repository file (specialized role inferred from path/context). |
| `apps/api/verify_ollama_retry.py` | 36 | backend | python | Repository file (specialized role inferred from path/context). |
| `apps/web/README.md` | 23 | frontend | docs | Documentation/guide markdown file. |
| `apps/web/eslint.config.mjs` | 18 | frontend | typescript/js | Repository file (specialized role inferred from path/context). |
| `apps/web/next.config.ts` | 10 | frontend | typescript/js | Repository file (specialized role inferred from path/context). |
| `apps/web/package.json` | 50 | frontend | config/data | Configuration or structured data file. |
| `apps/web/pnpm-lock.yaml` | 7384 | frontend | config/data | Configuration file for tooling/workflows. |
| `apps/web/pnpm-workspace.yaml` | 3 | frontend | config/data | Configuration file for tooling/workflows. |
| `apps/web/postcss.config.mjs` | 7 | frontend | typescript/js | Repository file (specialized role inferred from path/context). |
| `apps/web/public/file.svg` | 0 | frontend | asset | Static public asset for Next.js app. |
| `apps/web/public/globe.svg` | 0 | frontend | asset | Static public asset for Next.js app. |
| `apps/web/public/next.svg` | 0 | frontend | asset | Static public asset for Next.js app. |
| `apps/web/public/vercel.svg` | 0 | frontend | asset | Static public asset for Next.js app. |
| `apps/web/public/window.svg` | 0 | frontend | asset | Static public asset for Next.js app. |
| `apps/web/src/app/favicon.ico` | 30 | frontend | asset | Image/graphic asset used in docs or UI. |
| `apps/web/src/app/globals.css` | 72 | frontend | file | Repository file (specialized role inferred from path/context). |
| `apps/web/src/app/layout.tsx` | 21 | frontend | typescript/js | Global Next.js layout and base body classes. |
| `apps/web/src/app/page.tsx` | 60 | frontend | typescript/js | Landing page assembly with hero/features/footer. |
| `apps/web/src/app/repos/[repoId]/chat/page.tsx` | 65 | frontend | typescript/js | Server page creating chat session and rendering chat interface. |
| `apps/web/src/app/repos/[repoId]/learn/page.tsx` | 469 | frontend | typescript/js | Main learning workspace shell with tabs, overlays, and data orchestration. |
| `apps/web/src/app/repos/page.tsx` | 75 | frontend | typescript/js | Repository hub page that loads repo list and platform config. |
| `apps/web/src/components/chat/chat-interface.tsx` | 414 | frontend | typescript/js | Interactive streaming chat UI with markdown, code rendering, and source evidence panels. |
| `apps/web/src/components/common/brand-logo.tsx` | 53 | frontend | typescript/js | Shared UI component used across pages. |
| `apps/web/src/components/common/demo-banner.tsx` | 52 | frontend | typescript/js | Shared UI component used across pages. |
| `apps/web/src/components/common/repo-context-badge.tsx` | 31 | frontend | typescript/js | Shared UI component used across pages. |
| `apps/web/src/components/common/site-footer.tsx` | 72 | frontend | typescript/js | Shared UI component used across pages. |
| `apps/web/src/components/dashboard/activity-heatmap.tsx` | 87 | frontend | typescript/js | 365-day activity heatmap renderer. |
| `apps/web/src/components/dashboard/dashboard-view.tsx` | 183 | frontend | typescript/js | Learning analytics dashboard composition. |
| `apps/web/src/components/example.test.tsx` | 13 | frontend | typescript/js | Frontend component test file. |
| `apps/web/src/components/home/bento-grid.tsx` | 401 | frontend | typescript/js | Landing page marketing/feature presentation component. |
| `apps/web/src/components/home/hero-section.tsx` | 146 | frontend | typescript/js | Landing page marketing/feature presentation component. |
| `apps/web/src/components/learning/AchievementsPanel.tsx` | 217 | frontend | typescript/js | Achievement grid/modal with unlock progress and toast. |
| `apps/web/src/components/learning/ChallengeView.test.tsx` | 73 | frontend | typescript/js | Frontend component test file. |
| `apps/web/src/components/learning/ChallengeView.tsx` | 524 | frontend | typescript/js | Challenge UI for bug-hunt/code-trace/fill-blank interactions. |
| `apps/web/src/components/learning/MermaidDiagram.tsx` | 523 | frontend | typescript/js | Mermaid render wrapper with sanitization, fullscreen, zoom, and pan controls. |
| `apps/web/src/components/learning/XPBar.tsx` | 150 | frontend | typescript/js | XP progress bars and XP gain popup component. |
| `apps/web/src/components/learning/XPWidget.tsx` | 163 | frontend | typescript/js | Floating XP/level/streak widget and expanded stats panel. |
| `apps/web/src/components/learning/graph-view.tsx` | 908 | frontend | typescript/js | React Flow graph orchestration: load/filter/focus/export and inspector integration. |
| `apps/web/src/components/learning/graph/CustomEdge.tsx` | 119 | frontend | typescript/js | Edge style system with rank/weight highlighting and labels. |
| `apps/web/src/components/learning/graph/CustomNode.tsx` | 245 | frontend | typescript/js | Node style system and file-type heuristics for graph rendering. |
| `apps/web/src/components/learning/graph/GraphLegend.tsx` | 121 | frontend | typescript/js | Node-type filter legend UI. |
| `apps/web/src/components/learning/graph/GraphToolbar.tsx` | 119 | frontend | typescript/js | Graph action controls (fit, center, regenerate, minimap, export). |
| `apps/web/src/components/learning/graph/NodeDetailPanel.tsx` | 320 | frontend | typescript/js | Inspector panel with metrics, relations, and source preview. |
| `apps/web/src/components/learning/graph/graph-layouts.ts` | 227 | frontend | typescript/js | Auto-layout engine (ELK primary, Dagre fallback) with cache. |
| `apps/web/src/components/learning/lesson-view.test.tsx` | 179 | frontend | typescript/js | Frontend component test file. |
| `apps/web/src/components/learning/lesson-view.tsx` | 626 | frontend | typescript/js | Lesson workspace combining markdown, diagram, code evidence, quiz/challenges, completion. |
| `apps/web/src/components/learning/persona-selector.tsx` | 204 | frontend | typescript/js | Persona selection UI with mission/track emphasis. |
| `apps/web/src/components/learning/quiz-view.test.tsx` | 86 | frontend | typescript/js | Frontend component test file. |
| `apps/web/src/components/learning/quiz-view.tsx` | 224 | frontend | typescript/js | Quiz runner UI and score submission flow. |
| `apps/web/src/components/learning/syllabus-view.test.tsx` | 84 | frontend | typescript/js | Frontend component test file. |
| `apps/web/src/components/learning/syllabus-view.tsx` | 255 | frontend | typescript/js | Curriculum timeline viewer with module expansion and refresh action. |
| `apps/web/src/components/repos/repo-list.tsx` | 424 | frontend | typescript/js | Repo cards/import form/demo handling and indexing status polling. |
| `apps/web/src/components/ui/code-block.test.ts` | 22 | frontend | typescript/js | Frontend component test file. |
| `apps/web/src/components/ui/code-block.tsx` | 133 | frontend | typescript/js | Reusable UI primitive component. |
| `apps/web/src/components/ui/typing-indicator.tsx` | 28 | frontend | typescript/js | Reusable UI primitive component. |
| `apps/web/src/lib/api-client.ts` | 769 | frontend | typescript/js | Typed frontend API client and SSE parser for all backend domains. |
| `apps/web/src/lib/utils.ts` | 25 | frontend | typescript/js | Utility helpers (`cn`, date formatting). |
| `apps/web/src/test-setup.ts` | 1 | frontend | typescript/js | Repository file (specialized role inferred from path/context). |
| `apps/web/tsconfig.json` | 34 | frontend | config/data | Configuration or structured data file. |
| `apps/web/vercel.json` | 4 | frontend | config/data | Configuration or structured data file. |
| `apps/web/vitest.config.ts` | 15 | frontend | typescript/js | Repository file (specialized role inferred from path/context). |
| `cli/README.md` | 42 | cli | docs | Documentation/guide markdown file. |
| `cli/codebaseqa/__init__.py` | 1 | cli | python | Repository file (specialized role inferred from path/context). |
| `cli/codebaseqa/cli.py` | 345 | cli | python | Terminal client commands for indexing, chat, search, lessons, and CodeTour export. |
| `cli/pyproject.toml` | 18 | cli | config/data | Configuration file for tooling/workflows. |
| `docker/Dockerfile.api` | 36 | docker | file | Container image build for backend service. |
| `docker/Dockerfile.web` | 38 | docker | file | Container image build for frontend service. |
| `docker/README.md` | 29 | docker | docs | Documentation/guide markdown file. |
| `docker/docker-compose.yml` | 68 | docker | config/data | Local multi-service stack (web, api, redis). |
| `docker/entrypoint.sh` | 21 | docker | shell | API entrypoint with optional background demo seeding. |
| `docs/CODEBASE_DEEP_DIVE.md` | 981 | docs | docs | Project documentation artifact. |
| `docs/architecture.md` | 60 | docs | docs | Short system architecture overview and design decisions. |
| `docs/architecture_diagram_final.png` | 28654 | docs | asset | Documentation media/diagram asset. |
| `docs/media/README.md` | 24 | docs | docs | Documentation media/diagram asset. |
| `docs/media/screenshots/01-repo-import.svg` | 6 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/01_MainPage.png` | 293 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/01_b_MainPage.png` | 1139 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/02-chat-citations.svg` | 6 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/02_RepoPage.png` | 183 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/03-learning-lesson.svg` | 6 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/03_ChatPage.png` | 247 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/04-quiz-challenge.svg` | 6 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/04_AuthChat.png` | 1950 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/05-dependency-graph.svg` | 6 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/05_Graph.png` | 596 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/06-cli-workflow.svg` | 6 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/06_grpahDepth.png` | 1936 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/07_LearnPage.png` | 380 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/08_FullStackTrackl.png` | 426 | docs | asset | Documentation media/diagram asset. |
| `docs/media/screenshots/09_InsideLearn.png` | 655 | docs | asset | Documentation media/diagram asset. |
| `docs/media/social/README.md` | 11 | docs | docs | Documentation media/diagram asset. |
| `docs/media/video/README.md` | 6 | docs | docs | Documentation media/diagram asset. |
| `docs/media/video/demo-thumbnail.svg` | 14 | docs | asset | Documentation media/diagram asset. |
| `docs/releases/v1.0.0.md` | 65 | docs | docs | Release notes for v1.0.0 scope and verification. |
| `package.json` | 34 | root | config/data | Root workspace scripts for turbo/pnpm orchestration. |
| `pnpm-lock.yaml` | 7478 | root | config/data | Configuration file for tooling/workflows. |
| `pnpm-workspace.yaml` | 3 | root | config/data | Declares workspace packages (`apps/*`, `packages/*`). |
| `scripts/prewarm-demo.mjs` | 104 | scripts | typescript/js | Post-deploy prewarm for demo curriculum/graph/chat readiness. |
| `scripts/start-docker.sh` | 29 | scripts | shell | Convenience launcher for docker-compose with optional demo flag. |
| `scripts/verify-web-css.mjs` | 39 | scripts | typescript/js | Build artifact CSS sanity checks for CI guardrail. |
| `turbo.json` | 36 | root | config/data | Turbo task graph and cache behavior. |
