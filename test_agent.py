"""
Test script for News Agent with fallback options
"""
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_openai():
    """Test if OpenAI works"""
    try:
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ No OpenAI API key")
            return False

        llm = ChatOpenAI()
        response = llm.invoke("Say 'OpenAI works!'")
        print(f"✅ OpenAI: {response.content}")
        return True
    except Exception as e:
        print(f"❌ OpenAI failed: {e}")
        return False

def test_agent_fallback():
    """Test agent with fallback logic"""
    try:
        from src.agents.news_agent import NewsAgent

        print("🔄 Testing agent with OpenAI fallback...")
        agent = NewsAgent(
            model_name="gpt-4",
            use_openai=True,  # Force OpenAI
            enable_search=False,  # Skip search for now
            timeout=15
        )

        result = agent.research("What is AI?")
        if result['success']:
            print("✅ Agent works!")
            print(f"Response: {result['response'][:100]}...")
        else:
            print(f"❌ Agent failed: {result['error']}")

    except Exception as e:
        print(f"❌ Agent test failed: {e}")

def main():
    print("🧪 Testing News Agent Setup")
    print("="*50)

    # Test OpenAI
    openai_works = test_openai()

    if openai_works:
        print("\n🚀 Testing agent with OpenAI...")
        test_agent_fallback()
    else:
        print("\n💡 To test the agent:")
        print("1. Get an OpenAI API key")
        print("2. Add OPENAI_API_KEY to .env")
        print("3. Run: python test_agent.py")

if __name__ == "__main__":
    main()