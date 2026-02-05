
import asyncio
import logging
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("diagnose_content")

# This approximates the content that failed (mix of prose and maybe some code)
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
""" * 10  # Repeat to reach ~3000 chars

async def main():
    print("🔬 Starting Content Diagnosis...")
    from src.core.embeddings.ollama_embeddings import OllamaEmbeddings
    
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    
    text = MIXED_CONTENT
    print(f"   Embedding text of length {len(text)}...")
    
    try:
        # Embed single text
        result = await embeddings.embed_texts([text])
        print(f"✅ Success! Vector dimension: {len(result[0])}")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
