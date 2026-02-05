
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
logger = logging.getLogger("diagnose_chunk_size")

# Same mixed content as before, but we will truncate it
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
""" * 10  

async def main():
    print("📏 Testing Safe Chunk Size (2000 chars / ~500 tokens)...")
    
    url = "http://localhost:11434/api/embeddings"
    
    # Truncate to 2000 chars
    safe_content = MIXED_CONTENT[:2000]
    
    payload = {
        "model": "nomic-embed-text",
        "prompt": safe_content,
    }
    
    print(f"   Sending request text length={len(safe_content)}...")
    
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                print("✅ Success! 2000 chars is safe.")
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
