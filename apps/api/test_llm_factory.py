import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

# Mock settings for testing
from unittest.mock import patch, MagicMock
from src.core.llm.factory import create_llm
from src.core.llm.ollama_llm import OllamaLLM
from src.core.llm.openai_llm import OpenAILLM

async def main():
    print("🧪 Testing LLM Factory and Providers...\n")

    # Test 1: Factory creates OpenAI (default)
    print("1. Testing OpenAI Factory Creation (Default)...")
    with patch("src.config.settings.llm_provider", "openai"):
        llm = create_llm()
        if isinstance(llm, OpenAILLM):
            print("   ✅ Created OpenAILLM correctly")
        else:
            print(f"   ❌ Failed: Created {type(llm)}")

    # Test 2: Factory creates Ollama
    print("\n2. Testing Ollama Factory Creation...")
    with patch("src.config.settings.llm_provider", "ollama"):
        with patch("src.config.settings.ollama_base_url", "http://localhost:11434"):
            with patch("src.config.settings.ollama_model", "llama3.1"):
                llm = create_llm()
                if isinstance(llm, OllamaLLM):
                    print("   ✅ Created OllamaLLM correctly")
                else:
                    print(f"   ❌ Failed: Created {type(llm)}")

                # Test 3: Ollama Connectivity (Real Check)
                print("\n3. Testing Local Ollama Connectivity...")
                print(f"   Connecting to {llm._base_url}...")
                is_healthy = await llm.health_check()
                if is_healthy:
                    print("   ✅ Ollama is reachable and healthy!")
                    
                    # Try a simple generation if healthy
                    print("\n   Attempting simple generation...")
                    try:
                        response = await llm.generate([{"role": "user", "content": "Say 'Core systems functional' and nothing else."}])
                        print(f"   ✅ Response received: {response}")
                    except Exception as e:
                        print(f"   ⚠️ Generation failed (model might need pulling): {e}")
                        print("   Run: ollama pull llama3.1")
                else:
                    print("   ❌ Ollama is NOT reachable. Is it running?")
                    print("   Run: ollama serve")

if __name__ == "__main__":
    asyncio.run(main())
