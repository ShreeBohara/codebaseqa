# RESUME_DOSSIER — CodebaseQA

> Raw source material for a resume corpus. Written engineer-to-engineer, not as resume bullets.
> Generated from a line-by-line read of the repository at `34c7490` (branch `feat/durable-indexing-progress`, one commit ahead of `main` at `add5575`).
>
> **Number convention used throughout:**
> - `[MEASURED]` — read directly out of the repo, git, the SQLite DB, or the Chroma store on this machine. You can reproduce these live in front of an interviewer.
> - `[DERIVED]` — arithmetic on measured values plus published vendor pricing/limits. Reproducible.
> - `[EST]` — my estimate from comparable systems or from the code's own configured limits. Defensible if challenged, but **not benchmarked**. Never present these as observed results.

---

## Identity

**Name:** CodebaseQA

### The 30-second version

CodebaseQA is a self-hostable product that makes an unfamiliar codebase legible in minutes instead of weeks. Paste a GitHub URL; it shallow-clones the repo, parses every source file into function- and class-level chunks with nine Tree-sitter grammars, embeds them into a vector store, and then gives you four different lenses on the same index: a **streaming chat** that answers with real file-and-line citations, an **AI-generated learning track** that changes shape depending on whether you're a new hire, a security auditor, a full-stack dev, or a code archaeologist, an **interactive dependency graph** built deterministically from actual import statements, and a **quiz/challenge layer** with XP, streaks and achievements so that grinding through a strange system produces visible progress instead of drift. It runs against OpenAI, Anthropic, or a fully local Ollama, so a private repo never has to leave your machine. There's also a Python CLI, and lessons export to VS Code CodeTour files.

Built solo, start to public v1.0.0, in **19 calendar days** — then picked back up ~6 months later for a second phase that added a deployed backend (Terraform), a fifth LLM provider surface (Azure OpenAI), a Neo4j graph read model, a GraphQL surface, and a security-and-correctness audit pass.

### The longer version

The interesting engineering is not "I called an LLM." It's the four places where the obvious LLM-shaped solution was deliberately *removed* or *fenced in*:

- The **dependency graph** started as an LLM that generated nodes and edges. It was ripped out and replaced with a deterministic import resolver, because a map that changes between runs and invents dependencies is worse than no map. The LLM's surviving role is optional 18-word node descriptions, and that's off by default.
- The **intent classifier** is deterministic keyword scoring. The LLM is only invoked to break a genuine tie between the top two intents — cheap, testable, and free in the common case.
- Every **generation path** in the learning engine assumes the model will fail: four independent quality gates, a deterministic fallback for each, and a recorded `fallback_reason` persisted next to the content.
- Every **citation** the model produces is re-validated against an allowlist of real indexed paths and clamped against a real `{path: line_count}` map from the database. Hallucinated files are dropped; out-of-range line numbers are clamped. That's why the citations actually resolve.

That posture — *use AI aggressively, trust it nowhere* — is the through-line of the whole codebase, and it's the thing to lead with in any conversation about this project.

**Repo URL:** https://github.com/ShreeBohara/codebaseqa
**Demo video:** https://www.youtube.com/watch?v=nM8-2t4xr9A (90 seconds)
**Live URL:** Not recorded in the repo. It's set up for a split deploy — Next.js on Vercel (`apps/web/vercel.json`, `@vercel/analytics` in [layout.tsx:19](apps/web/src/app/layout.tsx:19)) and FastAPI on Render (`docs/CODEBASE_DEEP_DIVE.md:53-66`), wired together by `NEXT_PUBLIC_API_URL`. No production hostname is hardcoded anywhere, so pull the URL from your Vercel dashboard before citing it.

**Current status:** **Active, in a second development phase.** v1.0.0 shipped 2026-02-19 with full OSS governance (MIT, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SUPPORT, issue + PR templates, CI badge). After ~6 months dormant, work resumed 2026-08-08 and is ongoing as of 2026-08-11 — the current branch `feat/durable-indexing-progress` is one commit ahead of `main` and unmerged.

### By the numbers `[MEASURED unless noted]` — current tree, with Phase 1 in parentheses

| | |
|---|---:|
| **Commits** | 47 (34 in Phase 1, 13 in Phase 2) |
| **Active calendar days** | 19 + 4 |
| **Tracked files** | 219 (was 199) |
| **Total tracked lines** | ~27,750 (was ~24,400) |
| Backend production source (`apps/api/src`) | 11,340 lines / 44 modules (was 9,808 / 39) |
| Frontend source (`apps/web/src`) | 8,811 lines / 42 files |
| Backend tests | **3,178 lines / 20 modules** (was 2,006 / 16) |
| Frontend tests | 457 lines / 6 files |
| Infrastructure as code (Terraform + cloud-init) | **455 lines** (new in Phase 2) |
| Python CLI | 345 lines |
| Written docs + pre-build research | 8,241 lines |
| **Test functions** | **120** (142 pytest cases incl. parameterization) |
| **Python functions** | 315+ |
| **Python classes** | 98+ (53 Pydantic models) |
| **Exported React components** | 42 |
| **TypeScript interfaces / type aliases** | 89 (35 in the API contract layer alone) |
| **React hook call sites** | 208 (`useState` 120, `useEffect` 30, `useMemo` 26, `useCallback` 18, `useRef` 14) |
| **HTTP endpoints** | 37 REST **+ a GraphQL surface at `/graphql`** |
| **Database tables** | **13** (was 12) |
| **Database indexes** | **22** (was 19) |
| **Environment-tunable settings** | **127** (was 112) |
| **Runtime feature flags (booleans)** | **20** (was 19) |
| Tree-sitter grammars | 9 |
| Distinct LLM prompts | 16 |
| Retrieval weight profiles × coefficients | 6 × 8 = 48 tuned constants |
| Cache tiers | 3 (embedding / retrieval / answer) |
| Rate-limit buckets | 5, per-IP sliding window |
| **LLM providers / embedding providers** | **4 / 3** (OpenAI, Azure OpenAI, Anthropic, Ollama / OpenAI, Azure OpenAI, Ollama) |
| **Datastores** | SQLite, ChromaDB, Redis (optional), **Neo4j (optional)** |
| `except` blocks | 91+ |
| Structured `logger.*` calls | 85+ |
| Direct dependencies | ~75 (Python +strawberry-graphql, neo4j; 2 Terraform providers) |
| **Real OSS repos indexed during development** | 12+ (cal.com, documenso, plane, fastapi, express, rallly, shadcn-ui, httpie, encode, …) |
| **Accumulated Chroma collection segments on disk** | 44 (181 MB) |
| **Development SQLite DB size** | 103 MB |

`[DERIVED]` Phase 1 averaged ~1,280 tracked lines per calendar day for 19 days. Phase 2 added ~3,900 lines across 4 active days, but the meaningful number there is different: **13 commits whose messages total ~450 lines of written engineering rationale** — roughly one line of documented reasoning for every eight lines of code. Phase 2 is where the project stops looking like a fast build and starts looking like maintenance discipline.

### Languages `[MEASURED — git-tracked files only, lockfiles excluded]`

| Language | Files | Lines |
|---|---:|---:|
| Python | 87 | 15,373 |
| TypeScript (`.tsx`) | 36 | 7,736 |
| Markdown | 16 | 2,160 |
| TypeScript (`.ts`) | 6 | 1,075 |
| **HCL / Terraform** | **5 (+1 tftpl)** | **455** |
| YAML | 7 | 333 |
| JSON | 6 | 187 |
| JavaScript (`.mjs`) | 4 | 168 |
| Shell | 4 | 148 |
| CSS | 1 | 72 |
| TOML | 2 | 41 |

Largest files: [learning_service.py](apps/api/src/services/learning_service.py) 2,360 · [graph-view.tsx](apps/web/src/components/learning/graph-view.tsx) 908 · [pipeline.py](apps/api/src/core/rag/pipeline.py) 776 · [api-client.ts](apps/web/src/lib/api-client.ts) 769 · [lesson-view.tsx](apps/web/src/components/learning/lesson-view.tsx) 626.

### Notable dependencies

*Backend:* FastAPI + Uvicorn · Pydantic v2 + pydantic-settings · SQLAlchemy 2.x + aiosqlite · ChromaDB · `openai` · `anthropic` · tiktoken · **nine separate Tree-sitter grammar packages** (python, javascript, typescript, java, go, rust, c-sharp, cpp, ruby) · httpx · cachetools · redis · structlog · tenacity · pytest + pytest-asyncio · ruff

*Frontend:* Next.js 16.1.6 (App Router, `output: standalone`) · React 19.2.3 · `@xyflow/react` v12 · **elkjs + dagre** (two independent graph layout engines, one as failover for the other) · mermaid 11 · framer-motion 12 · react-markdown + react-syntax-highlighter · html-to-image · zustand · Tailwind CSS v4 · canvas-confetti · Vitest 4 + Testing Library + jsdom

*Tooling:* pnpm 10.28.2 workspaces · Turborepo 2.8 · Docker Compose (web + api + redis) · GitHub Actions

---

## Product thesis and market position

This section exists because the strongest version of this project's story is not "I built a RAG app." It's "I identified a gap in a real market, shipped a differentiated product against it in 19 days, and can defend every architectural decision." Use it when a manager or a founder asks *why*.

### The problem, with numbers

Onboarding into an unfamiliar codebase is one of the most expensive recurring costs in software, and it is almost entirely unmeasured. `[MEASURED — external, 2026]` Industry median **time-to-first-commit is 2–3 weeks**; DORA elite teams achieve 1–2 days while low performers take 2–4 weeks. Senior engineers reach ~90% velocity in 6–10 weeks; mid-level in 8–14 weeks; juniors in 4–6 months. Every one of those numbers is dominated by a single activity — reading code with no map, no guide, and no way to check whether you've understood it.

`[EST]` Run the arithmetic on a 50-engineer org with 20% annual turnover and a fully-loaded cost of ~$180k: ten ramp-ups a year, each burning 6–10 weeks at partial productivity, is roughly **$400k–$700k of annual dead weight**. That is the budget line this category is fighting over, and it's why Greptile raised at a reported $180M valuation.

### The competitive gap `[MEASURED — external, 2026 pricing]`

| Product | Position | The gap it leaves |
|---|---|---|
| **Greptile** | $30/seat/mo, semantic graph index, PR review focus | Cloud-only. No self-host. Your source leaves the building. |
| **Sourcegraph Cody** | Killed free + Pro individual tiers mid-2025; Enterprise-only, ~$16k/yr entry | Priced out of individuals and small teams entirely |
| **DeepWiki** | Free, ~50k pre-indexed public repos, wiki + Mermaid + Q&A | Public repos only. Read-only. Can't point it at your private monorepo. |
| **Bloop** | Was the open-source local-first option | Pivoted away from individual developers |
| **Continue.dev** | Genuinely open, BYOK | IDE-plugin shaped; no learning layer, no structural map |
| **GitHub Copilot Chat** | Broadest reach | Full codebase context reserved for Enterprise |

The unclaimed position: **self-hostable, private, BYOK, and built around *understanding* rather than *generation*.** That's the wedge CodebaseQA is aimed at, and it's why the architecture makes the choices it does — SQLite by default (zero-config self-host), Ollama as a first-class provider (source never leaves the machine), env-var BYOK, and a learning layer nobody else in the category ships.

### The product bet, and how it shows up in code

The bet is that "chat with your repo" is table stakes and insufficient — you can ask a chatbot a hundred questions and still have no mental model. So the product ships four surfaces that map onto what a new engineer actually does:

| What a new engineer does | Surface | Where it lives |
|---|---|---|
| Asks questions as they arise | Streaming chat with citations | WS-4 |
| Wants a structured path, not random walk | Persona-conditioned learning track | WS-6 |
| Needs to see the shape of the system | Deterministic dependency graph | WS-7 / WS-8 |
| Needs to verify they actually retained it | Quizzes + code challenges + XP | WS-9 / WS-10 |

`[EST]` If the product delivers even a **20% reduction in ramp time** — 2 weeks off a 10-week senior ramp — the arithmetic above says it pays for a self-hosted deployment several hundred times over. That is the pitch, and the honest caveat is that it was never measured with real users. Say the caveat out loud; it's more credible than the claim.

---

## Timeline

`[MEASURED — all from git]`

- **First commit:** `7f62f27` — 2026-01-31 15:44 PST. A one-line README.
- **First real code:** `c25e999` — 2026-01-31, *the same day*: 38 files, 3,315 insertions. The entire RAG skeleton landed in one commit, which means the architecture was decided before the repo existed. That's consistent with the 6,499 lines of research and implementation planning sitting in `Documents/`.
- **Last commit:** `34c7490` — 2026-08-11, on `feat/durable-indexing-progress`. `main` is at `add5575`, same day.
- **Total commits:** 47, across 19 distinct days, in two clearly separated phases with a ~6-month gap.

| Window | Commits | What was happening |
|---|---:|---|
| **Phase 1 — build** | **34** | **2026-01-31 → 2026-02-19** |
| Jan 31 – Feb 3 | 10 | RAG core, indexing, parser, chat UI. Then a testing push, then three consecutive commits fighting GitHub Actions. |
| Feb 4 – Feb 5 | 4 | Learning paths, dependency graph v1, gamification. Biggest feature expansion (`210d3bf`: 22 files, +1,148). |
| Feb 7 – Feb 10 | 9 | **The hardening arc.** `c208f3a` on Feb 8 is the largest commit in the repo: **49 files, +8,014 / −2,477**. |
| Feb 11 – Feb 19 | 11 | Docs, media, architecture diagram, the 981-line deep-dive, analytics. Zero new features. |
| *gap* | 0 | **2026-02-20 → 2026-08-07 — ~5.6 months dormant** |
| **Phase 2 — audit, deploy, extend** | **13** | **2026-08-08 → 2026-08-11** |
| Aug 8 | 2 | Security/correctness audit (13 findings) + CI-and-tooling gates that passed for the wrong reasons |
| Aug 9 | 4 | Docker docs correction, Azure OpenAI provider, Terraform infrastructure, dependency persistence |
| Aug 9 | 1 | Neo4j graph read model behind a default-off flag |
| Aug 11 | 4 | GraphQL surface + three CI-failure fixes on the same test |
| Aug 11 | 1 | Durable progress store + stuck-index reaper *(on branch, unmerged)* |

**Commits before 2026-04-01: 34. Commits on or after 2026-04-01: 13.**

The commit-message style changes completely between phases, and it's the most visible signal of growth in the whole repo. Phase 1: `"Major"`, `"Bug"`, `"Fixex"`, `"Graph Eha"`. Phase 2: multi-paragraph messages with a stated WHY, the alternatives considered and rejected with reasons, and an explicit verification line (`"Verified with apps/api/.env moved aside and all provider keys unset: 142 passed, ruff clean"`). Same author, same repo, six months apart. **Put those two lists side by side in an interview.**

---

## What is new since 2026-04-01

**13 commits, 2026-08-08 → 2026-08-11. `git diff --stat 263ce72 main` = 52 files changed, +3,347 / −133, plus `34c7490` on the current branch (+527 / −12 across 8 files).**

This is a distinct second phase with a different character from the build. Phase 1 was "make the product exist." Phase 2 is **audit, deploy, and extend the data model** — the work you only do when you intend to run something rather than demo it. Six workstreams, all new, none of which existed on 2026-02-19.

**Highest-value material for a resume, in order:** WS-16 (the security/correctness audit — credential leaks and a startup blocker), WS-18 (Terraform, and the provider-selection reasoning behind it), WS-19+WS-20 (moving graph derivation to index time, then projecting it into Neo4j), WS-21 (GraphQL, and being precise about a benefit that turned out not to be the intuitive one), WS-17 (Azure OpenAI), WS-22 (durable progress + stuck-index recovery).

### The six new subsystems

**1. Security and correctness audit — `2e53de0` (Aug 8), 13 findings, 20 files, +445/−84.**
Every item reproduced before the fix and re-verified after. The three that matter:
- **A token exfiltration path.** GitHub token injection was gated on `"github.com" in url` — which also matches `github.com.attacker.tld`. Any unauthenticated `POST /api/repos/` could send the operator's GitHub token to an attacker-controlled host. Fixed by comparing the *parsed hostname* against an exact allowlist.
- **A token leak into a public endpoint.** Git stderr containing the token was persisted to `Repository.indexing_error` and streamed by the public `/api/repos/{id}/progress` SSE endpoint. Now redacted before the exception is raised.
- **A live API key baked into the Docker image.** `COPY apps/api .` with no `.dockerignore` entry for `.env` shipped the developer's real `OPENAI_API_KEY` inside the image, plus a ~470 MB Darwin-built venv.
- Plus a **startup blocker**: `CORS_ORIGINS` typed as `List[str]` meant pydantic-settings JSON-decoded it *before* field validators ran, so docker-compose's comma-separated default raised `SettingsError` at import and `docker compose up` could never start the API. Fixed by reading it as a raw `str` and parsing in a property.

