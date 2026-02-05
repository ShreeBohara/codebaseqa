import asyncio
import httpx
import time

OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = "deepseek-r1:8b"
EMBED_MODEL = "nomic-embed-text"

async def call_llm():
    print(f"🤖 Requesting LLM ({LLM_MODEL})...")
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": "Summarize the history of computing in 10 words."}],
                "stream": False
            }
        )
        if resp.status_code == 200:
            print("✅ LLM success")
        else:
            print(f"❌ LLM failed: {resp.status_code} - {resp.text}")

async def call_embedding():
    print(f"🧠 Requesting Embedding ({EMBED_MODEL})...")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": EMBED_MODEL,
                "prompt": "This is a test sentence to embed."
            }
        )
        if resp.status_code == 200:
            print("✅ Embedding success")
        else:
            print(f"❌ Embedding failed: {resp.status_code} - {resp.text}")

async def main():
    print("Testing concurrent model switching in Ollama...")
    
    # 1. Warm up embedding
    await call_embedding()
    
    # 2. Call LLM (forcing swap)
    await call_llm()
    
    # 3. Call Embedding again immediately (forcing swap back)
    await call_embedding()
    
    # 4. Try concurrent calls
    print("\nAttempting concurrent calls...")
    await asyncio.gather(
        call_llm(),
        call_embedding(),
        call_embedding()
    )

if __name__ == "__main__":
    asyncio.run(main())
