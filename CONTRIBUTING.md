# Contributing to CodebaseQA

Thanks for your interest in improving CodebaseQA.

## Ways to Contribute

- Report bugs
- Propose features
- Improve docs
- Submit fixes or enhancements
- Add tests for edge cases and regressions

## Development Setup

Prerequisites:

- Node.js 20+
- pnpm 10+
- Python 3.11+

From repository root:

```bash
pnpm install
```

Backend setup:

```bash
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

Frontend setup (new terminal, repo root):

```bash
pnpm web:dev
```

## Run Checks Before Opening a PR

Backend:

```bash
cd apps/api
source venv/bin/activate
python -m pytest tests/unit tests/integration
ruff check src tests
```

Frontend:

```bash
pnpm --filter web lint
pnpm --filter web type-check
pnpm --filter web test -- --run
pnpm --filter web build
```

## Pull Request Guidelines

- Keep PRs focused and small enough to review.
- Add or update tests for behavior changes.
- Update docs/README when changing setup, features, or APIs.
- For UI changes, include before/after screenshots or a short video.
- Ensure CI passes before requesting review.

## Issue Guidelines

- Use the bug or feature templates where possible.
- Include exact reproduction steps and environment details.
- Link related issues/PRs if they exist.

## Code Style

- Python: Ruff rules in this repository.
- TypeScript/React: follow existing lint/format patterns in `apps/web`.
- Prefer clear naming and small, composable functions over clever shortcuts.

## Branch and Commit Tips

- Branch naming examples: `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`.
- Commit message style recommendation: `type(scope): summary`.
  Example: `fix(indexing): reset stale vectors before reindex`.
