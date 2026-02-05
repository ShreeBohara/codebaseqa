import asyncio
import logging
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

# Setup logging to see retry warnings
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("src.core.embeddings.ollama_embeddings")
logger.setLevel(logging.DEBUG)

async def main():
    print("🧪 Testing OllamaEmbeddings with Retries...\n")
    
    from src.core.embeddings.ollama_embeddings import OllamaEmbeddings
    
    # Initialize
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    
    # Create a batch of texts to simulated load
    texts = [f"This is test sentence number {i} to verify robust embedding." for i in range(20)]
    
    print(f"   Sending {len(texts)} texts to Ollama...")
    try:
        results = await embeddings.embed_texts(texts)
        print(f"\n✅ Success! Received {len(results)} embeddings.")
        if len(results) > 0:
            print(f"   Dimension: {len(results[0])}")
            
    except Exception as e:
        print(f"\n❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
