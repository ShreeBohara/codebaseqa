import asyncio
import logging
import sys
import os
import random
import string

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("diagnose_load")

def generate_large_text(kb_size: int = 4) -> str:
    """Generate random text of roughly kb_size KB."""
    # 1 KB = 1024 chars approx (1 byte per char ascii)
    return ''.join(random.choices(string.ascii_letters + string.digits + " \n", k=kb_size * 1024))

async def main():
    print("🐘 Starting Heavy Load Diagnosis for Ollama...")
    
    from src.core.embeddings.ollama_embeddings import OllamaEmbeddings
    
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    
    # Generate 50 large chunks (mimicking code files)
    print("   Generating 50 synthetic large chunks (4KB each)...")
    texts = [generate_large_text(4) for _ in range(50)]
    
    print(f"   Sending {len(texts)} large texts to Ollama sequentially...")
    print("   Total data: ~200 KB. Context per chunk: ~1000 tokens.")
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        results = await embeddings.embed_texts(texts)
        duration = asyncio.get_event_loop().time() - start_time
        print(f"\n✅ Success! Embedded {len(results)} chunks in {duration:.2f}s")
        print(f"   Average time per chunk: {duration/len(results):.2f}s")
        
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        # We expect to see retry logs in stdout if it fails

if __name__ == "__main__":
    asyncio.run(main())