**2. CI that passed for the wrong reasons — `320fc56` (Aug 8).**
Eight fixes, each a case of a green check that proved nothing:
- CI ran `pytest tests/unit tests/integration`, but `tests/test_parser.py` sits at the `tests/` root — so **CI silently skipped ~20 cases and never once constructed a Tree-sitter parser**, while local runs covered more than CI did on the same commit.
- `pnpm install --no-frozen-lockfile` let CI repair lockfile drift that the Vercel build then rejected — a PR could go green while the production deploy failed on the same commit. (This was weakness #8 in the first draft of this dossier; it's now fixed.)
- `pnpm test` ran bare `vitest`, which only switches to run mode when it detects CI — so the documented local command hung forever inside a turbo task expecting an exit.
- `type-check` ran bare `tsc`, but Next 16 generates route types only during dev/build, and `tsconfig` includes `.next/types/**` — absent on a clean checkout. Now `next typegen && tsc --noEmit`.
- `turbo.json` `globalDependencies` pointed at a root `.env.local` that does not exist, so **a cached web build could ship a stale inlined `NEXT_PUBLIC_*` value.**

**3. Azure OpenAI as a first-class provider — `c0e68aa` (Aug 9), +459/−24.**
The factories advertised multi-provider support behind real ABCs but only ever constructed public-OpenAI clients. The approach is the interesting part: target Azure's **v1 OpenAI-compatible surface** (`<endpoint>/openai/v1`) and reuse the standard `AsyncOpenAI` client rather than `AsyncAzureOpenAI`, whose static types the OpenAI SDK's own README warns can be incorrect — so the Azure branch is *a different base URL and a deployment name*, not a second client implementation. `api_key` widened to `str | Callable[[], str]` so an Entra token provider can be injected later without either class knowing how the credential is obtained. Two Azure divergences handled explicitly: `health_check` no longer treats a missing `/models` route as unhealthy (on Azure that route enumerates *deployments* and some configurations omit it; a 404 proves the endpoint answered), and `tokenizer_model` is passed separately because tiktoken can't resolve an encoding from a deployment name. 231 lines of new tests.

**4. Terraform for a real deployed backend — `b07a400` (Aug 9), 10 files, +653.**
The gap it closes: `apps/web` was live on Vercel, `api-client.ts` reads `NEXT_PUBLIC_API_URL` and falls back to `localhost:8000`, and **nothing ever set that variable** — so the deployed frontend could not reach an API at all. Creates a DigitalOcean droplet running the compose file via cloud-init, a block volume for SQLite + Chroma + clones, volume attachment, firewall, project grouping, and **the Vercel environment variable set from the droplet's address — one stack's output feeding the other's input.** ~$7/month at the defaults.

The host-selection reasoning is the part to quote:
- **Fly.io was the plan and got rejected** because its Terraform provider is abandoned — `fly-apps/fly` is still 0.0.23 from 2023-06-22, community fork last shipped 2024-10-28. Managing Fly through that defeats the purpose of using Terraform.
- **Azure Container Apps rejected** for the opposite reason: no block-device volume type, only Azure Files over SMB/NFS — the exact configuration `sqlite.org/howtocorrupt.html` §2.1 warns against.
- **DigitalOcean chosen** as a partner provider with 13.3M downloads updated within the week, and because a droplet provides a real block device, which is what SQLite and Chroma require.

Security decisions, all deliberate and all stated: `.gitignore` covering `*.tfstate` / `*.tfvars` / `*.tfplan` committed **in the same change** so it cannot be forgotten before a first apply (state holds every resolved secret in plaintext; `sensitive = true` only redacts CLI output); `.terraform.lock.hcl` **is** committed, pinning provider checksums; both providers pinned; and **no inbound rule for 6379** — compose publishes Redis for local dev, which on a public droplet is an unauthenticated Redis facing the internet, so the DO firewall omits it *and* host ufw allows only 22 and 8000, defense in depth rather than one control.

**5. Dependency edges moved to index time, then projected into Neo4j — `0cf2937` + `2a15ec6` (Aug 9), +1,072.**

*Part one (`0cf2937`)* fixes a real architectural flaw in WS-7. `generate_graph` re-derived the entire edge set on every cache miss by **reading every source file off disk inside the request** — blocking file I/O on the event loop, latency proportional to repo size, and the 45-second in-process TTL cache existed to hide it (and being per-process, bought nothing across workers). Worse: the graph was coupled to the clone still being present, so after a redeploy or volume reset, derivation silently fell back to unresolved import strings and **produced a worse graph for the same repository with nothing indicating it had happened.** Now derivation runs once at the end of indexing, while the clone is guaranteed to exist, into a new `code_dependencies` table; the read path is a single indexed query. Notable details: the table is unique on `(repo, source, target, relation)`, added to `Repository.dependencies` with delete-orphan cascade — *without which* `DELETE /api/repos/{id}` would leave orphaned edges that union into a later re-import of the same repo — and derivation is wrapped so a failure cannot fail an otherwise good index, with blocking reads offloaded via `asyncio.to_thread`. It **reuses LearningService's existing resolution helpers rather than reimplementing them, so there is still one definition of what an edge is.**

*Part two (`2a15ec6`)* adds `core/graph/neo4j_store.py` (224 lines) as a **read model, not a source of truth**. The motivation is a capability argument, not a performance one: the graph questions that matter are transitive — *what breaks if I change this file, how does auth reach the database, are there import cycles* — and the Python path structurally cannot answer them, because `hops` is hard-capped at 2 in the API since each hop rescans the whole edge list. Quadratic in Python; a single variable-length pattern in Cypher. Four traversals ship: `reachable_from`, `blast_radius`, `shortest_path`, `import_cycles`.

The engineering discipline around it is the notable part. `neo4j_enabled` **defaults to False**. `get_graph_store()` returns `None` when disabled *or misconfigured* rather than raising, so every caller treats "no graph store" as an ordinary path. Startup verifies connectivity and applies schema, but failure only logs — an unreachable graph database must not stop the API booting. A sync failure during indexing is caught and logged; SQL edges are unaffected. Repo deletion removes the subgraph *before* the SQL rows, so a failure leaves authoritative data intact and retryable rather than orphaning a subgraph. `sync_repository` **deletes the subgraph first rather than merging**, because a MERGE-only sync leaves edges for deleted files and drifts into a union of every commit ever indexed. Uniqueness constraints on `(repo_id, path)` double as the indexes that keep MERGE off a label scan. Ingest is batched `UNWIND`+`MERGE` at 500 rows. Depth is clamped 1–10 because an unbounded variable-length pattern is a trivial way to hang the database. Degree and centrality come from `COUNT {}` subqueries rather than the GDS plugin — deliberately, because in-database GDS is AuraDB Professional and above, and Aura Graph Analytics sessions are an offline batch shape (2 GB, one concurrent session, 30-minute TTL) that does not fit a synchronous request. 245 lines of tests.

**6. GraphQL alongside REST — `98e5c76` + three CI fixes (Aug 11), +598.**
Mounted at `/graphql`, **additive not a migration**, with tests asserting every REST route still works. The motivation is a measured five-round-trip waterfall: completing a lesson POSTs (which already returns `{xp_gained, stats}`), the client discards those and calls `refreshStats()`, firing four more GETs against the same SQLite file for the same repo. `learnerDashboard` collapses the four reads into one; `completeLesson` returns the post-mutation dashboard inline so the refresh is unnecessary.

Two things here are better than the feature itself:

*Being precise about a benefit that turned out not to be the intuitive one.* Measuring it **disproved the obvious claim**: the combined resolver issues *more* SQL statements than the four REST handlers (6 vs 4 on an empty repo), because it does the same four reads plus session overhead. What it actually removes is four HTTP round trips, four dependency-injection cycles, and four session open/close pairs. The tests and docstrings say that, rather than claiming a query-count win that does not exist. **Writing down that your optimization didn't do the thing everyone assumes it does is a senior habit.**

*The Strawberry threading landmine.* Strawberry processes sync and async fields on the event loop — unlike FastAPI there is **no automatic threadpool for sync resolvers** — and `get_db` hands out a synchronous SQLAlchemy `Session`. A single sync resolver would serialize blocking SQLite calls on the loop and **stall in-flight chat SSE streams**. So every resolver is `async` and offloads via `run_in_threadpool`, and *two tests enforce it*: one reflects over `Query`/`Mutation` asserting no resolver is a `sync def`, the other asserts each blocking helper is only reached through `run_in_threadpool`. `AsyncSession` was considered and rejected — a single `AsyncSession` is documented as unsafe across concurrent tasks, which is exactly how a DataLoader batches, and greenlet isn't installed. Chat deliberately stays on REST: GraphQL's incremental delivery (`@defer`/`@stream`) is not ratified, absent from the September 2025 spec edition, RFC open since 2024-09-18, and Strawberry's support is experimental requiring `graphql-core>=3.3.0a9` against an installed stable of 3.2.11.

**The three follow-up commits are a debugging story worth telling.** `79dafb0`: CI failed 7 of 10 new tests with "Missing credentials" while they passed locally — the difference was `apps/api/.env` silently supplying a real key, so **the local green was an artifact of that machine, not evidence the tests worked.** Fixed by injecting a dummy key and not entering the `TestClient` context manager (which runs the lifespan and eagerly builds the embedding client), then verified the right way: `.env` moved aside, all three provider keys unset, 142 passed. `909e7a7`: a test asserted `"/graphql" in app.routes`, but `GraphQLRouter` registers a different path across Strawberry versions — resolving to `/graphql` locally on 0.324.0 and `""` on CI's resolution of the `>=0.240,<1.0` range. **The test was asserting the framework's route table rather than the application's behavior.** Replaced with a real query and a response check. `add5575`: the third failure on the same test was the signal the whole approach was wrong — and there's a nice detail, that **pytest truncates long set reprs with `...`, so the failure output was actively misleading about what the set contained.** Last route-table assertion replaced with a request.

**7. Durable progress + stuck-index recovery — `34c7490` (Aug 11), on branch, unmerged.**
Two bugs "whose failure mode was silence." First, **progress was write-only**: `IndexingService` wrote progress into a per-instance dict, but the SSE endpoint builds its own `IndexingService` per request, so it never saw those writes and always fell through to the database branch, which hardcodes `current_step="Unknown"` and a percentage of 0 or 100 — **the per-file progress the indexer computed could not reach any client, and the progress bar could only ever show 0% or 100%.** A per-process dict wouldn't fix it either, since indexing runs in a background task and, with >1 worker, a different process. `core/progress.py` adds a `ProgressStore` over a **capped Redis stream per repository** (`progress:{repo_id}`, MAXLEN 500) with a process-wide in-memory fallback. A *stream* rather than a key specifically because the SSE endpoint wants history — a client connecting late replays what it missed via `XRANGE` instead of seeing only the current value. Publishing never raises (progress is telemetry; a Redis blip must not fail a healthy index), and there's a test with a Redis double that raises on every call.

Second, **a killed index was unrecoverable**: only FAILED and COMPLETED are terminal, and every self-healing path keys on FAILED — so a container killed during CLONING/PARSING/EMBEDDING left the row in that state forever with no retry path through the API. **In demo mode that bricked the deployment.** `reap_stuck_indexing` runs at startup, where anything still in a transient state provably has no live indexer because the process that owned it is gone. PENDING is deliberately left alone — a repo queued but not yet started is not stuck, and failing it would break the normal import path.

### What Phase 2 changes about the story you tell

The first draft of this dossier listed ten known weaknesses. **Phase 2 closed four of them** — CI lockfile pinning, the absence of a deployed backend, graph derivation cost on the read path, and the untested multi-provider claim — and it closed them with written reasoning rather than quietly. It also *added* capability the Phase 1 architecture structurally could not reach: transitive graph traversal.

If you present this project chronologically, Phase 2 is the more senior half. Phase 1 demonstrates you can build a large product fast. Phase 2 demonstrates you can come back to your own code after six months, **find your own security bugs**, discover that your CI was proving nothing, be precise about a performance claim that turned out to be wrong, and pick infrastructure by disqualifying the obvious options for stated reasons. Those are different skills, and the second set is rarer.

### The internal split that also matters: 2026-02-08

Within Phase 1, the real boundary is commit `c208f3a`, "Major rework across 3 features, chat, graph, learn." One day, 49 files, +8,014/−2,477. It's the line between *working prototype* and *system with opinions*.

**Before (v1 shape):**

- One generic chat system prompt. Every question treated identically.
- One fixed hybrid-search weight blend for all queries.
- No caching. Every question re-embedded, re-retrieved, re-generated, every time.
- No concurrency control, no request timeout. A slow provider could pile up unbounded work per repo.
- The dependency graph asked an **LLM to generate the graph** — 50 files inside a 10,000-char prompt budget, `graph_min_edges: 15` as an accept threshold, and a retry that regenerated edges when it came back too sparse. 180-second timeout. Nondeterministic. Hallucinated edges.
- Learning content: one LLM call, `json.loads`, bare `try/except`. No cache. Personas were a name and an emoji.
- Schema changes required deleting the SQLite file.
- No demo mode, no rate limiting, no public-safety story.

**After (current shape):**

| Subsystem | What replaced it |
|---|---|
| Chat | 5-way intent classifier → 5 system prompts → 5 retrieval profiles, plus a streamed `RetrievalDiagnostics` trace ([pipeline.py](apps/api/src/core/rag/pipeline.py), 776 lines rewritten) |
| Retrieval scoring | 6 named weight profiles × 8 coefficients, including a *trivial-chunk penalty* that exists because `export {};` barrel files were outranking READMEs ([chroma_store.py:164-225](apps/api/src/core/vectorstore/chroma_store.py:164)) |
| Caching | 3 independent tiers, Redis-first with in-process fallback, answer cache keyed on retrieved chunk IDs ([chat_cache.py](apps/api/src/core/cache/chat_cache.py), new) |
| Concurrency | Per-repo `asyncio.Semaphore` (4), 2s acquire timeout returning a typed SSE backpressure error, 90s `asyncio.timeout` around generation |
| Graph | **LLM removed from the structural path entirely.** Deterministic import resolution, module rollup, component-aware pruning, edge ranking ([learning_service.py:1314-2315](apps/api/src/services/learning_service.py:1314), ~1,000 lines) |
| Learning | Persona blueprints, 4 quality gates, DB cache with 7-day TTL and prompt versioning, deterministic fallbacks ([learning_service.py:225-810](apps/api/src/services/learning_service.py:225)) |
| Schema | Additive, idempotent runtime migrations at startup ([migrations.py](apps/api/src/models/migrations.py), new) |
| Public safety | Single-repo pinning, mutation gating, 5 sliding-window rate-limit buckets, a kill switch ([demo_mode.py](apps/api/src/core/demo_mode.py) + [rate_limit.py](apps/api/src/core/rate_limit.py), both new) |

That commit alone is a legitimate standalone resume line.

---

## Architecture

### System map

```
┌─────────────────────────────────────────────────────────────────────────┐
│ BROWSER — Next.js 16 / React 19 (Vercel, output: standalone)            │
│   apps/web/src/lib/api-client.ts  ← 769 lines, 35 typed interfaces,     │
│                                     ONE contract layer for the whole app │
│   hand-rolled SSE reader: buffers across network chunks, splits on \n\n │
│   ApiError carries {status, code, retryAfterSeconds} end-to-end          │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ HTTPS  (37 endpoints)
┌──────────────────────────────▼──────────────────────────────────────────┐
│ FastAPI (Render / Docker)   apps/api/src/main.py                        │
│  lifespan: mkdir data dirs → init_db → run_pending_migrations →         │
│            vector_store.initialize()   … reverse on shutdown            │
│                                                                          │
│  /api/repos     clone · index · SSE progress · delete · file · demo seed│
│  /api/chat      session CRUD · SSE streaming answer                     │
│  /api/search    hybrid semantic search                                  │
│  /api/learning  curriculum · lessons · quiz · challenge · graph · XP    │
│  /api/platform  runtime demo flags handed to the frontend               │
│  /health        db · vector store · llm reachability · GitHub quota     │
│  /graphql   [P2] learnerDashboard (4 GETs -> 1) · completeLesson        │
│                  every resolver async + run_in_threadpool (see WS-21)   │
└──┬────────────┬──────────────┬───────────────┬──────────────┬───────────┘
   │            │              │               │              │
┌──▼─────┐ ┌────▼──────┐ ┌─────▼────────┐ ┌────▼─────────┐ ┌──▼──────────┐
│Indexing│ │RAGPipeline│ │LearningSvc   │ │Gamification  │ │ChallengeSvc │
│Service │ │           │ │              │ │Service       │ │             │
│        │ │intent →   │ │persona       │ │XP · 6 levels │ │bug_hunt     │
│clone   │ │expand ≤6 →│ │blueprint →   │ │streaks       │ │code_trace   │
│walk    │ │embed(cach)│ │retrieve →    │ │15 achieve-   │ │fill_blank   │
│parse   │ │→ hybrid × │ │LLM →         │ │ments         │ │+ SERVER-SIDE│
│chunk   │ │6 profiles │ │4 QUALITY     │ │idempotent    │ │validation   │
│embed   │ │→ dedupe   │ │GATES →       │ │award paths   │ │+ mock bank  │
│store   │ │→ LLM      │ │DB cache 7d   │ │              │ │fallback     │
│        │ │  rerank   │ │              │ │              │ │             │
│        │ │→ 18k ctx  │ │generate_graph│ │              │ │             │
│        │ │→ stream   │ │= DETERMINISTIC│ │             │ │             │
└──┬─────┘ └────┬──────┘ └─────┬────────┘ └────┬─────────┘ └──┬──────────┘
   │            │              │               │              │
┌──▼────────────▼──────────────▼───────────────▼──────────────▼───────────┐
│ SQLite via SQLAlchemy — 12 tables, 19 indexes                           │
│   repositories · code_files · code_chunks                               │
│   chat_sessions · chat_messages(+retrieval_meta JSON)                   │
│   learning_paths · learning_syllabi · learning_lessons(+quality_meta)   │
│   lesson_progress · user_xp · achievements · graph_node_interactions    │
│   code_dependencies [P2] — edges derived ONCE at index time, not per    │
│      request; unique on (repo,source,target,relation), cascade-deleted  │
├─────────────────────────────────────────────────────────────────────────┤
│ ChromaDB (persistent) — one collection per repo_id, 1/(1+distance)      │
├─────────────────────────────────────────────────────────────────────────┤
│ Redis (OPTIONAL) — 3 chat cache tiers + 5 sliding-window rate buckets   │
│   [P2] + progress:{repo_id} capped stream (MAXLEN 500) for SSE replay   │
│   every call individually try/excepted; degrades to in-process TTLCache │
├─────────────────────────────────────────────────────────────────────────┤
│ Neo4j (OPTIONAL, DEFAULT-OFF) [P2] — read model PROJECTED from          │
│   code_dependencies. Never a source of truth. Unreachable = ordinary    │
│   path, not an error. Traversals the SQL path structurally cannot do:   │
│   reachable_from · blast_radius · shortest_path · import_cycles         │
├─────────────────────────────────────────────────────────────────────────┤
│ ./data/repos/<owner>/<name> — shallow clones kept for graph extraction  │
└─────────────────────────────────────────────────────────────────────────┘

External: GitHub (git clone --depth 1, REST rate_limit probe)
          OpenAI | Azure OpenAI | Anthropic | Ollama   (chat)
          OpenAI | Azure OpenAI | Ollama               (embeddings)

Deployed [P2]: Vercel (web) + DigitalOcean droplet & block volume (api),
  both provisioned by infra/terraform — the droplet's IP is written into
  Vercel's NEXT_PUBLIC_API_URL as one stack's output feeding the other's
  input. Firewall opens 22 and 8000 only; 6379 deliberately absent.
```

### Request lifecycle: one question, end to end

This is the trace to walk an interviewer through. `[MEASURED]` values are configured limits; `[EST]` latencies are not benchmarked.

```
  ① POST /api/chat/sessions/{id}/messages
     ├─ session lookup                                          ~1 ms
     ├─ assert_demo_repo_access()          (no-op unless DEMO_MODE)
     ├─ enforce_demo_soft_limit(req,"chat") 18/60s per IP, sliding window
     ├─ load prior messages ORDER BY created_at ASC
     ├─ _build_history(): newest-first until 1,800-token budget, then reverse
     └─ persist user message, set session title from first 100 chars

  ② acquire per-repo semaphore                    max 4, 2s timeout
     └─ on timeout → SSE {type:error, code:CHAT_REPO_CONCURRENCY_LIMIT}
        (typed backpressure, NOT a hang and NOT a 500)

  ③ async with asyncio.timeout(90)  ── everything below is inside this

  ④ RETRIEVE  ─────────────────────────────────────── [EST] 0.8–1.5s cold
     ├─ classify_intent_async()
     │    deterministic phrase scoring across 5 intents (3 pts/hit)
     │    + regex bonuses; LLM tiebreak ONLY on an exact top-2 tie
     ├─ intent → profile   (overview→docs_first, tech_stack→stack, …)
     ├─ _expand_query() → ≤6 variants
     │    7-key synonym map + intent-specific + entry-point detector
     ├─ retrieval cache lookup, key = (repo, normalized_q, intent,
     │    profile, context_files)                       10 min TTL
     └─ per variant:  embed (1h cache) → hybrid_search(limit×4 oversample)
          scoring:  α·vector + (1−α)·min(Σ8 boosts, 1.5) − trivial_penalty
          merge across variants by MAX score per chunk id

  ⑤ RERANK  ──────────────────────────────────────── [EST] 1–2s cold
     top-18 → LLM → strict JSON {"ranked_ids":[…]}
     fallback chain: strict parse → outermost-brace → UUID-regex scavenge
                     → original order.  Unranked chunks appended, never dropped.

  ⑥ EMIT  sources  (top 6 chunks + line ranges)
     EMIT  meta     (intent, profile, grounding, retrieval_ms, rerank_ms)
           grounding = high/medium/low — an OVERVIEW answer that retrieved
           zero docs-path chunks is downgraded to "medium" and says so

  ⑦ GENERATE ─────────────────────────── first token [EST] ~2–4s cold
     ├─ answer cache lookup, key = (repo, question, intent,
     │    TOP-12 CHUNK IDS, model)                      30 min TTL
     │    └─ HIT → still streams, in 320-char slices, so the UI can't tell
     ├─ _build_context(): grouped by file, "### Files Referenced" index,
     │    1,800 char/chunk cap, 18,000 char total budget, explicit
     │    "*Context truncated due to budget.*" marker when it bites
     └─ stream tokens → SSE {type:content} … → {type:done}

  ⑧ PERSIST assistant message WITH retrieval_meta JSON
     → every answer carries its own retrieval trace, queryable months later

  ⑨ finally: release semaphore
```

**Why ⑧ matters.** Most RAG side-projects cannot answer "why did it say that?" after the fact. Here the intent, profile, expanded queries, candidate count, whether rerank ran, cache-hit state, and per-stage latency are written onto the message row. You can open the DB and reconstruct the reasoning path for any answer that was ever produced.

### The seven places AI runs — and what happens when each one fails

This table is the single best artifact in this dossier for an AI-engineering interview. "We use AI" is not a design. Seven call sites with seven different caching, validation, and failure postures is.

| # | Call site | Cached? | Validation | On failure |
|---|---|---|---|---|
| 1 | Intent tiebreak | No | Response must contain one of the allowed intent strings | Fall back to deterministic top-scoring intent |
| 2 | Listwise rerank (top-18) | No | Returned IDs checked against the exact set sent | Brace-extract → UUID-regex scavenge → original order |
| 3 | Answer generation | **Yes, 30 min**, keyed on chunk IDs | Grounding level computed and surfaced to the user | Typed SSE error with a code; timeout at 90s |
| 4 | Curriculum generation | **Yes, 7 days**, DB-backed, prompt-versioned | Exactly 4 modules; ≥2 lessons each; ≥2 persona terms | Deterministic pillar-based syllabus, reason recorded |
| 5 | Lesson generation | **Yes, 7 days**, DB-backed, prompt-versioned | ≥4 of 6 required sections; persona density ≥0.2; ≥1 surviving validated code ref | Deterministic 6-section markdown + synthesized diagram, reason recorded |
| 6 | Challenge generation | No | Pydantic-typed schema per challenge type | Deterministic mock challenge bank |
| 7 | Graph node descriptions | Yes (in demo mode) | ≤18 words, JSON repaired before parse | Silently skipped — **off by default** |

Two more validators sit *outside* the model entirely and are the reason the product feels trustworthy:

- **Citation validation** — every `code_reference` is filtered against an allowlist of indexed paths, extension-checked, existence-checked against the `CodeFile` table, and line-clamped against the real line count ([learning_service.py:920-962](apps/api/src/services/learning_service.py:920)). Deduped by `file:start:end`, capped at 8.
- **Mermaid quality scoring** ([learning_service.py:968-1174](apps/api/src/services/learning_service.py:968)) — rejects a diagram if it has no diagram keyword, matches the classic `A -->` toy pattern, has <3 edges, has <4 meaningful labels, has ≥60% single-token labels, has ≥60% generic labels drawn from an 11-word blocklist (`node`, `component`, `service`, `module`, `system`, `process`, `step`, `input`, `output`, `start`, `end`), or fails to mention real file/directory tokens from the retrieved set. Anything rejected is replaced by a deterministically synthesized structural map that buckets the validated file references into entry / orchestration / core / data / support layers. **A lesson diagram in this product is either grounded in real files or generated from real files. It is never a decorative lie.**

### Data model

12 tables, 19 indexes, all `String(36)` UUID primary keys, `cascade="all, delete-orphan"` from `Repository` downward so a repo delete is a single statement.

| Table | Role | Notable columns |
|---|---|---|
| `repositories` | Index root | `status` enum (pending→cloning→parsing→embedding→completed/failed), `last_commit_sha`, `total_files`, `total_chunks`, `indexing_error` |
| `code_files` | Per-file metadata | `content_hash` (SHA-256), `line_count` — *this is the ground truth citations get clamped against*, `imports` JSON |
| `code_chunks` | Embeddable units | `chunk_type`, `chunk_name`, `start_line`/`end_line`, `context_before` (imports), `docstring`, `content_hash` |
| `chat_sessions` / `chat_messages` | Conversation | **`retrieval_meta` JSON — the per-answer retrieval trace** |
| `learning_syllabi` | Curriculum cache | `persona`, `syllabus_json`, `expires_at` |
| `learning_lessons` | Lesson cache | `lesson_json`, **`quality_meta`**, **`prompt_version`**, `expires_at` |
| `lesson_progress` | Completion | `quiz_score`, `challenges_perfect`, scoped by `(repo, lesson, persona)` |
| `user_xp` | Gamification state | `total_xp`, `level`, `streak_days`, `longest_streak`, unique per repo |
| `achievements` | Unlocks | **unique index on `(repository_id, achievement_key)`** — idempotency enforced at the schema level |
| `graph_node_interactions` | Explore tracking | **unique index on `(repository_id, node_id)`** — you cannot farm XP by re-clicking |
| `learning_paths` | Vestigial | Phase-2 scaffold, unused |

The two unique indexes are the interesting part: **idempotency is enforced in the schema, not in application logic.** A double-click, a React strict-mode double-render, or a page refresh cannot inflate XP, because the database refuses the duplicate.

### Cost model `[DERIVED unless noted]`

| Operation | Calls | Cost |
|---|---|---|
| Index a 1,000-file repo | ~1.5M embedding tokens | **~$0.03** |
| Index at the 5,000-file ceiling | ~7.5M embedding tokens | **~$0.15** |
| One cold chat answer | 6 embeddings + 1 rerank + 1 completion | **~$0.02–0.04** |
| One cached chat answer | 0 | **$0.00** |
| One full persona track (curriculum + 8–16 lessons + quizzes) | 12–20 completions | **~$0.15–0.40** |
| Dependency graph, any size | **0 LLM calls on the default path** | **$0.00** |
| Public demo, a few hundred visitors/day `[EST]` | mostly cache hits | **~$1–5/day** |

The graph row is the one to point at. Removing the LLM from that path didn't just fix determinism — it took the most-viewed feature's marginal cost to zero and its p99 latency off the provider's SLA entirely.

### Storage decisions and their escape hatches

SQLite because the target user is one developer self-hosting, and `DATABASE_URL` is a plain SQLAlchemy URL so Postgres is a one-variable swap. Chroma because it is embedded and zero-config; `vector_db_type` and `qdrant_url` exist as the documented exit. Redis is entirely optional — every cache and every rate limiter degrades to an in-process structure, and `/api/cache/stats` reports which backend is actually live so you're never guessing in production.

---

## Workstreams

### WS-1: Repository ingestion and indexing pipeline

- **What it does and why:** Turns a GitHub URL into a searchable index. Everything else is downstream. It has to be fast enough that a user doesn't abandon the page, resilient enough that one malformed file doesn't kill a 3,000-file run, and idempotent enough that re-indexing doesn't leave duplicate chunks.
- **Files:** [indexing_service.py](apps/api/src/services/indexing_service.py) (582) · [repo_manager.py](apps/api/src/core/github/repo_manager.py) (195) · [repos.py](apps/api/src/api/routes/repos.py) (289) · [seed_demo.py](apps/api/src/demo/seed_demo.py) (209) · tests: [test_indexing.py](apps/api/tests/unit/test_indexing.py) (168), [test_repo_manager.py](apps/api/tests/unit/test_repo_manager.py) (79)
- **Dates:** 2026-01-31 → 2026-02-10 (7 commits)
- **New since 2026-04-01?** No — nothing is.
- **Technique named precisely:** Shallow single-branch clone (`--depth 1 --single-branch --branch <detected>`) with `git ls-remote --symref HEAD` for default-branch detection; `os.walk` with in-place `dirs[:]` pruning against a 14-entry skip-set; SHA-256 content hashing per file *and* per chunk; **destructive-rebuild indexing** — delete SQL rows and drop the Chroma collection before every run ([indexing_service.py:140-150](apps/api/src/services/indexing_service.py:140)); heading-boundary markdown chunking with a 2,200-char cap and greedy line accumulation; batched `session.add_all()` per file.
- **Security detail worth citing:** `parse_github_url` sanitizes owner and repo against `[A-Za-z0-9._-]+` and rejects `.`/`..`/path separators; `get_file_content` resolves the target and calls `Path.relative_to(repo_root)` to reject traversal outside the clone ([repo_manager.py:27-51, 172-195](apps/api/src/core/github/repo_manager.py:27)). The file-content endpoint is user-facing and takes a raw `path` query parameter — the traversal guard is doing real work.
- **The hardest part:** Two bugs that shaped the whole design.

  **Session and event-loop lifetime in background tasks.** FastAPI's `BackgroundTasks` run *after* the response, by which point the request-scoped SQLAlchemy session is closed. The fix ([repos.py:29-49](apps/api/src/api/routes/repos.py:29)) makes the background callable synchronous, builds a *fresh* session from the factory and a *fresh* event loop via `asyncio.new_event_loop()`, and closes both in `finally`. It looks strange until you know why — which makes it a great thing to be asked about.

  **The Python closure-in-loop bug in the Chroma batch writer.** The original built lambdas inside a `for` loop over batches and handed them to a `ThreadPoolExecutor`; every lambda captured the same mutable loop variables, so all of them wrote the *last* batch. Result: silently wrong data, no exception. The fix is default-argument binding at lambda-definition time, and [chroma_store.py:96-106](apps/api/src/core/vectorstore/chroma_store.py:96) still carries the comment `# Fix: Capture batch values at lambda definition time using defaults`. Called out by name in the first feature commit ("Fix critical bugs: ChromaDB closure").

  The standing design tension is **idempotency vs. speed**. Content hashes are stored per chunk — exactly what incremental re-indexing needs — but the pipeline throws the index away and rebuilds. Deliberate: partial re-indexing against a stale vector store produces phantom citations, and a wrong citation is worse than a slow rebuild.
- **Scale it demonstrably handles:**
  - `[MEASURED]` Caps: 5,000 files/repo, 500 KB/file, 14 skipped directory patterns, ~30 extensions plus extensionless Ruby (`Gemfile`, `Rakefile`, `config.ru`).
  - `[MEASURED]` Repos actually cloned and indexed during development, from `apps/api/data/repos/`: **cal.com, documenso, encode, expressjs/express, facebook, tiangolo/fastapi, httpie, lukevella/rallly, makeplane/plane, shadcn-ui, vercel/nextjs-subscription-payments, realworld-apps**, plus a personal portfolio. A deliberately hostile spread: TS monorepos, Python frameworks, Ruby, multi-app workspaces.
  - `[MEASURED]` **44 accumulated Chroma collection segments** (181 MB) and a **103 MB** SQLite metadata DB — the physical residue of ~44 full index builds in 19 days.
  - `[MEASURED]` Current state after cleanup: `vercel/nextjs-subscription-payments` → 63 files / 167 chunks; a portfolio repo → 108 files / 1,105 chunks; 1,272 live embeddings.
  - `[DERIVED]` ~$0.03 per 1,000-file index; ~$0.15 at the ceiling — cheap enough that destructive rebuild is affordable.
  - `[EST]` ~1,000-file TS repo: 20–35 s clone, 30–60 s parse, 60–120 s embed at default sequential embedding. **2–4 minutes end to end.** Not benchmarked.
- **Proposed lenses:** `backend 4` — background job orchestration, session lifetime, batching, idempotency, path-traversal defense. `systems 3`. `swe 4` — two subtle silent-corruption bugs found, fixed, and documented in-place. **PROPOSED, not a verdict.**

---

### WS-2: Multi-language Tree-sitter semantic parser

- **What it does and why:** Splits source on *syntactic* boundaries — whole functions, whole classes, individual methods — instead of line counts. Fixed-size chunking cuts a function in half and destroys the thing you were trying to retrieve.
- **Files:** [tree_sitter_parser.py](apps/api/src/core/parser/tree_sitter_parser.py) (357) · [test_parser.py](apps/api/tests/test_parser.py) (138) · [test_rag_language_mapping.py](apps/api/tests/unit/test_rag_language_mapping.py) (31)
- **Dates:** 2026-01-31 → 2026-02-08 (6 commits)
- **New since 2026-04-01?** No.
- **Technique named precisely:** Tree-sitter CST traversal driven by a **declarative per-language config table**. Nine grammars, each described by five keys — `function_types`, `class_types`, `import_types`, `class_body_types`, plus optional `function_name_types` / `class_name_types` overrides. Traversal is a recursive `visit(node, in_class)` threading a boolean so top-level functions and class methods chunk differently. Dedup via a `(start_line, end_line, chunk_type, name)` tuple set, required because the recursive descent legitimately reaches the same node by more than one path (exported wrappers, decorated definitions, nested declarations). Parser instances are `@lru_cache(maxsize=20)`'d. Top-of-file imports are prepended to every chunk as `context_before`, so a retrieved function carries knowledge of its dependencies. Python docstrings are extracted structurally — first `expression_statement` → `string` inside the `block` — not by regex.
- **The hardest part:** Nine grammars agree on nothing. "Name of this thing" is `identifier` in Python, `type_identifier` in Go and TypeScript, `constant` in Ruby, `field_identifier` in some C++ contexts. "Body of this class" is `block` / `class_body` / `declaration_list` / `field_declaration_list` / `body_statement` depending on language. A per-language `if` ladder would be unreadable and unextendable.

  The solution is **two-stage name resolution over an ordered fallback list**: try every candidate type as a *direct child* first, and only if all miss, recurse into descendants ([tree_sitter_parser.py:323-332](apps/api/src/core/parser/tree_sitter_parser.py:323)). The ordering is load-bearing and non-obvious — in `class Foo extends Bar`, a plain descendant search returns `Bar`. Class-level defaults (`DEFAULT_FUNCTION_NAME_TYPES`, `DEFAULT_CLASS_NAME_TYPES`, `DEFAULT_CLASS_BODY_TYPES`) mean most languages need zero overrides and **a tenth language is a six-line config entry.**

  Second hard part: **failing safely**. A grammar that throws, or a file with no recognizable structure, must not silently produce zero chunks — that's a hole in the index nobody notices. Two fallbacks: a whole-file `MODULE` chunk (truncated at 4,000 chars) when parsing succeeds but finds nothing, and a caller-side fall-through to raw indexing when the parser raises ([indexing_service.py:413-417](apps/api/src/services/indexing_service.py:413)).
- **Scale:** `[MEASURED]` 9 grammars, ~30 extensions. `[EST]` Tree-sitter runs 1–10 MB/s of source; parsing is never the bottleneck — embedding is. `[EST]` A 1,000-file TS repo yields ~2,500–4,000 chunks.
- **The literature to cite:** AST-aware chunking (cAST, EMNLP 2025 Findings) reports **+4.3 Recall@5 on RepoEval and +2.67 Pass@1 on SWE-bench** over line-based splitting. Cite it as the *motivation*; do not claim you reproduced it.
- **Proposed lenses:** `ai 3` — retrieval-quality engineering, not modeling. `backend 4`. `swe 5` — the single best "show me code you're proud of" file in the repo; it's the one place the abstraction genuinely earns its keep. **PROPOSED.**

---

### WS-3: Vector store and profile-weighted hybrid retrieval

- **What it does and why:** Pure vector similarity is bad at code. Ask "where is `handleLogin` defined" and cosine happily returns five files that *discuss* authentication and never the one containing the symbol. This layer blends vector score with lexical and structural signals, and — critically — **varies the blend by question type**.
- **Files:** [chroma_store.py](apps/api/src/core/vectorstore/chroma_store.py) (368) · [test_retrieval_scoring.py](apps/api/tests/unit/test_retrieval_scoring.py) (86) · [search.py](apps/api/src/api/routes/search.py) (82)
- **Dates:** 2026-01-31 → 2026-02-08 (7 commits; profiles arrived in the Feb 8 rework)
- **New since 2026-04-01?** No.
- **Technique named precisely:** Oversample-then-rescore. Request `limit × 4` from Chroma, convert distance to similarity as `1 / (1 + distance)`, then:

  ```
  final = α · vector_score + (1 − α) · min(Σ boosts, 1.5) − trivial_penalty
  ```

  Eight independent boosts: stopword-filtered keyword matches in content · query-term matches in the **file path** · an important-file pattern boost (entry/config/route/model → `index`/`main`/`app`/`server`/`config`/`route`/`handler`) · a chunk-type boost · a docs boost · a manifest boost (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`) · a location-profile **compacted-path match** (strip `/` from both query and path, substring-test — this is what makes "where is user profile page" find `app/user/profile/page.tsx`) · an error-focus boost for content containing `error|exception|raise|throw|retry|fallback`.

  **Six named profiles** each set all eight coefficients. `docs_first` runs α=0.45 with a 0.45 docs boost and a 0.55 trivial penalty; `code_first` runs α=0.65 with a 0.08 docs boost and a 0.30 penalty. Same index, six different lenses. A `path_allowlist` parameter supports @-file scoping from the UI.
- **The hardest part: the barrel-file problem.** Monorepos are full of `packages/ui/index.ts` containing exactly `export {};`. They're short, so they embed to a dense generic vector that lands near almost any query, and they're named `index.ts`, so the entry-point pattern boost fires too. In testing they were beating `README.md` on *"what are the main features of this application?"* — the single most important question the product answers.

  Three coordinated fixes: (1) `_is_trivial_chunk` detects re-export stubs and subtracts a flat penalty; (2) the **indexer** refuses to create a `file_summary` chunk for a trivial re-export at all ([indexing_service.py:185-191, 450](apps/api/src/services/indexing_service.py:185)) — the same predicate implemented at *both ends of the pipeline*, deliberately, because catching it at index time is cheaper and catching it at query time is the safety net for already-indexed repos; (3) the `docs_first` profile exists so overview questions weight README evidence over dependency lists.

  There is a regression test locking this down using real content from the Documenso repo, and a golden eval case in [chat_quality_cases.json](apps/api/tests/evals/chat_quality_cases.json) asserting `no_dependency_only_inference` — *"don't tell me what this app does by reading its package.json."* That eval file is small but it is the most senior artifact in the repo: it encodes a **quality** requirement, not a correctness one.
- **Scale:** `[MEASURED]` 6 profiles × 8 coefficients = 48 tuned constants. 4× oversampling, `max(limit×3, 24)` candidates per expanded query → a 6-variant expansion touches up to ~576 candidate rows before dedup. 1,272 vectors currently resident. `[EST]` Chroma brute-force cosine over 10k–50k dim-1536 vectors: ~10–40 ms; the eight-boost rescoring is O(candidates) string work, ~1–3 ms.
- **Own this weakness before they find it:** the "keyword" half is substring matching over chunk content, not true BM25, and fusion is a weighted linear blend rather than Reciprocal Rank Fusion. Both are the textbook upgrades. State it first, then explain the trade — BM25 needs a second index, and RRF discards score magnitude, which the profile weights depend on.
- **Proposed lenses:** `ai 4` — real IR work with a documented failure case and a permanent regression guard. `backend 3`. `swe 4` — the same invariant enforced at two layers, with a comment explaining why. **PROPOSED.**

---

### WS-4: Intent-routed RAG chat pipeline with SSE streaming

- **What it does and why:** The product's front door. Converts a natural-language question into a grounded, cited, streaming answer. The piece most likely to get probed hardest in an interview.
- **Files:** [pipeline.py](apps/api/src/core/rag/pipeline.py) (776) · [chat.py](apps/api/src/api/routes/chat.py) (307) · [chat-interface.tsx](apps/web/src/components/chat/chat-interface.tsx) (414) · [api-client.ts:403-442](apps/web/src/lib/api-client.ts:403) · tests: [test_rag_intents.py](apps/api/tests/unit/test_rag_intents.py), [test_rag.py](apps/api/tests/unit/test_rag.py), [test_chat_pipeline.py](apps/api/tests/integration/test_chat_pipeline.py)
- **Dates:** 2026-01-31 → 2026-02-08 (6 commits; substantially rewritten Feb 8)
- **New since 2026-04-01?** No.
- **Technique named precisely:**
  1. **Deterministic intent classification with an async LLM tiebreak.** `_score_intents` scores all five intents against phrase lists (3 pts/hit) plus regex bonuses (`\b(feature|overview|purpose)\b` → +2 overview; `\b(api|handler|service|class|function|method)\b` → +1 implementation). Only on an exact top-2 tie, and only if `chat_intent_llm_tiebreak_enabled`, does one cheap uncached LLM call arbitrate. Zero score → default `IMPLEMENTATION`. **Say this out loud: the LLM is the tiebreak, not the classifier.**
  2. **Intent → profile → system prompt routing.** Five prompt templates with numbered rules. The `OVERVIEW` prompt literally says *"Do NOT infer product features only from package dependencies unless docs are absent."* That's a prompt-level defense mirroring the retrieval-level `docs_first` profile and the eval assertion — **three layers, one bug.**
  3. **Query expansion, ≤6 variants.** A 7-key synonym map (`auth → authentication/authorization/login/session/token`), intent-specific additions, and an entry-point detector that appends the literal `"index.ts OR index.js OR main.py OR app.tsx OR server.ts"`.
  4. **Multi-query merge by max score per chunk ID** — a chunk surfacing for three variants keeps its best score rather than being triple-counted.
  5. **LLM listwise rerank** over the top 18 returning `{"ranked_ids":[…]}`, validated against the exact ID set sent, with a **UUID-regex scavenging fallback** (`[0-9a-fA-F-]{32,36}`) for malformed responses, then a final fallback to original order. Unranked chunks are appended, never dropped.
  6. **Context assembly under a hard budget** — grouped by file, a "### Files Referenced" index first, 1,800-char per-chunk truncation, a running total against 18,000 chars, and an explicit `*Context truncated due to budget.*` marker so the model knows it has a partial view. Language fences inferred per extension across 13 languages.
  7. **History budgeting** — newest-first accumulation to a 1,800-token (≈7,200-char) budget, then reversed to chronological. Implemented in *two* places (route and pipeline) with the same 4-chars-per-token approximation.
  8. **SSE protocol** — four typed event kinds (`sources`, `meta`, `content`, `done`) plus three typed errors (`CHAT_REQUEST_TIMEOUT`, `CHAT_GENERATION_ERROR`, `CHAT_REPO_CONCURRENCY_LIMIT`), served with `X-Accel-Buffering: no` so nginx-class proxies don't buffer the stream into uselessness.
  9. **Cached-answer replay** — a cache hit still *streams*, in 320-char slices, so the UI never has to distinguish cached from live ([pipeline.py:763-767](apps/api/src/core/rag/pipeline.py:763)).
- **The hardest part: making an LLM-in-the-loop path observable and honest about its own confidence.**

  *Observability.* A `RetrievalDiagnostics` dataclass carries intent, profile, the actual expanded queries, candidate count, rerank flag, retrieval ms, rerank ms, cache-hit, and grounding. It is emitted mid-stream as a `meta` event **and** persisted onto the `ChatMessage` row as `retrieval_meta` JSON. You can open the database months later and ask *why did it answer that?* Most side-project RAG has no answer.

  *Honesty.* `grounding` is computed `high`/`medium`/`low` by checking whether an OVERVIEW-intent answer actually retrieved any docs-path chunk ([pipeline.py:483-487](apps/api/src/core/rag/pipeline.py:483)). The system tells the user when it is answering from weak evidence.

  The other genuinely fiddly part is **SSE escaping**, listed among the critical bugs in the very first feature commit. Every payload goes through `json.dumps` into `data: {...}\n\n`; the failure mode is a code chunk containing a newline or quote silently truncating an event and desynchronizing the client parser. The frontend has the matching discipline: it accumulates a buffer across network reads and only parses complete lines ([api-client.ts:419-439](apps/web/src/lib/api-client.ts:419)), because a TCP read has no reason to align with an event boundary.
- **Scale:** `[MEASURED]` 90 s request timeout · 4 concurrent chats/repo with 2 s queue wait · 20-message / 1,800-token history · 18,000-char context · ≤6 expanded queries · 24 retrieval candidates · 18 rerank candidates · caches at 30/10/60 min.
  `[DERIVED]` Cold answer = 6 embeddings + 1 rerank + 1 completion ≈ **$0.02–0.04**. `[EST]` Cold first token ~2–4 s; retrieval-cache-warm ~150–400 ms; full answer-cache hit <100 ms. `[EST]` ~20–40 concurrent streams on one instance before the provider becomes the bottleneck. Not benchmarked.
- **Proposed lenses:** `ai 5` — routing, expansion, listwise reranking, context budgeting, grounding self-assessment, persisted retrieval traces. The strongest AI-engineering artifact here. `backend 4`. `frontend 3`. **PROPOSED.**

---

### WS-5: Three-tier chat cache and concurrency hardening

- **What it does and why:** A public demo where every visitor asks "what does this repo do?" would otherwise re-run the entire pipeline per visitor. This makes repeated and near-repeated questions nearly free, and stops a slow provider from becoming an unbounded queue.
- **Files:** [chat_cache.py](apps/api/src/core/cache/chat_cache.py) (206, new) · [llm_cache.py](apps/api/src/core/cache/llm_cache.py) (73) · [dependencies.py](apps/api/src/dependencies.py) (124) · [chat.py:39-49, 192-212](apps/api/src/api/routes/chat.py:39)
- **Dates:** 2026-02-08 (single day)
- **New since 2026-04-01?** No.
- **Technique named precisely:** Three TTL caches with **semantically distinct key schemas**, each SHA-256-hashed over a canonical JSON payload:
  - *Embedding*: `(query, embedding_model)`, 1 h.
  - *Retrieval*: `(repo_id, normalized_query, intent, profile, sorted context_files)`, 10 min. Normalization lowercases, strips outside `[a-z0-9_\-./ ]`, collapses whitespace — so "How does AUTH work?" and "how does auth work" share an entry.
  - *Answer*: `(repo_id, question, intent, **top-12 retrieved chunk IDs**, llm_model)`, 30 min.

  Redis-first with in-process `cachetools.TTLCache` fallback (2,048 / 512 / 512 entries), every Redis call individually try/excepted. `/api/cache/stats` reports per-tier size/maxsize/ttl plus which rate-limit backend is live.

  Concurrency: a module-level `Dict[repo_id, asyncio.Semaphore]` guarded by a `threading.Lock` for creation — correct, because FastAPI runs sync dependencies in a threadpool — acquired with `asyncio.wait_for(..., 2.0)`, released in `finally`, wrapped in `async with asyncio.timeout(90)`.
- **The hardest part: cache invalidation without an invalidation mechanism.** The naive answer key is `(repo, question)`, which goes stale the instant the repo is re-indexed and starts confidently citing line numbers that no longer exist. Explicit invalidation means tracking every dependency edge from an index build to every derived artifact. Folding the **retrieved chunk IDs** into the key sidesteps the entire problem: chunk IDs are regenerated on every index, so re-indexing invalidates the whole answer cache automatically, with zero invalidation code. **The key *is* the dependency set** — the same idea as content-addressed build systems, applied where people usually don't. The graph cache uses the same trick with the repo's `updated_at` timestamp.

  Secondary: the semaphore dict is created lazily from async handlers, and `asyncio.Semaphore` binds to the running loop. A `threading.Lock` around dict creation is the right primitive (not an `asyncio.Lock`); getting it wrong produces a race that only appears under real concurrency.
- **Scale:** `[MEASURED]` 3 tiers, 3,072 in-process entries, TTLs 3600/600/1800 s, 4 concurrent/repo, 2 s queue wait, 90 s hard timeout. `[EST]` A demo pinned to one repo with a handful of starter prompts should see **60–80% answer-cache hit rate** after warm-up. `pnpm demo:prewarm` exists to warm exactly this before traffic arrives.
- **Proposed lenses:** `backend 5` — layered caches, content-addressed keys, graceful degradation, exposed stats, bounded concurrency, typed backpressure. `systems 4`. `ai 3`. **PROPOSED.**

---

### WS-6: Persona-driven learning engine (V1 → V2 rewrite)

- **What it does and why:** Generates a 4-module curriculum tailored to *why* you're reading this codebase, then generates each lesson on demand with real file references and an architecture diagram. This is the feature that separates the product from "chat with your repo."
- **Files:** [learning_service.py:38-1313](apps/api/src/services/learning_service.py:38) (~1,275 of the 2,360 lines) · [learning.py](apps/api/src/api/routes/learning.py) (514) · [learning.py models](apps/api/src/models/learning.py) (144) · frontend: [lesson-view.tsx](apps/web/src/components/learning/lesson-view.tsx) (626), [syllabus-view.tsx](apps/web/src/components/learning/syllabus-view.tsx), [persona-selector.tsx](apps/web/src/components/learning/persona-selector.tsx), [quiz-view.tsx](apps/web/src/components/learning/quiz-view.tsx), [MermaidDiagram.tsx](apps/web/src/components/learning/MermaidDiagram.tsx) (523) · tests: [test_learning_v2_service.py](apps/api/tests/unit/test_learning_v2_service.py) (295), [test_learning_v2_routes.py](apps/api/tests/integration/test_learning_v2_routes.py) (191)
- **Dates:** 2026-02-01 → 2026-02-09 (10 commits)
- **New since 2026-04-01?** No — but **partially reworked within the project**. V1 and V2 coexist behind `LEARNING_V2_ENABLED`; V2 falls back to V1 on any exception; V1 remains fully functional. A real feature-flagged migration, not a rewrite-in-place.
- **Technique named precisely:**
  - **Persona blueprints** ([learning_service.py:54-83](apps/api/src/services/learning_service.py:54)) — each persona is a data structure with a `retrieval_query` (**so a security auditor's retrieval differs, not just their prompt**), a `tone`, a `mission`, four `pillars`, and `relevance_terms` used later as an automated quality signal.
  - **Four quality gates.** Curriculum rejects and falls back if: module count ≠ 4, any module has <2 lessons, or <2 persona relevance terms appear anywhere. Lesson rejects if: <4 of 6 required headings present (score <0.66), persona term density <0.2, or zero validated code references survived. Every rejection writes a `quality_meta` blob with the specific `fallback_reason`, persisted alongside the content.
  - **Citation validation against database ground truth** — described in the Architecture section above; this is the mechanism that makes lesson citations resolve.
  - **Mermaid quality scoring** — an eight-condition rejection filter plus a deterministic structural-map synthesizer, also described above.
  - **DB-backed cache with prompt versioning** — `LearningSyllabus` / `LearningLesson` store the JSON plus `prompt_version` (`learning_v2_1`) and `expires_at` (7-day TTL). Bumping the prompt version is how a prompt change rolls out without stale content; `force_regenerate` is exposed on the route. A `CacheInfo` object (`source`, `generated_at`, `expires_at`, `prompt_version`, `cache_hit`) goes back to the client so the UI can show provenance.
  - **Defensive JSON recovery** — `_extract_json_block` (strip fences, take outermost `{…}`) then `_repair_json_like`, which strips `//` and `/* */` comments, removes trailing commas, inserts missing commas between `}{`, and converts single-quoted keys **and** values to double-quoted with inner-quote escaping.
  - **Frontend Mermaid rendering** ([MermaidDiagram.tsx](apps/web/src/components/learning/MermaidDiagram.tsx)) re-sanitizes model output client-side (quoting labels containing parens or braces), normalizes the rendered SVG (rewrites `width`/`height` from `viewBox`, strips `max-width`, injects a font-size stylesheet), and provides pan/zoom to 8× with a fullscreen canvas and fit-to-view. Because *even after server-side validation*, LLM Mermaid still breaks the renderer.
- **The hardest part: grading generated content without a human in the loop.** "Is this lesson good?" has no ground truth and no cheap oracle. The approach decomposes subjective quality into objective proxies, each targeting a specific observed failure mode — structural completeness (models drop sections in long prompts), persona relevance (models regress to generic content), grounding (models invent file paths), diagram specificity (models emit `A --> B --> C` when they don't know the architecture). Each proxy has a threshold, a deterministic fallback, and a recorded reason. Fallbacks always produce something usable, so a bad generation degrades to a plain-but-correct lesson rather than an error page.

  **This is the answer to "how do you evaluate LLM output?"** — neither "vibes" nor "an LLM judge," but a decomposed rubric with recorded failure attribution. There are unit tests asserting a generic diagram is rejected and a contextual one accepted.

  Second hard part: **regenerating without churn.** A lesson must be stable across visits (users bookmark them; XP is awarded against lesson IDs) but must not be stale forever. Hence the 7-day TTL + prompt-version keying + an explicit force-regenerate escape hatch.
- **Scale:** `[MEASURED]` 4 personas × 4 modules × 2–4 lessons = **32–64 distinct generated lessons per repository**. Retrieval: 24 docs for curriculum, 20 per lesson. 7-day cache. Minimum 550 words, 6 required sections, ≤8 validated citations per lesson.
  `[DERIVED]` One full persona track ≈ 12–20 LLM calls ≈ **$0.15–0.40**. The 7-day cache is what makes a public demo of this survivable. `[EST]` Curriculum 6–12 s cold, lesson 8–20 s cold, both <100 ms cached.
- **Proposed lenses:** `ai 5` — persona-conditioned retrieval, structured generation, automated quality gates, grounded citation validation, prompt versioning. Applied-LLM product engineering, not prompt-and-pray. `backend 4`. `frontend 3`. **PROPOSED.**

---

### WS-7: Deterministic dependency graph engine (Graph v2.1 / v2.2)

- **What it does and why:** Builds a navigable map of the repository — which file imports which, rolled up to modules when the file graph is too dense to read. Exists because the fastest way to understand an unfamiliar system is to see its shape. **The most algorithmically substantial subsystem in the project.**
- **Files:** [learning_service.py:1314-2315](apps/api/src/services/learning_service.py:1314) (~1,000 lines) · [learning.py:79-150](apps/api/src/models/learning.py:79) · [test_learning_graph_v2.py](apps/api/tests/unit/test_learning_graph_v2.py) (231, 10 cases)
- **Dates:** 2026-02-04 → 2026-02-09 (5 commits; deterministic rewrite 2026-02-08)
- **New since 2026-04-01?** No — but **fully rewritten within the project**, LLM-generated → deterministic. The best "I replaced a bad approach with a good one" story in the repo.
- **Before → after:** V1 gave the LLM up to 50 file summaries inside a 10,000-char prompt budget and asked it to emit nodes and edges, with `graph_min_edges: 15` as an accept threshold and an edge-only regeneration retry when it came back sparse. Slow (180 s timeout), expensive, nondeterministic run-to-run, and it invented dependencies. V2 removes the LLM from structure entirely. Its only surviving job is optional ≤18-word node descriptions, behind `graph_v2_enrich_descriptions`, which **defaults to false**. The dead V1 settings are still in `config.py` — good archaeology for an interviewer.
- **Technique named precisely:**
  1. **Edge extraction** — seven regex import patterns (ES `import ... from`, `require()`, dynamic `import()`, `export * from`, `export {} from`, Python `from X import`, Python `import X`) over file content read from the on-disk clone, with fallback to the `imports` list the Tree-sitter parser captured at index time if the file is gone. Confidence by import kind: relative (`./`) 0.92, scoped (`@`) 0.78, bare 0.72. Repeated imports accumulate `weight = min(5, 1 + count // 2)`.
  2. **Module path resolution** ([learning_service.py:2247-2315](apps/api/src/services/learning_service.py:2247)) — an ordered candidate list: relative resolution via `posixpath.normpath`, `@/` alias → repo root *and* → `src/`, root-relative `/foo`, monorepo best-effort `src/` prefix. Each candidate is tested as a direct path, then with each of 10 known extensions appended, then as `<dir>/index.<ext>`. Escapes above the repo root are rejected. **A miniature module resolver**, and the reason edges actually land.
  3. **Node metrics** — in/out degree, degree, degree centrality (`degree / (N−1)`), and `importance = clamp(1, 10, round(1 + centrality·7 + min(3, log1p(loc)/4)))`. Connectivity dominates; size contributes sub-linearly.
  4. **Edge ranking** — `0.45·normalized_weight + 0.25·confidence + 0.20·normalized_endpoint_degree + 0.10·cross_group_bridge_bonus`. The bridge bonus deliberately promotes edges crossing architectural boundaries, because those are the ones that explain the system.
  5. **Module rollup** — `_module_key_for_path` does monorepo-aware bucketing (`apps/<x>/src/<y>` → 4 segments; `apps|packages/<x>` → 2; `src/<x>` → 2; well-known top-level dirs → 1). Cross-module edges aggregate by `(source, target, relation)` with `weight = clamp(1, 5, round(total/3))`; intra-module edges become `internal_edge_count` and surface as an **internal density** metric `internal / (n·(n−1))` on the node.
  6. **Adaptive entry-view selection** ([learning_service.py:1546-1562](apps/api/src/services/learning_service.py:1546)) — **the cleverest decision in the codebase.** >90 nodes or >240 edges means "dense," so a module overview *would* read better. **But** if the cross-module edge ratio is <8% or there are <18 cross-module edges, the module view collapses into disconnected blobs and is *less* informative than the file view. So density alone doesn't trigger rollup — density **plus** cross-module signal does. The reason is returned to the client as `entry_reason` (`below_dense_threshold` / `low_cross_module_signal` / `dense_with_cross_module_signal` / `user_selected_*`).
  7. **Component-aware pruning** — over the node cap, run BFS `_connected_components`, sort largest-first, **keep whole small components**, and within an oversized component keep top scorers by `2.5·degree + 6.0·centrality + 4.0·(bridges ≥ 2) + min(2, log1p(loc)/5) + 2.0·(entrypoint-named)`. Naive global top-N would silently delete entire subsystems.
  8. **Per-node edge budget** — each node keeps its top-K incident edges by rank (10 file view / 14 module view), union'd across nodes. Bounds hub explosion without globally truncating.
  9. **Total determinism** — every collection sorted by an explicit stable key before return: nodes by ID; edges by `(source, target, relation, label)`; per-node ranking by `(-rank, -weight, -confidence, source, target, relation)`. Proven by `test_build_deterministic_edges_is_stable` and `test_module_graph_aggregation_deterministic`.
  10. **Scoped drill-down and focus subgraphs** — k-hop BFS (k ∈ {1,2}) from a module scope or a single focus node, with boundary neighbors included so context isn't cut at the edge.
  11. **TTL + LRU result cache** — keyed on `(repo_id, granularity, scope, focus_node, hops, repo_version)` where `repo_version` is `updated_at`/`last_indexed_at`, so re-indexing invalidates automatically. 45 s TTL, 64 entries, `RLock`-guarded, **deep-copied on both read and write** so a caller can't mutate the cached Pydantic model.
- **The hardest part: deciding what a graph is allowed to hide.** A real monorepo produces thousands of file-level edges. Render all of them → an unreadable hairball. Render a naive top-N → you delete subsystems without telling anyone, producing a map that lies by omission. The answer is a **five-stage funnel** — view selection → scope/focus filtering → component-aware pruning → per-node edge budget → global edge cap — where **every stage that drops something records that it did.** `truncated`, `raw_stats` (pre-pruning counts), `cross_module_ratio`, `internal_edges_summarized`, and the applied `edge_budget` all ship to the client in `GraphMeta`. The graph never silently lies about its own completeness.

  Second hard part: **the module resolver.** Import specifiers are a mess — `@/components/ui`, `../../lib/utils`, `~/app`, bare names that may or may not be workspace-internal, directory imports that mean `index.ts`. Getting a usable hit rate without a real bundler resolver took the ordered-candidate approach and a lot of testing against real repos.
- **Scale:** `[MEASURED]` File view 160 nodes / 600 edges; module 120/260; scoped 220/420. Auto-rollup at >90 nodes or >240 edges. Cross-module gate ≥8% ratio and ≥18 edges. Per-node budgets 10/14. Cache 45 s × 64 entries. 10 unit tests covering resolution, determinism, pruning, density math, thresholds, aggregation, scoping, budgeting.
  `[EST]` A 1,500-file monorepo yields ~3,000–8,000 raw edges, funnelled to ≤600. Generation for that size — pure deterministic Python — **~200–600 ms cold, <5 ms cached.** `[MEASURED]` **Zero LLM calls on the default path**, so the p99 has no provider dependency at all. That is exactly why the rewrite happened.
- **Proposed lenses:** `systems 5` — graph algorithms (BFS components, degree centrality, multi-stage budgeted pruning), determinism guarantees, TTL/LRU caching with defensive copying. `backend 4`. `ai 2` — notable precisely *because* it took AI out of the critical path; that's a mature judgment call and worth saying. **PROPOSED.**

---

### WS-8: Graph visualization frontend (level-of-detail rendering)

- **What it does and why:** Renders WS-7 and keeps it interactive at scale. A correct graph that stutters at 200 nodes is not a usable feature.
- **Files:** [graph-view.tsx](apps/web/src/components/learning/graph-view.tsx) (908) · [graph-layouts.ts](apps/web/src/components/learning/graph/graph-layouts.ts) (227) · [CustomNode.tsx](apps/web/src/components/learning/graph/CustomNode.tsx) (245) · [CustomEdge.tsx](apps/web/src/components/learning/graph/CustomEdge.tsx) (119) · [NodeDetailPanel.tsx](apps/web/src/components/learning/graph/NodeDetailPanel.tsx) (320) · [GraphToolbar.tsx](apps/web/src/components/learning/graph/GraphToolbar.tsx) · [GraphLegend.tsx](apps/web/src/components/learning/graph/GraphLegend.tsx)
- **Dates:** 2026-02-01 → 2026-02-08 (5 commits)
- **New since 2026-04-01?** No.
- **Technique named precisely:**
  - **Dual layout engine with timeout failover.** Primary is **ELK** (`layered`, `direction: RIGHT`, `crossingMinimization: LAYER_SWEEP`, `nodePlacement: NETWORK_SIMPLEX`, `edgeRouting: ORTHOGONAL`), raced against a **1,500 ms timeout** via `Promise.race`; on timeout or failure it falls back to **dagre** (`rankdir: LR`, `acyclicer: greedy`). ELK minimizes crossings better; dagre is fast and never hangs. Spacing adapts to graph shape: dense file scope (≥120 nodes, <25% modules) → 188 px layer spacing; heavy edge load (edges > 2× nodes) → 158; otherwise 130.
  - **Layout memoization by graph signature.** A canonical string from sorted `id:entity:group` for nodes plus sorted `source->target:relation` for edges, cached in a 48-entry `Map` with FIFO eviction. Toggle a filter and toggle it back — instant, not a re-run of ELK.
  - **ELK is loaded through a runtime-constructed dynamic import** ([graph-layouts.ts:24](apps/web/src/components/learning/graph/graph-layouts.ts:24)) rather than a literal `import()` specifier, deliberately hiding the module path from the Next.js/webpack static analyzer so elkjs stays out of the server bundle. Load failure sets `elkInstance` to `null` — a **tri-state**: `undefined` = untried, `null` = permanently unavailable, object = ready — and dagre takes over. Ugly, load-bearing, and worth explaining; the honest framing is that a bundler-config fix (`serverExternalPackages`) is the cleaner answer today.
  - **Zoom-driven level of detail.** Below 0.7 zoom nodes render `compact`; below 0.55 only the top **60** edges by rank render; below 0.9 only the top **180**; above that, all. Because the backend already ranked every edge, the frontend budget is just a prefix of a sorted list — the two halves of the system were designed together.
  - **Focus mode with k-hop neighborhoods** — client-side BFS over the filtered edge set, plus a rule that selected-node edges are *always* kept regardless of budget, so clicking a node never makes its own connections vanish.
  - **Node visual encoding** — size scales with `importance` (the backend's degree-centrality-derived score), 8 color-coded file types with icons, module nodes get a distinct accent, and degree drives an activity indicator. The graph's visual weight literally encodes centrality.
  - **PNG export** via `html-to-image` `toPng` at `pixelRatio: 2` on the `.react-flow` element.
- **The hardest part: keeping React Flow at 60 fps when the graph is large.** Every derived value sits behind `useMemo` with a precise dependency array — `filteredNodes` → `filteredNodeIds` → `filteredEdges` → `focusNeighborhoodNodeIds` → `selectedNeighborhoodNodeIds` → `selectedNeighborhoodEdgeIds` → `budgetedEdgeIds` → `renderedNodes` → `renderedEdges`: a **nine-stage derivation chain** where one sloppy dependency causes a full re-layout on every mouse move. Nodes and edges are **hidden, not unmounted** (`hidden: true`), so React Flow doesn't tear down and rebuild DOM on every zoom tick. Zoom is debounced *by value*: `setZoomLevel(prev => Math.abs(prev - viewport.zoom) < 0.03 ? prev : viewport.zoom)` — a 3% deadband turning a continuous scroll gesture into a handful of state updates instead of hundreds ([graph-view.tsx:569-571](apps/web/src/components/learning/graph-view.tsx:569)).

  Subtler: an `isFetchingRef` guard plus a `requestRef` holding the *intended* request state, so rapid view switches (module → file → scoped → focus) can't produce out-of-order responses that overwrite newer state with older data.
- **Scale:** `[MEASURED]` Handles the backend caps: 160/220 nodes, 600 edges. LOD budgets 60/180/∞. ELK budget 1,500 ms. Layout cache 48 entries. `[EST]` Smooth to ~200 nodes / ~400 visible edges on a normal laptop; the LOD budgets are what keep the zoomed-out "whole system" view usable, which is precisely the view with the most edges on screen.
- **Proposed lenses:** `frontend 5` — layout engine failover, memoized derivation chains, LOD rendering, gesture debouncing, race-condition guards. The strongest frontend work in the repo. `systems 3`. `swe 4`. **PROPOSED.**

---

### WS-9: Interactive challenge engine

- **What it does and why:** Turns passive lesson reading into active recall. Three challenge types generated from lesson context: **bug hunt** (find the buggy line in a 15–25 line snippet), **code trace** (predict the return value, 4 options), **fill in the blank** (≤3 blanks, multiple choice each).
- **Files:** [challenges.py](apps/api/src/services/challenges.py) (335) · [learning.py:396-514](apps/api/src/api/routes/learning.py:396) · [ChallengeView.tsx](apps/web/src/components/learning/ChallengeView.tsx) (524) · tests: [test_learning_challenges.py](apps/api/tests/integration/test_learning_challenges.py), [ChallengeView.test.tsx](apps/web/src/components/learning/ChallengeView.test.tsx)
- **Dates:** 2026-02-01 → 2026-02-05 (4 commits)
- **New since 2026-04-01?** No.
- **Technique named precisely:** Pydantic-typed schemas (`BugHuntChallenge`, `CodeTraceChallenge`, `FillBlankChallenge`) with per-type prompt builders and per-type **server-side** validators. `validate_bug_hunt` compares the line number, `validate_code_trace` the index, `validate_fill_blank` normalized strings — **the correct answer never reaches the browser before submission.** Three layers of degradation: LLM → outermost-brace JSON extraction → a deterministic **mock challenge bank**, so the feature is never broken, only less novel. Hint usage is tracked and reduces the award (75 with hint, 150 perfect).
- **The hardest part:** Getting a model to produce a *findable but non-trivial* bug and — harder — to report the bug's line number **consistently with the snippet it just emitted**. Models routinely emit 20 lines and claim the bug is on line 34. Mitigations are prompt-level (name the bug classes: off-by-one, missing null check, wrong comparison operator), typed schema, and mock fallback. Honestly the least-hardened AI surface in the project: the line number is *not* re-validated against the snippet's actual line count. Volunteer this in an interview as "the next thing I'd fix, and it's a 10-line fix."
- **Scale:** `[MEASURED]` 3 types, 3 validators, a full mock bank per type, XP 75/150. `[EST]` ~1 LLM call ≈ $0.01, generation 4–10 s.
- **Proposed lenses:** `ai 3`, `backend 3` (server-side answer authority is the right call), `frontend 3`. **PROPOSED.**

---

### WS-10: Gamification — XP, levels, streaks, achievements, activity heatmap

- **What it does and why:** Reading an unfamiliar codebase has no natural feedback loop; you can't tell whether you're making progress. This supplies one.
- **Files:** [gamification.py](apps/api/src/services/gamification.py) (560) · [database.py:269-361](apps/api/src/models/database.py:269) · [learning.py:209-395](apps/api/src/api/routes/learning.py:209) · frontend: [XPBar.tsx](apps/web/src/components/learning/XPBar.tsx), [XPWidget.tsx](apps/web/src/components/learning/XPWidget.tsx), [AchievementsPanel.tsx](apps/web/src/components/learning/AchievementsPanel.tsx) (217), [dashboard-view.tsx](apps/web/src/components/dashboard/dashboard-view.tsx), [activity-heatmap.tsx](apps/web/src/components/dashboard/activity-heatmap.tsx)
- **Dates:** 2026-02-01 → 2026-02-08 (7 commits)
- **New since 2026-04-01?** No.
- **Technique named precisely:** A declarative XP table (8 award reasons) and a 6-tier level ladder (0/200/500/1000/2000/5000 XP → Newcomer, Explorer, Contributor, Architect, Master, Legend). **15 achievement definitions** across 4 categories (learning, streak, explorer, challenge) with idempotent unlock semantics. Streak logic compares `last_activity_date` to today and yesterday: same day → no-op; yesterday → increment; older → reset to 1; `longest_streak` tracked separately. Streak bonus is `min(streak_days × 25, 250)` — capped, so a 30-day streak doesn't award 750 XP per lesson. State is scoped **per repository**, not per user, a deliberate simplification given there is no auth.
- **The hardest part: idempotency across every award path.** Every one of these can be replayed by a double-click, a React strict-mode double-render, or a refresh: lesson complete, quiz submit, challenge complete, graph first view, graph node view. Each needed a distinct dedup key *and* a distinct storage strategy — `LessonProgress` keyed `(repo, lesson_id, persona)`, `GraphNodeInteraction` keyed by node ID with a **unique DB index**, `Achievement` keyed by achievement key with a **unique DB index**, and the graph *first view* flagged separately from node views. The frontend cooperates via a `viewedNodeIdsRef` `Set` so the API isn't even called twice ([graph-view.tsx:457-460](apps/web/src/components/learning/graph-view.tsx:457)), but the **server and ultimately the schema are the authority**. Get this wrong and the XP counter inflates on refresh, which destroys the entire point of the feature.
- **Scale:** `[MEASURED]` 6 levels, 15 achievements, 8 XP reasons, 4 tracked entity tables, 2 unique DB indexes enforcing idempotency, streak bonus capped at 250. The dev DB shows 38 `user_xp` rows, 23 unlocked achievements, 18 graph node interactions, 7 lesson completions from real use.
- **Proposed lenses:** `backend 3` — idempotency and state modeling done properly, enforced at the schema level. `frontend 3` — heatmap, animated XP bar, confetti on unlock. `swe 3`. **PROPOSED.**

---

### WS-11: Provider abstraction layer (LLM + embeddings) with rate-limit survival

- **What it does and why:** Lets the same product run against OpenAI, Anthropic, or a fully local Ollama, and survive provider rate limits during long index runs. **This is what makes "point it at your private repo without shipping your source anywhere" a real claim rather than marketing.**
- **Files:** [core/llm/](apps/api/src/core/llm/) — `base.py` (23), `factory.py` (34), `openai_llm.py` (126), `anthropic_llm.py` (96), `ollama_llm.py` (98) · [core/embeddings/](apps/api/src/core/embeddings/) — `openai_embeddings.py` (207), `ollama_embeddings.py` (155), `factory.py`, `base.py` · [llm_cache.py](apps/api/src/core/cache/llm_cache.py) · [test_openai_embeddings.py](apps/api/tests/unit/test_openai_embeddings.py) (98)
- **Dates:** 2026-01-31 → 2026-02-08 (7 commits on the OpenAI embedder alone)
- **New since 2026-04-01?** No.
- **Technique named precisely:** ABC + factory behind a settings string. The engineering lives in the embedders:
  - **Token-budgeted batching** — `tiktoken` encodes every text; batches close when either a 250,000-token budget or a 128-item count would be exceeded. Per-text truncation at 8,000 tokens (buffered under the 8,192 model limit) by encode → slice → decode, which is *exact* rather than a character-count guess.
  - **Retry-After-aware exponential backoff with jitter** — on `RateLimitError`, parse `retry-after-ms` first, then `retry-after`, and only if neither header exists compute `min(max_backoff, base · 2^attempt + uniform(0, 0.5))`. Honoring the server's own hint beats guessing; jitter prevents synchronized retry storms. Defaults 6 retries / 1 s base / 30 s ceiling.
  - **Cross-thread request pacing** — an optional minimum spacing implemented with a `threading.Lock` and a monotonic `_next_request_time` cursor, so pacing holds even though this singleton is reachable from FastAPI's threadpool. It computes the sleep **inside** the lock and awaits **outside** — the correct pattern; never hold a lock across an await.
  - **Concurrency gated to 1 by default**, with an explicit comment that sequential minimizes provider pressure and memory, and an `asyncio.gather` fast path only when the operator raises `OPENAI_EMBEDDING_REQUEST_CONCURRENCY`.
  - **Ollama embeddings** ([ollama_embeddings.py](apps/api/src/core/embeddings/ollama_embeddings.py)) — `tenacity` retry with `stop_after_attempt(10)` and `wait_exponential(min=2, max=30)` over three httpx exception classes, a 0.2 s inter-request sleep to avoid overwhelming a local model, a per-chunk char cap, a configurable `num_ctx`, a specific 404 branch that tells the user to run `ollama pull <model>`, an empty-text guard returning a zero vector of correct dimensionality, and a **`fail_open`** mode that substitutes a zero vector and continues rather than killing a 3,000-chunk index run over one flaky embedding.
  - **Ollama chat** — streaming retry that only retries **before the first token has been yielded** (`should_retry = attempt < max_retries - 1 and not yielded`, [ollama_llm.py:73](apps/api/src/core/llm/ollama_llm.py:73)), because retrying after partial output would duplicate text in the user's face.
  - **`/health`** checks database, vector store, LLM reachability, **GitHub API rate-limit headroom**, and demo-repo readiness, returning `healthy`/`degraded` with per-check detail.
- **The hardest part: indexing a large repo without getting rate-limited into failure.** A 5,000-file repo produces thousands of chunks; naive concurrent embedding hits HTTP 429 within seconds, and a naive fixed retry re-hits the same limit. The composite fix is four independent knobs (batch token budget, batch item count, request concurrency, inter-request spacing) plus header-aware backoff plus jitter — **all eleven parameters exposed as environment variables** ([config.py:52-58](apps/api/src/config.py:52)) and documented in the README with the explicit note that large repos can trigger 429s and indexing retries automatically. That documentation exists because the failure was hit for real.

  There is also a visible **debugging saga** around Ollama. Untracked local scripts sit in `apps/api/`: `reproduce_ollama.py` → `diagnose_load.py` → `diagnose_content.py` → `diagnose_chunk_size.py` → `diagnose_fix.py` → `verify_ollama_retry.py`. Minimal repro, then isolate load, then isolate content, then isolate chunk size, then verify the fix. Textbook bisect-the-variable debugging, and the artifacts survived. It produced three shipped settings (`ollama_embedding_num_ctx: 2048`, `ollama_embedding_max_chars: 3000`, `ollama_embedding_fail_open: true`) and the retry-only-before-first-token rule. **Tell this story when asked how you debug.**
- **Scale:** `[MEASURED]` 3 LLM providers, 2 embedding providers, 11 tunable embedding parameters, 6 retries (OpenAI) / 10 retries (Ollama), 30 s backoff ceiling, 250k-token / 128-item batches, 8,000-token truncation. Two dedicated unit tests: `test_embed_texts_retries_on_rate_limit`, `test_embed_texts_respects_min_request_spacing`.
  `[DERIVED]` At 250k tokens/request, a 7.5M-token full index is ~30 API calls — well inside any tier's *request* limits. The binding constraint is tokens-per-minute, which is exactly what the spacing knob addresses.
- **Proposed lenses:** `backend 5` — production API-client engineering: header-aware backoff, jitter, cross-thread pacing, token budgeting, graceful degradation, tested. `ai 4`. `systems 3`. **PROPOSED.**

---

### WS-12: Demo mode and public-deployment guardrails

- **What it does and why:** Lets one deployment be exposed to the public internet with the author's own API key attached. Without this, "here's a live demo" means "here's my OpenAI bill."
- **Files:** [demo_mode.py](apps/api/src/core/demo_mode.py) (110, new) · [rate_limit.py](apps/api/src/core/rate_limit.py) (177, new) · [seed_demo.py](apps/api/src/demo/seed_demo.py) (209) · [platform.py](apps/api/src/api/routes/platform.py) · [entrypoint.sh](docker/entrypoint.sh) · [prewarm-demo.mjs](scripts/prewarm-demo.mjs) · [demo-banner.tsx](apps/web/src/components/common/demo-banner.tsx) · [test_demo_mode.py](apps/api/tests/integration/test_demo_mode.py)
- **Dates:** 2026-02-08 (single day)
- **New since 2026-04-01?** No.
- **Technique named precisely:**
  - **Single-repo pinning** — `assert_demo_repo_access(db, repo_id)` at the top of every repo-scoped handler 404s anything that isn't the featured repo, with a typed `DEMO_REPO_ONLY` code and a message pointing at self-hosting. `assert_demo_repo_mutation_allowed` gates import/delete with `DEMO_REPO_MUTATION_DISABLED`.
  - **Five independent sliding-window rate limiters**, per bucket per client IP: chat 18/60 s · curriculum 6/60 s · lesson 8/60 s · graph 5/60 s · challenge 10/60 s. The Redis implementation is a **sorted set per key**: `ZREMRANGEBYSCORE` to evict the window, `ZCARD` to count, `ZADD` with a `{timestamp}-{uuid8}` member to avoid score collisions, `EXPIRE` to self-clean. A *true* sliding window, not a fixed bucket, so it can't be gamed by straddling a boundary. The in-memory fallback is a `deque` per key with identical eviction semantics. Both compute an accurate `retry_after` from the oldest event in the window and return it in **both** the JSON body and the `Retry-After` header.
  - **A kill switch** — `DEMO_BUSY_MODE=true` returns 503 `DEMO_BUSY_MODE` on every gated endpoint. One env var to stop the bleeding when something goes wrong publicly.
  - **Runtime config handoff** — `GET /api/platform/config` returns `demo_mode`, `demo_repo_id`, banner text, and mutation permissions, so the frontend hides destructive actions and shows the banner **from server state**, not a build-time constant. Change the flag, restart the API, and the UI follows without a redeploy.
  - **Background seeding** — `entrypoint.sh` runs `python -m src.demo.seed_demo --check-only` and, if not ready, seeds `--no-wait` in the background so the server binds its port immediately rather than failing a platform health check while indexing.
  - **Prewarming** — `pnpm demo:prewarm` polls until the demo repo is `completed`, then generates a curriculum, generates the graph, and **drains one full chat SSE stream**, so the first real visitor hits warm caches instead of a cold pipeline.
  - Demo pinned to `vercel/nextjs-subscription-payments` — real, recognizable, moderately sized, and familiar enough that a visitor can independently judge whether the answers are correct.
- **The hardest part: making the guardrails invisible when they're off, and legible when they fire.** Every path is a no-op when `DEMO_MODE=false`. Every gate returns a **typed error code with `retry_after_seconds`** rather than a bare 429. `api-client.ts` has a matching `ApiError` carrying `{status, code, retryAfterSeconds}`, and [chat-interface.tsx:108-124](apps/web/src/components/chat/chat-interface.tsx:108) turns a 429 into *"Demo rate limit reached. Retry in ~12s."* and a 503 into the busy message. **The whole path — server error code → HTTP header → typed client error → user-facing copy — was designed as one thing**, and that end-to-end coherence is the mark of someone who has actually operated something publicly.
- **Scale:** `[MEASURED]` 5 buckets, per-IP, true sliding window, Redis + memory backends, 30 s cooldown floor, `X-Forwarded-For`-aware IP extraction (correct behind Render/Vercel proxies).
  `[DERIVED]` Worst-case single-IP spend under the caps: 18 chats + 6 curricula + 8 lessons + 5 graphs + 10 challenges per minute. With the 30-min answer cache and a pinned repo, realistic sustained cost for `[EST]` a few hundred visitors/day is **~$1–5/day**, most of it absorbed by cache hits.
- **Proposed lenses:** `backend 4` — real rate limiting with correct sliding-window semantics and dual backends. `systems 3`. `swe 4`. **PROPOSED.**

---

### WS-13: CLI client and VS Code CodeTour export

- **What it does and why:** Terminal-first access to everything, plus an escape hatch that turns generated lessons into a real IDE artifact rather than a walled-garden feature.
- **Files:** [cli/codebaseqa/cli.py](cli/codebaseqa/cli.py) (345) · [cli/pyproject.toml](cli/pyproject.toml) · [codetour_schemas.py](apps/api/src/models/codetour_schemas.py) · [learning_service.py:2317-2360](apps/api/src/services/learning_service.py:2317)
- **Dates:** 2026-01-31 → 2026-02-10 (4 commits)
- **New since 2026-04-01?** No.
- **Technique named precisely:** A Click-based CLI with 6 commands (`index`, `ask`, `list`, `search`, `lessons`, `export-tour`), `httpx` against the same REST API the web app uses, Rich for terminal rendering, and **live SSE consumption in the terminal** — `index --wait` drives a progress bar off the same `/progress` stream the browser uses, and `ask` streams tokens as they arrive. Editable install via `pip install -e .`, configured with `CODEBASEQA_API_URL`. CodeTour export maps validated `code_references` to `CodeTourStep{file, line, description, title}` and emits Microsoft's `.tour` JSON, synthesizing an "Introduction" step against `README.md` when a lesson has no references.
- **The hardest part:** Not much — worth being honest about that. The design point to defend is the discipline: **the CLI is a pure API consumer with zero backend imports**, which forced the REST surface to be genuinely complete rather than "complete except for the bits the web app does inline." That constraint is why the API was worth documenting in two OpenAPI formats.
- **Scale:** `[MEASURED]` 6 commands, 345 lines, one external contract.
- **Proposed lenses:** `backend 3`, `swe 3`. **PROPOSED.**

---

### WS-14: Testing, CI, and runtime migrations

- **What it does and why:** Keeps 24,400 lines built by one person in 19 days from regressing.
- **Files:** [apps/api/tests/](apps/api/tests/) (16 modules, 2,006 lines) · [chat_quality_cases.json](apps/api/tests/evals/chat_quality_cases.json) · 6 frontend test files (457 lines) · [ci.yml](.github/workflows/ci.yml) · [migrations.py](apps/api/src/models/migrations.py) (116) · [verify-web-css.mjs](scripts/verify-web-css.mjs) · [pyproject.toml](apps/api/pyproject.toml)
- **Dates:** 2026-02-02 → 2026-02-08. Note three consecutive commits on 2026-02-03 titled "Fixing Testes on github actions" (×2) — the works-locally-fails-in-CI arc, preserved in history.
- **New since 2026-04-01?** No.
- **Technique named precisely:** Pytest with `asyncio_mode = "auto"`, coverage enforced via `addopts = "--cov=src --cov-report=term-missing"`, ruff with `select = ["E","F","I","W"]`. Tests split `unit/` (9 modules) and `integration/` (5 modules), with a shared `conftest.py` providing sync `TestClient`, async `AsyncClient`, and per-language sample-code fixtures. The integration chat test monkeypatches the RAG pipeline and asserts the **exact SSE event sequence** `sources → meta → content → done`, parameterized over the debug flag — **the wire protocol itself is under test**, not just the happy path.

  CI runs two independent jobs. Backend: Python 3.11 + pip cache → ruff → pytest with coverage XML → Codecov. Frontend: pnpm 10.28.2 + Node 20 → lint → `tsc --noEmit` → `next build` → **`pnpm web:verify-css`** → vitest. That CSS step is unusual and it exists for a specific reason: Tailwind v4 + Next 16 had a failure mode where the build succeeded but shipped an **unstyled page**. The README documents the `rm -rf apps/web/.next` remedy. So a custom build-artifact assertion was added to catch a class of failure neither the linter, the type checker, nor the tests could see.

  **Runtime migrations** run inside the FastAPI lifespan: additive-only, idempotent, introspection-guarded (`_column_exists` / `_table_exists` via SQLAlchemy `inspect`), covering 3 column additions, 1 table creation, and 5 index creations. Deliberately not Alembic — the stated reason is avoiding an Alembic dependency for small increments, which is right for a single-file SQLite deployment where the user will never run a migration command.
- **The hardest part: testing a system whose core is nondeterministic.** The solution is drawing the boundary carefully. Deterministic components get real assertions — intent scoring, retrieval boost ordering, graph determinism, module path resolution, edge budgeting, density math, embedding retry/backoff with a fake clock. LLM-dependent paths are tested via monkeypatched fakes asserting **shape and protocol** rather than content: did the SSE sequence come out right, did `mode` and `context_files` reach the RAG layer, did the cache serve without touching the LLM, did the fallback fire and record the right reason. The genuinely subjective part lives in the eval fixture as a stated quality contract rather than a green checkmark.

  The most valuable single test is `test_docs_first_profile_boosts_readme_and_penalizes_trivial_exports` — it encodes a real production bug (barrel files beating READMEs) as a permanent guard, using real content from a real repo.
- **Scale:** `[MEASURED]` 22 test modules / 2,463 lines total; ~1:4 test-to-source on the backend. 2 CI jobs, 9 steps. 9 runtime migration operations. Codecov wired. `[EST]` Backend line coverage in the 45–60% band — deterministic core well covered, LLM-orchestration paths much less so.
- **Proposed lenses:** `swe 4` — unit/integration split, protocol-level testing, regression-test-from-a-real-bug habit. `backend 3`. **PROPOSED.**

---

### WS-15: Product surface, documentation, and launch packaging

- **What it does and why:** Turning working code into something a stranger will actually try. **Eleven of 34 commits — nearly a third of the project's history — are this**, which is itself the signal.
- **Files:** [README.md](README.md) (458) · [docs/CODEBASE_DEEP_DIVE.md](docs/CODEBASE_DEEP_DIVE.md) (981) · [docs/architecture.md](docs/architecture.md) · [docs/releases/v1.0.0.md](docs/releases/v1.0.0.md) · `docs/media/` (10 numbered PNG screenshots + 6 hand-authored SVG diagrams) · `docs/arch_final.png` · CONTRIBUTING / CODE_OF_CONDUCT / SECURITY / SUPPORT · `.github/ISSUE_TEMPLATE/` · [hero-section.tsx](apps/web/src/components/home/hero-section.tsx) · [bento-grid.tsx](apps/web/src/components/home/bento-grid.tsx) (401)
- **Dates:** 2026-02-07 → 2026-02-19 (11 commits)
- **New since 2026-04-01?** No.
- **What's in it:** A README with a full env-var reference (60+ documented variables across core/LLM/embedding/demo/graph/chat groups), a complete endpoint table, CLI docs, a **"Current Limitations" section naming three real weaknesses**, a 90-second demo video, a 10-screenshot gallery walking the whole product flow, and an architecture diagram. Plus `/openapi.json` **and** `/openapi.yaml` served from the API, and a 981-line generated deep-dive with a file-by-file appendix.
- **The hardest part:** Restraint. The "Current Limitations" section is the tell — it states that large repos are slow and expensive, that lesson/graph quality depends on model capability and retrieved context, and that the Docker setup is OpenAI-optimized unless more vars are wired. Writing that down while trying to attract stars is the harder choice and the right one.
- **Scale:** `[MEASURED]` 458-line README, 981-line deep dive, 8,241 lines of docs/research, 16 media assets, 37 endpoints, 60+ documented env vars (112 exist in code), 5 governance files, 3 templates.
- **Proposed lenses:** `swe 4` — API documentation in two formats, honest limitations, OSS governance scaffolding. `frontend 3`. **PROPOSED.**

---

### WS-16: Security and correctness audit of a six-month-old codebase

- **What it does and why:** A systematic audit of the author's own code after a six-month gap, producing 13 ranked findings, each reproduced before the fix and re-verified after. Exists because the project was about to be deployed to a public host with real credentials attached, and Phase 1 had never been reviewed by anyone.
- **Files:** [config.py](apps/api/src/config.py) · [repo_manager.py](apps/api/src/core/github/repo_manager.py) · [.dockerignore](.dockerignore) · [docker-compose.yml](docker/docker-compose.yml) · [ci.yml](.github/workflows/ci.yml) · [turbo.json](turbo.json) · [package.json](apps/web/package.json) · [pipeline.py](apps/api/src/core/rag/pipeline.py) · [api-client.ts](apps/web/src/lib/api-client.ts)
- **Dates:** 2026-08-08 (`2e53de0`, `320fc56`)
- **New since 2026-04-01?** **Yes — entirely.**
- **Technique named precisely:** Threat-modeling the credential paths (where does a secret enter, where can it exit), plus differential verification of the CI pipeline — comparing what CI *actually executed* against what the local `pyproject.toml` `testpaths` executed, on the same commit. The three security findings are textbook classes: **substring hostname matching** (`"github.com" in url` matching `github.com.attacker.tld`) fixed by parsing and comparing the hostname exactly; **secret leakage through an error channel** (token in git stderr → persisted to `indexing_error` → streamed by a public SSE endpoint) fixed by redaction before the raise; and **build-context over-inclusion** (`COPY apps/api .` with no `.dockerignore` rule for `.env`) baking a live key into an image.
- **The hardest part: finding bugs whose symptom is that everything looks fine.** None of the 13 findings produced a failing test or an error message. The CI one is the sharpest — `pytest tests/unit tests/integration` skipped `tests/test_parser.py` because that file sits at the `tests/` root, so **CI never once constructed a Tree-sitter parser** while showing green, and the local suite covered *more* than CI did on the same commit. That's a class of bug you can only find by asking "what is this check actually proving?" rather than "is it passing?" Same shape as the `turbo.json` finding, where `globalDependencies` named a root `.env.local` that does not exist, so a cached web build could ship a stale inlined `NEXT_PUBLIC_*` value into production.

  The `CORS_ORIGINS` finding is the best interview anecdote: typed as `List[str]`, pydantic-settings JSON-decodes it inside `EnvSettingsSource` **before** field validators run, so the comma-separated default in docker-compose raised `SettingsError` at import time and `docker compose up` **could never start the API at all** — a documented deployment path that had never worked. Fixed by reading it as a raw `str` and parsing in a property.
- **Scale:** `[MEASURED]` 13 findings across 20 files, +445/−84, plus 8 tooling fixes in `320fc56`. Verified green: ruff, 89 pytest cases, 12 vitest, tsc.
- **Proposed lenses:** `swe 5` — self-auditing, reproduce-then-fix-then-verify discipline, and finding three genuine credential-exposure paths in your own code. `backend 4`. `systems 3`. **PROPOSED.**

---

### WS-17: Azure OpenAI provider integration

- **What it does and why:** Makes the multi-provider abstraction true rather than aspirational. Both factories advertised provider choice behind real ABCs but only ever constructed public-OpenAI clients. Azure is the provider enterprises actually have.
- **Files:** [config.py](apps/api/src/config.py) · [llm/factory.py](apps/api/src/core/llm/factory.py) · [embeddings/factory.py](apps/api/src/core/embeddings/factory.py) · [openai_llm.py](apps/api/src/core/llm/openai_llm.py) · [openai_embeddings.py](apps/api/src/core/embeddings/openai_embeddings.py) · [test_azure_openai_provider.py](apps/api/tests/unit/test_azure_openai_provider.py) (231)
- **Dates:** 2026-08-09 (`c0e68aa`, +459/−24)
- **New since 2026-04-01?** **Yes — entirely.**
- **Technique named precisely:** Target Azure's **v1 OpenAI-compatible surface** (`<endpoint>/openai/v1`) and reuse the standard `AsyncOpenAI` client instead of `AsyncAzureOpenAI` — **so the Azure branch is a different base URL and a deployment name, not a second client implementation.** The justification is documented: the OpenAI SDK's own README warns `AsyncAzureOpenAI`'s static types "can be incorrect." `azure_openai_base_url()` normalizes the endpoint to `/openai/v1` **idempotently**, accepting a bare host, a trailing slash, or an already-complete URL. `api_key` widened to `str | Callable[[], str]` so an Entra token provider can be supplied later without either class knowing how the credential is obtained — the extension point exists, nothing supplies one yet, and the commit says so.
- **The hardest part: the two silent divergences between Azure and public OpenAI.** Both would have produced confusing wrong behavior rather than errors. `health_check` treated a missing `/models` route as unhealthy, but **on Azure that route enumerates *deployments* and some configurations omit it entirely** — a 404 means the endpoint answered, so credentials and networking are fine. Without the fix, `/api/health` would report a perfectly working Azure deployment as degraded. Separately, `tiktoken` resolves an encoding from a *model* name, and Azure gives you a *deployment* name — so `tokenizer_model` is threaded through separately rather than assuming they're the same string. Also bumped `openai>=1.106.0`, the floor Microsoft documents for the v1 surface and the first version exporting the error classes the health check discriminates on.
- **Scale:** `[MEASURED]` 5 new settings, 2 factory branches with fail-fast named-variable errors, 231 lines of tests. Provider count 3 → 4 for chat, 2 → 3 for embeddings.
- **Proposed lenses:** `backend 4` — reading vendor documentation carefully enough to find the divergences that fail silently. `systems 3`. **PROPOSED.**

---

### WS-18: Terraform infrastructure — deployed backend and cross-provider wiring

- **What it does and why:** Closes a gap that made the deployed product non-functional: `apps/web` was live on Vercel, `api-client.ts` reads `NEXT_PUBLIC_API_URL` with a `localhost:8000` fallback, and **nothing ever set that variable** — so the deployed frontend could not reach an API. The only prior deployment artifact was a local-development compose file.
- **Files:** [infra/terraform/](infra/terraform/) — `main.tf` (125), `variables.tf` (144), `README.md` (96), `cloud-init.yaml.tftpl` (80), `outputs.tf` (47), `versions.tf` (35), `example.tfvars` (32), `vercel.tf` (24), `.terraform.lock.hcl` (48), `.gitignore` (22)
- **Dates:** 2026-08-09 (`b07a400`, +653)
- **New since 2026-04-01?** **Yes — entirely. First infrastructure-as-code in the project.**
- **Technique named precisely:** Two providers in one stack with **an output feeding an input** — a DigitalOcean droplet running the compose file via cloud-init, a block volume, volume attachment, firewall, project grouping, and a `vercel_project_environment_variable` set from the droplet's address. 21 variables, 6 outputs, ~$7/month at defaults.
- **The hardest part: picking a host by disqualification, and writing down why.** The reasoning is the artifact:
  - **Fly.io was the plan and got rejected** — its Terraform provider is abandoned (`fly-apps/fly` still 0.0.23 from 2023-06-22; community fork last shipped 2024-10-28). Managing Fly through that defeats the purpose of using Terraform at all.
  - **Azure Container Apps rejected** for the opposite reason — no block-device volume type, only Azure Files over SMB/NFS, which is **the exact configuration `sqlite.org/howtocorrupt.html` §2.1 warns against.** Choosing a host on the basis of your database's documented corruption modes is the kind of reasoning that reads as senior.
  - **DigitalOcean chosen** — partner provider, 13.3M downloads, updated within the week, and a droplet gives a real block device, which SQLite and Chroma require.
- **The security posture, all deliberate and all stated in the commit:** `.gitignore` covering `*.tfstate` / `*.tfvars` / `*.tfplan` committed **in the same change** so it cannot be forgotten before a first apply — because state holds every resolved secret in plaintext and `sensitive = true` only redacts CLI output. `.terraform.lock.hcl` **is** committed, pinning provider checksums. Both providers version-pinned (`~> 2.99`, `~> 5.10`) because both ship several releases a month. And **no inbound rule for port 6379** — compose publishes Redis for local dev, which on a public droplet is an unauthenticated Redis facing the internet; the DO firewall omits it *and* host ufw allows only 22 and 8000, so **the exposure does not rest on a single control.**
- **Scale:** `[MEASURED]` 455 lines of HCL + cloud-init, 6 resources, 21 variables, 2 pinned providers, ~$7/month.
- **Proposed lenses:** `systems 4` — IaC, cross-provider dependency wiring, defense-in-depth firewalling, state-secret handling. `backend 3`. `swe 4` — the rejected-alternatives documentation is the strongest part. **PROPOSED.**

---

### WS-19: Dependency edges persisted at index time

- **What it does and why:** Moves graph derivation off the read path. `generate_graph` re-derived the entire edge set on every cache miss by reading every source file off disk **inside the request**.
- **Files:** [database.py](apps/api/src/models/database.py) (`CodeDependency`) · [indexing_service.py](apps/api/src/services/indexing_service.py) (`_persist_dependency_graph`) · [migrations.py](apps/api/src/models/migrations.py) · [learning_service.py](apps/api/src/services/learning_service.py) · [test_dependency_persistence.py](apps/api/tests/unit/test_dependency_persistence.py) (181)
- **Dates:** 2026-08-09 (`0cf2937`, +390/−4)
- **New since 2026-04-01?** **Yes** — and it **partially reworks WS-7**, whose read path this replaces.
- **Before → after:** Before, three consequences of deriving in-request: graph latency proportional to repository size with **blocking file I/O on the event loop**; the 45-second in-process TTL cache existed purely to hide this and, being per-process, bought nothing across workers; and the graph was **coupled to the clone still being present** — after a redeploy, container restart, or volume reset, derivation silently fell back to the unresolved import strings on `CodeFile.imports` and produced a *worse graph for the same repository, with nothing indicating it had happened.* After: derivation runs once at the end of indexing, while the clone is guaranteed to exist, into a `code_dependencies` table; the read path is a single indexed query.
- **Technique named precisely:** New table with `(source_path, target_path, relation, weight, confidence)`, indexed on `repository_id` and on each endpoint, **unique on `(repo, source, target, relation)`**, wired into `Repository.dependencies` with delete-orphan cascade — *without which* `DELETE /api/repos/{id}` would leave orphaned edges that union into a later re-import of the same repository. `_persist_dependency_graph` runs after embedding, wrapped so a derivation failure cannot fail an otherwise good index, and offloads the blocking file reads with `asyncio.to_thread`. `_reset_repository_index_data` clears edges too.
- **The hardest part: not forking the definition of an edge.** The obvious implementation reimplements resolution in the indexer, and then two subtly different resolvers drift apart. Instead it **reuses `LearningService`'s existing resolution helpers, so there is still exactly one definition of what an edge is** — the same instinct as the duplicated trivial-chunk predicate in WS-3, applied in the opposite direction.
- **Scale:** `[MEASURED]` 1 new table, 3 new indexes, 1 new migration, 181 lines of tests. `[EST]` Removes O(repo size) blocking file I/O from every graph cache miss.
- **Proposed lenses:** `backend 4` — moving work from read path to write path, cascade correctness, single-definition discipline. `systems 3`. **PROPOSED.**

---

### WS-20: Neo4j graph read model (optional, default-off)

- **What it does and why:** Adds transitive graph traversals the SQL/Python path structurally cannot perform — *what breaks if I change this file*, *how does auth reach the database*, *are there import cycles*.
- **Files:** [neo4j_store.py](apps/api/src/core/graph/neo4j_store.py) (224) · [dependencies.py](apps/api/src/dependencies.py) · [main.py](apps/api/src/main.py) · [indexing_service.py](apps/api/src/services/indexing_service.py) · [repos.py](apps/api/src/api/routes/repos.py) · [test_neo4j_graph_store.py](apps/api/tests/unit/test_neo4j_graph_store.py) (245)
- **Dates:** 2026-08-09 (`2a15ec6`, +682/−3)
- **New since 2026-04-01?** **Yes — entirely.**
- **Technique named precisely:** A **projection, not a source of truth.** `code_dependencies` (SQL) stays authoritative; Neo4j is projected from it at index time and rebuildable by re-indexing. Schema is four statements — uniqueness constraints on `(repo_id, path)` and `(repo_id, key)` that **double as the indexes keeping `MERGE` off a label scan** — plus two secondary indexes. Ingest is batched `UNWIND` + `MERGE` at 500 rows so a large repo doesn't build one enormous transaction. Four traversals: `reachable_from` (variable-length `[:IMPORTS*1..n]` forward), `blast_radius` (the same pattern reversed), `shortest_path`, and `import_cycles` (`(f)-[:IMPORTS*2..n]->(f)`, a code-health signal the SQL path cannot express at all).
- **The capability argument, which is the point:** `hops` is hard-capped at 2 in the REST API because each hop rescans the entire edge list — **depth is quadratic in Python and a single variable-length pattern in Cypher.** This isn't "Neo4j is faster," it's "Neo4j can express a query shape the other path cannot."
- **The hardest part: adding a datastore without making it load-bearing.** Every decision is aimed at that. `neo4j_enabled` **defaults to False**. `get_graph_store()` returns `None` when disabled *or misconfigured* rather than raising, so every caller treats "no graph store" as an ordinary path rather than an error path. Startup verifies connectivity and applies schema, but **a failure only logs — an unreachable graph database must not stop the API booting.** A sync failure during indexing is caught and logged; SQL edges are unaffected. Repo deletion removes the subgraph **before** the SQL rows, so a failure leaves the authoritative data intact and retryable rather than orphaning a subgraph.

  Two subtleties worth quoting. `sync_repository` **deletes the subgraph first rather than merging**, because a MERGE-only sync leaves edges for files that no longer exist and **silently accumulates a graph that no commit ever had.** And depth is clamped (1–10, 2–10 for cycles) because an unbounded variable-length pattern is a trivial way to hang the database — `$hops` is string-interpolated rather than parameterized *because Cypher does not allow a parameter inside a variable-length bound*, so it's coerced to a bounded int by the caller first. That's the right way to handle a case where parameterization isn't available.

  Also a deliberate non-use of the obvious tool: degree and centrality come from `COUNT {}` subqueries rather than Graph Data Science, because **in-database GDS is AuraDB Professional and above, and Aura Graph Analytics sessions are an offline batch shape (2 GB, one concurrent session, 30-minute TTL) that does not fit a synchronous request.**
- **Scale:** `[MEASURED]` 4 schema statements, 500-row ingest batches, 4 traversals, depth clamped 1–10, 245 lines of tests. `[EST]` Transitive queries that are quadratic in Python become a single indexed Cypher pattern.
- **Proposed lenses:** `systems 5` — graph database modeling, Cypher, projection-vs-source-of-truth, optional-dependency discipline, and rejecting GDS for a stated licensing/shape reason. `backend 4`. **PROPOSED.**

---

### WS-21: GraphQL surface for the learner read path

- **What it does and why:** Collapses a measured five-round-trip waterfall on lesson completion into one request. Mounted at `/graphql`, **additive, not a migration** — every REST route still works, with tests asserting it.
- **Files:** [graphql/schema.py](apps/api/src/api/graphql/schema.py) (292) · [main.py](apps/api/src/main.py) · [test_graphql.py](apps/api/tests/integration/test_graphql.py) (275)
- **Dates:** 2026-08-11 (`98e5c76` + `79dafb0`, `909e7a7`, `add5575`)
- **New since 2026-04-01?** **Yes — entirely.**
- **Technique named precisely:** Strawberry GraphQL with 9 types. `learnerDashboard` merges four REST GETs (stats, achievements, activity, completed lessons); `completeLesson` returns the post-mutation dashboard **inline**, which is what removes the fifth round trip. Keeping the dashboard as one type rather than four top-level fields is what makes the inline return possible. The mutation reads the dashboard back **in the same session, after the write, so the client cannot observe a state that predates its own mutation.** Resolvers reuse `GamificationService` directly so GraphQL and REST cannot diverge in behavior. `ActivityDay` is a list rather than a map with a comment explaining why — GraphQL has no arbitrary-key type.
- **The hardest part, part one: being precise about a benefit that turned out to be the opposite of the intuition.** Measuring it **disproved the obvious claim**: the combined resolver issues **more** SQL statements than the four REST handlers — 6 vs 4 on an empty repo — because it performs the same four reads plus session overhead. What it actually removes is four HTTP round trips, four dependency-injection cycles, and four session open/close pairs. The tests and docstrings state that rather than claiming a query-count win that does not exist.
- **The hardest part, part two: the Strawberry threading landmine.** Strawberry "processes sync and async fields using the event loop, which means that using a sync def will block the entire worker" — unlike FastAPI, **there is no automatic threadpool for sync resolvers.** `get_db` hands out a synchronous SQLAlchemy `Session`, so one sync resolver would serialize blocking SQLite calls on the loop and **stall in-flight chat SSE streams** — a cross-subsystem failure that would be near-impossible to diagnose from the symptom. Every resolver is therefore `async` and offloads via `run_in_threadpool`, each opening **a fresh session, not a request-scoped one, because `Session` is not thread-safe and this runs on a threadpool worker.** Two tests enforce the rule structurally: one reflects over `Query`/`Mutation` asserting no resolver is a `sync def`, the other asserts each blocking helper is only reached through `run_in_threadpool`. `AsyncSession` was considered and rejected — a single `AsyncSession` is documented as unsafe across concurrent tasks, which is exactly how a DataLoader batches, and greenlet isn't installed.
- **Scope discipline:** chat stays on REST, with the reasoning recorded — GraphQL incremental delivery (`@defer`/`@stream`) is **not ratified**, absent from the September 2025 spec edition, RFC open since 2024-09-18, and Strawberry's support is experimental requiring `graphql-core>=3.3.0a9` against an installed stable of 3.2.11. "Streaming tokens over GraphQL here would mean betting on an unratified extension for no gain."
- **The three CI-failure follow-ups are the best debugging story in the repo.** See the "What is new" section for the full account: a local green that was **an artifact of the developer's `.env`**, then two rounds of a test asserting against `app.routes` — the framework's route table — instead of the application's behavior, with `GraphQLRouter` registering a different path across Strawberry versions. The third failure was the signal the approach itself was wrong. Bonus detail: **pytest truncates long set reprs with `...`, so the failure output was actively misleading about what the set contained.** Final verification was done properly — `.env` moved aside, all three provider keys unset, 142 passed, ruff clean.
- **Scale:** `[MEASURED]` 292 lines of schema, 9 types, 2 queries, 1 mutation, 275 lines of tests including 2 structural threading-rule tests. 5 round trips → 1.
- **Proposed lenses:** `backend 5` — GraphQL schema design, async/threadpool correctness under a documented framework hazard, structural tests enforcing an invariant, and honest performance accounting. `swe 5` — the "measuring it disproved the intuitive claim" note and the route-table debugging arc. `frontend 2`. **PROPOSED.**

---

### WS-22: Durable indexing progress and stuck-index recovery

- **What it does and why:** Two bugs "whose failure mode was silence" — a progress bar that could only ever show 0% or 100%, and an index that could get permanently wedged with no retry path.
- **Files:** [core/progress.py](apps/api/src/core/progress.py) (159, new) · [database.py](apps/api/src/models/database.py) (`reap_stuck_indexing`) · [indexing_service.py](apps/api/src/services/indexing_service.py) · [repos.py](apps/api/src/api/routes/repos.py) · [main.py](apps/api/src/main.py) · [test_progress_store.py](apps/api/tests/unit/test_progress_store.py) (233)
- **Dates:** 2026-08-11 (`34c7490`, +527/−12) — **on `feat/durable-indexing-progress`, not yet merged to `main`**
- **New since 2026-04-01?** **Yes — entirely.**
- **Technique named precisely:** A **capped Redis stream per repository** (`progress:{repo_id}`, `MAXLEN 500`, approximate) with a **process-wide** in-memory `deque` fallback. A *stream* rather than a plain key specifically because the SSE endpoint wants history — a client that connects late replays what it missed via `XRANGE` instead of only seeing the current value. `get_progress` now reads the shared store first, then the instance dict, then the database. Publishing **never raises**: progress is telemetry, and a Redis blip must not fail an otherwise healthy index, so a publish failure degrades to memory and the caller sees nothing — with a test using a Redis double that raises on **every** call. Logged at `debug` rather than `warning` because a flapping Redis would otherwise emit one warning per parsed file.
- **The hardest part: a bug where the fix has to cross a process boundary.** `IndexingService` wrote progress into a **per-instance dict**, and the SSE endpoint constructs a fresh `IndexingService` per request — so it never saw those writes and always fell through to the database branch, which hardcodes `current_step="Unknown"` and a percentage of 0 or 100. **The per-file progress the indexer computed was unreachable by any client.** The non-obvious part is that the intuitive fix doesn't work either: a per-*process* dict still fails, because indexing runs in a background task and, under more than one worker, in a different process from the request that wants to read it. That forces an external store, which forces the optional-Redis question, which forces the fallback design. `ProgressStore` stores its fallback at class level explicitly because *"a per-instance dict is the bug this replaces."*
- **Second bug: a state machine with an unreachable exit.** Only FAILED and COMPLETED are terminal, and every self-healing path (`repos.py`, `seed_demo.py`) keys on FAILED — so a container killed during CLONING, PARSING, or EMBEDDING left the row in that state **forever**, with no way to retry through the API. **In demo mode that bricked the deployment.** `reap_stuck_indexing` runs at startup, which is the one moment where anything still in a transient state provably has no live indexer, because the process that owned it is gone. **PENDING is deliberately left alone** — a repository queued but not yet started is not stuck, and failing it would break the normal import path. That distinction is the whole correctness argument.
- **Scale:** `[MEASURED]` 500-entry capped stream, 500-entry memory deque, 2 backends, 4 store operations, 233 lines of tests including a raise-on-every-call Redis double.
- **Proposed lenses:** `systems 4` — cross-process state, Redis streams, degradation that cannot fail the caller, and a state-machine liveness fix. `backend 4`. **PROPOSED.**

---

## Genuinely hard

Eight things a competent engineer would not find trivial. The first six are Phase 1; the last two are Phase 2.

**1. Nine Tree-sitter grammars that agree on nothing, unified without a nine-way branch.**
Each language names its AST nodes differently — the identifier for "name of this class" is `identifier`, `type_identifier`, or `constant` depending on grammar; "body of this class" is `block`, `class_body`, `declaration_list`, `field_declaration_list`, or `body_statement`. The naive implementation is a per-language `if` ladder nobody can extend. The implementation here is a declarative config table plus a **two-stage name resolver that tries direct children before descendants** ([tree_sitter_parser.py:323-332](apps/api/src/core/parser/tree_sitter_parser.py:323)). The ordering is load-bearing and non-obvious: in `class Foo extends Bar`, a plain descendant search returns `Bar`. Adding a tenth language is now a six-line config entry, and the recursive traversal requires a `(start_line, end_line, type, name)` dedup set because legitimate paths reach the same node twice.

**2. Cache invalidation solved by making the key content-addressed.**
Caching an LLM answer on `(repo, question)` is a correctness bug in waiting — re-index the repo and every cached answer keeps citing line numbers that no longer exist. Explicit invalidation means tracking every dependency edge between an index build and every derived artifact. The key used instead is `(repo_id, question, intent, top-12 retrieved chunk IDs, model)` ([chat_cache.py:97-115](apps/api/src/core/cache/chat_cache.py:97)). Chunk IDs regenerate on every index, so re-indexing invalidates the entire answer cache automatically, with **zero invalidation code**. The key *is* the dependency set — the same idea as content-addressed build systems, applied somewhere people usually don't. The graph cache does the same thing with the repo's `updated_at`.

**3. Deciding what a graph is allowed to hide — and admitting it.**
A real monorepo has thousands of import edges. Show all → unreadable hairball. Show a naive global top-N → you silently delete entire subsystems and produce a map that lies by omission. The engine implements a five-stage funnel where the pruning stage runs **BFS connected components first and preserves whole small components** before ranking within oversized ones ([learning_service.py:2006-2041](apps/api/src/services/learning_service.py:2006)). Every stage that drops something reports it: `truncated`, `raw_stats`, `cross_module_ratio`, `internal_edges_summarized`, and the applied `edge_budget` all ship to the client.

The adaptive view selection is the sharpest single decision in the codebase. Density alone does **not** trigger a module rollup — the rollup fires only when the graph is dense *and* the cross-module edge ratio is ≥8% with ≥18 cross-module edges ([learning_service.py:1546-1562](apps/api/src/services/learning_service.py:1546)). The reasoning: a big graph with almost no cross-module edges rolls up into disconnected blobs that are *less* informative than the file view. Most implementations check node count and stop. And the whole thing is deterministic — every collection sorted by an explicit stable key, with two named tests proving it.

**4. Grading LLM output without a human, and degrading honestly when it fails.**
"Is this generated lesson good?" has no ground truth and no cheap oracle. The approach decomposes it into objective proxies, each targeting a specific observed failure mode: section-heading completeness ≥0.66, persona relevance density ≥0.2, ≥1 surviving validated code reference, and an eight-condition Mermaid specificity filter. Each has a threshold, a deterministic fallback, and a recorded `fallback_reason` persisted in `quality_meta`.

The citation validator is the strongest piece: the model gets an explicit allowlist of indexed paths, and its output is then re-validated against that allowlist **and** clamped against a real `{path: line_count}` map from the database, deduped by `file:start:end`, capped at 8. That is why the citations resolve. Combined with the chat pipeline's `grounding` self-assessment — which downgrades an overview answer to `medium` when it retrieved no docs — **the system is built to tell you when it's guessing.**

**5. Keeping an LLM-in-the-loop retrieval path observable, bounded, and fast.**
One chat request touches an intent classifier, an optional tiebreak call, six embedding calls, six vector searches, a rescoring pass over hundreds of candidates, a listwise rerank call, and a streaming completion — any of which can be slow, flaky, or return malformed JSON. Production shape required several mechanisms working together: a `RetrievalDiagnostics` record streamed as a `meta` event *and* persisted onto the message row; a per-repo semaphore with a 2 s acquire timeout returning typed backpressure instead of hanging; a 90 s `asyncio.timeout` around the whole generator; four-layer JSON recovery on the reranker; and a cached answer that still **streams in 320-char slices** so the UI can't tell cached from live.

Plus the two silent-corruption bugs that shaped the foundation: the background task needing its own event loop *and* its own DB session ([repos.py:29-49](apps/api/src/api/routes/repos.py:29)), and the closure-in-loop bug where thread-pool lambdas all captured the final batch and wrote the same data N times ([chroma_store.py:96-106](apps/api/src/core/vectorstore/chroma_store.py:96)). Both produce **wrong data rather than an exception**, which is the hardest class of bug to find.

**6. Making a system safe to point at the public internet with your own API key attached.**
Most side projects skip this and just don't ship a demo. Doing it properly required a *true* sliding-window rate limiter (Redis sorted sets with `ZREMRANGEBYSCORE`/`ZCARD`/`ZADD`, uuid-suffixed members to prevent score collisions) with a behaviorally-identical in-memory fallback; per-bucket budgets tuned to the actual cost of each operation (graph is cheapest to compute but heaviest to render, so it gets 5/min; chat gets 18); accurate `retry_after` derived from the oldest event in the window, returned in both body and header; single-repo pinning enforced at the top of *every* repo-scoped handler; a one-variable kill switch; server-driven frontend config so flags don't need a redeploy; background seeding so the container passes its health check while still indexing; and a prewarm script that drains a full SSE stream to warm the answer cache before the first visitor. **Every one of those is a lesson someone usually learns from an incident.**

**7. Finding bugs in your own six-month-old code whose only symptom is that everything looks fine.** `[Phase 2]`
None of the 13 audit findings produced a failing test, an error, or a user complaint. Three were credential-exposure paths: a **substring hostname check** (`"github.com" in url`) that also matched `github.com.attacker.tld`, turning an unauthenticated public endpoint into a token-exfiltration primitive; a **secret leaking through an error channel**, where git stderr containing the token was persisted to `Repository.indexing_error` and then *streamed by a public SSE endpoint*; and a **live `OPENAI_API_KEY` baked into the Docker image** because `COPY apps/api .` had no `.dockerignore` rule for `.env`.

The CI finding is the sharpest: `pytest tests/unit tests/integration` skipped `tests/test_parser.py` because that file sits at the `tests/` root, so **CI never once constructed a Tree-sitter parser** — while showing green, and while the *local* suite covered more than CI did on the same commit. Finding that requires asking "what is this check actually proving?" rather than "is it passing?" The same question found a `turbo.json` `globalDependencies` pointing at a root `.env.local` that does not exist, meaning a cached web build could ship a stale inlined `NEXT_PUBLIC_*` value to production, and a `CORS_ORIGINS` type annotation that made `docker compose up` **structurally incapable of starting the API** — a documented deployment path that had never once worked, because pydantic-settings JSON-decodes `List[str]` before field validators run.

**8. Adding two datastores and a second API protocol without making any of them load-bearing.** `[Phase 2]`
Neo4j and GraphQL both landed as strictly additive surfaces, and the discipline is uniform: `neo4j_enabled` defaults to **False**; `get_graph_store()` returns `None` when disabled *or misconfigured* rather than raising, so every caller treats absence as an ordinary path; startup verifies connectivity but **a failure only logs, because an unreachable graph database must not stop the API booting**; a sync failure during indexing cannot affect the authoritative SQL edges; and repo deletion removes the Neo4j subgraph *before* the SQL rows so a failure leaves the authoritative data intact and retryable. `sync_repository` deletes-then-inserts rather than merging, because **a MERGE-only sync silently accumulates a graph that no commit ever had.**

The GraphQL side has a genuinely nasty hazard: Strawberry processes sync and async fields on the event loop with **no automatic threadpool**, unlike FastAPI. Since `get_db` yields a synchronous SQLAlchemy `Session`, a single sync resolver would serialize blocking SQLite calls on the loop and **stall in-flight chat SSE streams** — a cross-subsystem failure nearly impossible to diagnose from the symptom. The fix is every resolver `async` + `run_in_threadpool` + a fresh session per call (because `Session` isn't thread-safe on a worker thread), enforced by **two structural tests** that reflect over the schema asserting no resolver is a `sync def` and that each blocking helper is only reached through the threadpool. And `AsyncSession` was considered and rejected for a stated reason: a single `AsyncSession` is documented unsafe across concurrent tasks, which is exactly how a DataLoader batches.

Underneath both is WS-19, which is the least flashy and arguably the most important: graph derivation moved from the read path to index time, eliminating **blocking file I/O on the event loop** and a silent correctness bug where a missing clone made the graph quietly degrade to unresolved import strings and produce *a worse graph for the same repository, with nothing indicating it had happened.*

---

## Anything important or interesting

*Everything below is context for future you — for a manager, a recruiter, or an interviewer who asks "tell me about this project."*

### The one-paragraph story to tell

> "I spotted a gap in the codebase-understanding market — Greptile is cloud-only at $30/seat, Sourcegraph killed its individual tiers, DeepWiki is public-repos-only, and none of them treat *learning* as a first-class surface. So I built the self-hostable, BYOK, learning-first version: paste a GitHub URL, get chat with real citations, a persona-adaptive curriculum, a deterministic dependency graph, and a quiz/challenge layer. Solo, ~24,000 lines, 19 days, public v1.0.0. I used AI hard — deep research before writing a line, an AI-generated implementation plan, AI pair-programming through the build — and the interesting part is where I *overrode* it. The dependency graph originally asked an LLM to generate the graph structure; I ripped that out and replaced it with a deterministic import resolver, because a map that changes between runs and invents edges is worse than no map. Same instinct everywhere: the intent classifier is deterministic with an LLM only breaking ties, every generated lesson passes four quality gates with deterministic fallbacks, and every citation the model produces gets re-validated against the actual database before a user sees it. Use AI aggressively, trust it nowhere.
>
> Then six months later I came back and audited my own code. That pass found three credential-exposure paths — including a substring hostname check that would send my GitHub token to `github.com.attacker.tld` — and a CI pipeline that had been green while silently skipping twenty test cases and never once constructing a parser. I fixed those, then gave the project the things it needed to actually run rather than demo: Terraform for a real deployed backend, Azure OpenAI so the multi-provider abstraction was true instead of aspirational, dependency edges derived at index time instead of on every request, and a Neo4j read model for the transitive queries the Python path structurally couldn't answer. The part I'd point at is the GraphQL work: I added it to collapse a five-round-trip waterfall, measured it, and found it issues *more* SQL queries than the REST handlers it replaced — the win is round trips, not query count. I wrote that in the docstring instead of claiming the win everyone assumes."

### Why it was built

The premise is written down in `Documents/Deep_Reseacrh_idea_guide.md`, dated before the first commit: the category is split between cloud-locked enterprise tools and IDE plugins optimized for *generation*, and nobody owns "self-hostable, private, understanding-first." The cost side is in the Product Thesis section above — 2–3 week median time-to-first-commit, 6–10 weeks to senior velocity, and an `[EST]` $400k–$700k/year of dead weight for a 50-engineer org at 20% turnover.

The four surfaces map onto what a new engineer actually does: ask questions, follow a path, see the shape, verify retention. That mapping is the product design, and it's why the codebase has a learning engine and a graph engine at all rather than just a chatbot.

### How AI was used to build it — be specific about this

Four distinct modes. The distinction matters because "I used AI" is worth nothing in an interview while "here is the division of labor, and here is where I overrode it" is worth a great deal.

**Mode 1 — AI as research analyst, before any code was written.**
`Documents/Deep_Reseacrh_idea_guide.md` (291 lines) is a deep-research synthesis produced *before* the first commit: competitive analysis of Greptile/Bloop/Cody/Copilot/Cursor/Continue.dev with pricing and positioning; the AST-chunking literature; embedding model comparisons (voyage-code-3 vs. OpenAI vs. self-hostable Qwen3/Nomic); vector DB selection (Chroma for dev → Qdrant for prod → pgvector if you already run Postgres); hybrid search evidence; GitHub API scaling patterns; developer-tool UX principles; self-hosting deployment patterns.

**Multiple shipped architectural decisions trace directly to that document, and you can point at the fossils:**

| Research recommendation | Where it shows up in shipped code |
|---|---|
| Tree-sitter over regex chunking | 9 grammars in `tree_sitter_parser.py` |
| Chroma for dev, Qdrant for prod | `vector_db_type` and `qdrant_url` in `config.py` — present, unused, the documented exit |
| voyage-code-3 leads code-embedding benchmarks | `voyage_api_key` / `voyage_model = "voyage-code-3"` — present, unwired |
| SQLite default, Postgres for teams | `DATABASE_URL` is a plain SQLAlchemy URL |
| BYOK via env vars, never log keys | 112 env-tunable settings, `.env.example` with 61 documented vars |
| CodeTour export for "learning paths that actually help" | `codetour_schemas.py` + `export-tour` CLI command |
| Hybrid search is non-negotiable for code | The 6-profile scoring engine |

**Mode 2 — AI as implementation planner.**
`Documents/codebase-qa-implementation-guide.md` (4,705 lines) plus `codebaseqa-implementation-guide_part1.md` (1,794 lines) are AI-generated build plans — **6,499 lines of specification for a 24,400-line repo, a 1:4 plan-to-code ratio.** This is why commit `c25e999` could land 38 files and 3,315 lines on day one: the architecture was already decided. The honest tradeoff, worth volunteering: a plan that thorough biases you toward executing it rather than questioning it, and the LLM-generated-graph design that got thrown out a week later is exactly what that failure mode looks like.

**Mode 3 — AI as pair programmer, during the build.**
Visible in the code's texture: comments explaining *why* rather than what (`# Fix: Capture batch values at lambda definition time using defaults`; `# Use a thread-safe lock because this singleton can be used across worker threads`; `# Keep repo_root for compatibility/future expansion`), 85 structured `logger` calls with `%s` lazy formatting across 39 modules, uniformly typed signatures across 315 functions. Commits like `c208f3a` — 49 files, +8,014/−2,477 in one day — are not achievable at that quality by hand in that window. `docs/CODEBASE_DEEP_DIVE.md` is explicitly a generated artifact ("Generated on: 2026-02-15", 981 lines, file-by-file appendix) — AI as documentation generator over the finished system.

**Mode 4 — AI inside the product.** Seven call sites, seven different failure postures. See the table in the Architecture section. That table *is* the demonstration of expertise; a shallow implementation has one posture repeated seven times.

**Mode 5 — AI as auditor and reviewer, six months later.** `[Phase 2]`
This is the mode most people don't have a story for, and it's the most current one. All **12 Phase 2 commits carry `Co-Authored-By: Claude Opus 5`** — the AI involvement is recorded in git history rather than claimed, which means it's verifiable and you never have to be vague about it.

What makes this phase different from Mode 3 is the *shape* of the work. Phase 1 was generative: produce a large amount of correct code quickly. Phase 2 was adversarial: point the model at existing code and ask what's wrong with it. The output was 13 ranked findings, each reproduced before the fix and re-verified after, and the findings are of a kind that generative use never surfaces — a substring hostname check that becomes a token-exfiltration path, a CI invocation that silently skips a test directory, a `List[str]` annotation that makes a documented deployment path structurally impossible, a test that asserts against a framework's route table instead of the application's behavior.

The commit messages are the artifact to point at. They state the WHY, name the alternatives considered and why each was rejected (Fly.io's abandoned provider, Azure Container Apps' lack of block storage against SQLite's own corruption docs, `AsyncSession`'s concurrency semantics, GDS's licensing tier), and end with an explicit verification line — `"Verified with apps/api/.env moved aside and all provider keys unset: 142 passed, ruff clean."` **That last habit is the tell:** it came from discovering that a previous local green was an artifact of the developer's own `.env` file, so the verification method itself was corrected, not just the test.

The honest framing for an interview: *"I used AI to build it fast, and then six months later I used AI to attack what I'd built. The second pass found three credential-exposure paths and a CI pipeline that was proving nothing. I'd trust the second workflow more than the first."*

**Where the human overrode the AI — this is the part that reads as engineering judgment:**

- **Deleting the LLM from the graph engine.** The plan and V1 both had the model generating graph structure. Replaced with a deterministic import resolver because nondeterminism and hallucinated edges are unacceptable in a *map*. Result: cost per graph went to $0, p99 latency left the provider's SLA, and the output became reproducible and testable. The enrichment flag defaults to `false`.
- **Making the intent classifier deterministic with an LLM tiebreak, not an LLM classifier.** Cheaper, faster, testable; the model arbitrates only genuine ties.
- **Building quality gates that assume the model will fail.** Four gates, deterministic fallbacks, recorded failure reasons, persisted.
- **Re-validating every model-produced citation against the database.** Allowlist + extension check + existence check + line clamp.
- **The barrel-file fix.** No plan predicts that `export {};` will outrank your README. That came from watching real output on real repos (Documenso, cal.com, plane) and fixing it at three layers — indexer, retrieval scorer, and prompt — plus a permanent regression test.
- **The Ollama debugging saga.** Six diagnostic scripts, minimal-repro → isolate load → isolate content → isolate chunk size → verify fix. Produced three shipped settings and the retry-only-before-first-token rule.

### Interview prep — expected questions and where the answers live

| Question | Where to go |
|---|---|
| "Walk me through what happens when a user asks a question." | The **Request lifecycle** trace in Architecture. Nine numbered steps; know ④ ⑤ ⑦ cold. |
| "Why Tree-sitter instead of splitting on lines?" | WS-2 + the cAST +4.3 Recall@5 result |
| "How do you know your retrieval is any good?" | WS-3: barrel-file bug → three-layer fix → regression test → the eval fixture asserting `no_dependency_only_inference` |
| "How do you evaluate LLM output?" | WS-6: four decomposed proxies, thresholds, deterministic fallbacks, `quality_meta` attribution. Not vibes, not an LLM judge. |
| "How do you stop it hallucinating file references?" | The citation validator: allowlist + extension + existence + line-clamp against the `CodeFile` table |
| "What's the hardest bug you've fixed?" | The thread-pool closure bug (wrote the same batch N times, silently) or the background-task session/loop lifetime. Both corrupt data without raising. |
| "Tell me about a decision you reversed." | The graph engine: LLM-generated → deterministic. Numbers: 180 s timeout and nondeterministic → ~200–600 ms, reproducible, $0. |
| "How does this scale?" | Caps in WS-1/4/7, three-tier cache in WS-5, per-repo semaphore, and the honest ceiling: single-node SQLite + embedded Chroma. |
| "How did you use AI to build this?" | The four modes above — and pivot fast to *where you overrode it*. |
| "How do you handle provider rate limits?" | WS-11: header-aware backoff → jitter → four tuning knobs → eleven env vars → two unit tests |
| "How would you make this safe as a public demo?" | WS-12 — and note you already did |
| "Why is `learning_service.py` 2,360 lines?" | Own it immediately. Two subsystems that should be two modules; the seam is clean at line 1314. |
| "What would you do differently?" | The list below. Have it ready *before* they ask. |
| **"Tell me about a security bug you found."** | WS-16. Three credential paths in your own code: substring hostname match → token exfiltration, token in stderr → public SSE endpoint, live API key baked into a Docker image. |
| **"How do you know your tests are actually testing anything?"** | WS-16 — CI silently skipped ~20 cases and never constructed a Tree-sitter parser while green. And WS-21 — a local pass that was an artifact of the developer's `.env`. |
| **"When did you pick a technology and then reject it?"** | WS-18. Fly.io rejected for an abandoned Terraform provider; Azure Container Apps rejected because SQLite's own docs warn against network filesystems. |
| **"Tell me about an optimization that didn't work the way you expected."** | WS-21. GraphQL issues *more* SQL statements than the four REST handlers; the win is round trips, not queries — and the docstrings say so. |
| **"When do you reach for a graph database?"** | WS-20. Not for speed — for a query shape. `hops` was capped at 2 because each hop rescans the edge list: quadratic in Python, one variable-length pattern in Cypher. |
| **"How do you add a dependency without making it load-bearing?"** | WS-20. Default-off, `None` on misconfiguration, startup failure only logs, deletion ordered so the authoritative store survives a failure. |

### Known weaknesses — volunteer these before they're found

**Still open:**

1. **`learning_service.py` is ~2,400 lines holding two unrelated subsystems.** The graph engine (1314–2315) has zero dependency on the learning engine and should be `services/graph_service.py`. Phase 2 added to this file rather than splitting it, so the problem is now slightly worse.
2. **"Keyword" search is substring matching, not BM25**; fusion is a linear blend, not RRF. Both are the known upgrades. The trade: BM25 needs a second index; RRF discards the score magnitude the profile weights depend on.
3. **No auth, no multi-tenancy.** All state is scoped per *repository*, not per user. Right for a self-hosted single-user tool, blocking for anything else — and now the main thing standing between this and a team product, since Phase 2 gave it a real deployment.
4. **Indexing is full-rebuild only.** Content hashes are already computed and stored per chunk, so incremental is a diff-and-upsert away.
5. **SQLite + embedded Chroma means single-node.** Postgres and Qdrant are one env var each, but neither path has been exercised. Terraform provisions a single droplet with a single block volume, which matches this constraint honestly rather than papering over it.
6. **Bug-hunt line numbers aren't re-validated against the emitted snippet.** The model can claim a bug on line 34 of a 20-line snippet. Still the cheapest real fix in the repo.
7. **Frontend coverage is thin** — 457 lines across 6 files, and `graph-view.tsx` (908 lines, the most complex component) has none. Phase 2 added ~1,170 lines of *backend* tests and zero frontend tests, so the imbalance widened.
8. **The Neo4j traversals are not exposed through any route.** `reachable_from`, `blast_radius`, `shortest_path`, and `import_cycles` are implemented and tested but unreachable from the API or UI. The capability exists; the product surface doesn't.
9. **GraphQL covers only the learner read path.** Two queries and one mutation against a 37-endpoint REST surface — deliberate and stated, but it means two API styles now have to be maintained.
10. **The demo's cost model was never validated under real traffic.** The rate limits are reasoned, not measured.

**Closed in Phase 2 — worth mentioning as *fixed*, since the fix is the more interesting story:**

- ~~CI runs `--no-frozen-lockfile`~~ → fixed in `320fc56`, along with the discovery that **CI had been silently skipping ~20 test cases and never constructing a Tree-sitter parser.**
- ~~No deployed backend; `NEXT_PUBLIC_API_URL` never set~~ → fixed in `b07a400` with Terraform.
- ~~Graph derivation cost paid on every read~~ → fixed in `0cf2937`, moved to index time.
- ~~Multi-provider abstraction only ever built OpenAI clients~~ → fixed in `c0e68aa` with Azure OpenAI.
- ~~Progress bar could only show 0% or 100%; a killed index was unrecoverable~~ → fixed in `34c7490`.
- ~~Untracked debugging scripts in the working tree~~ → `.gitignore` updated in `98e5c76`.

### The surprising things

- **The vestigial config is a fossil record of the project's decision history.** `graph_max_files: 50`, `graph_prompt_max_chars: 10000`, `graph_min_edges: 15`, `graph_edge_max_tokens: 600` all still sit in [config.py:118-124](apps/api/src/config.py:118) — dead settings from the deleted LLM graph. `voyage_api_key` / `voyage_model` are fossils of the embedding research. `vector_db_type` / `qdrant_url` are fossils of the vector DB research. **You can read what this project considered and rejected out of its unused settings.**
- **112 environment-tunable settings and 19 runtime feature flags** in a 19-day solo project. `LEARNING_V2_ENABLED`, `GRAPH_DENSE_MODE_V21`, `CHAT_INTENT_ROUTING_ENABLED`, `CHAT_CONTENT_RERANK_ENABLED`, `NEXT_PUBLIC_GRAPH_DENSE_MODE_V21` — every risky subsystem shipped behind a flag with a documented rollback, including a frontend flag whose `.env.example` comment literally says *"Set to false for strict file-first fallback during rollback."* That is release engineering, not hobby code.
- **The same predicate is deliberately implemented twice**, at both ends of the pipeline: `_is_trivial_reexport` in the indexer, `_is_trivial_chunk` in the retrieval scorer. Catching barrel files at index time is cheaper; catching them at query time is the safety net for indexes that already exist. Duplication as defense-in-depth, not as an accident.
- **Idempotency is enforced in the database schema, not application code.** Two unique indexes — `(repository_id, achievement_key)` and `(repository_id, node_id)` — mean a double-click, a strict-mode double-render, or a refresh *cannot* inflate XP. The database refuses.
- **CI verifies compiled CSS.** `pnpm web:verify-css` exists because Tailwind v4 + Next 16 could produce a green build that shipped an unstyled page — invisible to the linter, the type checker, and the tests. Most people just live with that bug class.
- **The demo repo choice is a product decision, not a convenience.** `vercel/nextjs-subscription-payments` is real, recognizable, and moderately sized, so a visitor can independently judge whether the answers are *correct*. Demoing on a repo nobody knows proves nothing.
- **A cached answer still streams**, in 320-char slices — a cache hit is invisible to the user and the UI needs zero special-casing. Small, and exactly what separates a demo from a product.
- **`apps/api/data/` is 285 MB** — a 103 MB SQLite file and 181 MB of Chroma across **44 accumulated collection segments**: the physical residue of ~44 full index builds over a dozen real OSS repos in 19 days. It's the most honest scale evidence in the project, and it lives in `.gitignore`'d directories where nobody would ever look.
- **The frontend ships the retrieval trace to the user.** [chat-interface.tsx:15-23](apps/web/src/components/chat/chat-interface.tsx:15) types a `meta` object carrying intent, profile, grounding, and per-stage latency, rendered next to the answer. The system's self-assessment is a *user-facing feature*, not just a log line.

### If picked back up, in priority order

1. **Merge `feat/durable-indexing-progress` into `main`.** It's finished, tested, and unmerged.
2. **Expose the Neo4j traversals through a route and a UI affordance.** `blast_radius` answers *"what breaks if I change this file"* — arguably the single most valuable question the product could answer for a new engineer, and it's already implemented, tested, and unreachable. Highest value-per-effort item in the repo.
3. Split `learning_service.py` into `learning_service.py` + `graph_service.py` (clean seam at line 1314). Half a day; Phase 2 made this more urgent, not less.
4. Incremental re-indexing. The content hashes already exist; it's a diff and an upsert. Now cheaper than before, since `code_dependencies` gives a persisted edge set to diff against.
5. Real BM25 as the lexical arm with RRF fusion, benchmarked against the current linear blend using the eval fixture as the harness. That fixture has one case; it should have thirty. This is the change that turns "I tuned retrieval" into "I measured retrieval."
6. Auth + per-user state. Unblocks team deployments and turns the gamification layer from a personal toy into a shared onboarding tracker — the actual commercial wedge, and now the main thing standing between this and a team product.
7. Frontend tests for `graph-view.tsx` — highest complexity, lowest coverage, and the gap widened in Phase 2.
8. Clamp bug-hunt line numbers against the snippet.

---

## Sources for external numbers cited above

- [cAST: Enhancing Code RAG with Structural Chunking via AST (EMNLP 2025 Findings)](https://aclanthology.org/2025.findings-emnlp.430/) — +4.3 Recall@5 on RepoEval, +2.67 Pass@1 on SWE-bench for AST-aware chunking
- [Time to First Commit benchmarks — em-tools.io](https://www.em-tools.io/engineering-metrics/time-to-first-commit) — 2–3 week industry median, DORA elite 1–2 days
- [Developer Onboarding 90-Day Guide — Full Scale](https://fullscale.io/blog/software-developer-onboarding-guide/) — senior 6–10 weeks to 90% velocity, junior 4–6 months
- [7 AI Tools for Codebase Onboarding — Security Boulevard](https://securityboulevard.com/2026/06/7-ai-tools-for-codebase-onboarding-and-understanding/) and [Greptile Review — Stackpick](https://stackpick.net/tools/greptile/) — Greptile $30/seat/mo, DeepWiki free + public-only, Cody Enterprise ~$16k/yr
- [OpenAI Embedding Pricing 2026 — embeddingcost.com](https://embeddingcost.com/openai) — `text-embedding-3-small` at $0.02 / 1M tokens
