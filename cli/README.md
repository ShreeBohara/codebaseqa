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
```

## Requirements

The API server must be running at `http://localhost:8000`.

```bash
cd apps/api
uvicorn src.main:app --reload
```
