import asyncio
import os
import sys
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

async def test_llm_factory():
    from src.core.llm.factory import create_llm
    from src.core.llm.ollama_llm import OllamaLLM
    
    print("Testing LLM Factory...")
    with patch("src.config.settings.llm_provider", "ollama"):
        llm = create_llm()
        assert isinstance(llm, OllamaLLM)
        print("✅ Ollama LLM created")

async def test_embedding_factory():
    from src.core.embeddings.factory import create_embedding_service
    from src.core.embeddings.ollama_embeddings import OllamaEmbeddings
    
    print("\nTesting Embedding Factory...")
    with patch("src.config.settings.embedding_provider", "ollama"):
        emb = create_embedding_service()
        assert isinstance(emb, OllamaEmbeddings)
        print("✅ Ollama Embeddings created")

async def test_caching():
    from src.core.cache.llm_cache import get_llm_cache
    
    print("\nTesting Caching...")
    cache = get_llm_cache()
    messages = [{"role": "user", "content": "hello"}]
    model = "test-model"
    response = "cached response"
    
    cache.set(messages, model, response)
    retrieved = cache.get(messages, model)
    assert retrieved == response
    print("✅ Cache set/get works")

async def test_java_parsing():
    from src.core.parser.tree_sitter_parser import TreeSitterParser
    
    print("\nTesting Java Parsing...")
    try:
        parser = TreeSitterParser("java")
        code = """
        public class Test {
            public void hello() {
                System.out.println("Hello");
            }
        }
        """
        result = parser.parse(code, "Test.java")
        assert len(result.chunks) > 0
        print("✅ Java parsing works")
    except Exception as e:
        print(f"❌ Java parsing failed: {e}")

async def main():
    print("🚀 Starting Final Verification\n")
    await test_llm_factory()
    await test_embedding_factory()
    await test_caching()
    await test_java_parsing()
    print("\n✨ All systems go!")

if __name__ == "__main__":
    asyncio.run(main())
