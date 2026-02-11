# CodebaseQA CLI

Command-line interface for CodebaseQA.

## Installation

```bash
cd cli
pip install -e .
```

## Usage

```bash
# Index a repository
codebaseqa index https://github.com/expressjs/express

# List indexed repositories
codebaseqa list

# Ask a question
codebaseqa ask <repo_id> "What is the main entry point?"

# Search code
codebaseqa search <repo_id> "authentication"

# List generated lessons (default persona: new_hire)
codebaseqa lessons <repo_id>

# Export lesson as VS Code CodeTour
codebaseqa export-tour <repo_id> <lesson_id>
```

## Requirements

The API server must be running at `http://localhost:8000` by default.
Set `CODEBASEQA_API_URL` to target a different host.

```bash
cd apps/api
uvicorn src.main:app --reload
```
