
import asyncio
import logging
import sys
import os
import httpx

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("diagnose_fix")

# Same mixed content as before
MIXED_CONTENT = """
# RAG System Architecture

The RAG (Retrieval-Augmented Generation) system is designed to provide context-aware answers.

## Components

1. **Ingestion Pipeline**:
    - Clones repositories
    - Parses code using tree-sitter
    - Chunks content based on semantic boundaries
    
2. **Vector Store (ChromaDB)**:
    - Stores embeddings
    - Supports metadata filtering

3. **Query Engine**:
    - Embeds user query
    - Retrieves top-k matches
    - Reranks results (optional)

## Configuration

```typescript
export const RAGConfig = {
    chunkSize: 1500,
    overlap: 200,
    model: "nomic-embed-text",
    topK: 10
}
```

The system ensures that `keep_alive` is maintained during heavy indexing loads to prevent model thrashing.
When `Ollama` returns 500, we retry with exponential backoff.
""" * 10  # Repeat to reach ~3000 chars (actually ~8000)

async def main():
    print("🚑 Testing Fix (Explicit Context Size)...")
    
    url = "http://localhost:11434/api/embeddings"
    
    # Try with explicit context options
    payload = {
        "model": "nomic-embed-text",
        "prompt": MIXED_CONTENT,
        "options": {
            "num_ctx": 2048  # Force smaller context
        }
    }
    
    print(f"   Sending request with num_ctx=2048, length={len(MIXED_CONTENT)}...")
    
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                print("✅ Success! Fixed with explicit context.")
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
