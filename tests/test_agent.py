"""Smoke tests for the Holistic AI-powered News Agent."""

import os
from dotenv import load_dotenv

# Load environment early so credential checks work
load_dotenv()


def credentials_available() -> bool:
    """Verify the required Holistic AI credentials are present."""
    required_vars = ["HOLISTIC_AI_TEAM_ID", "HOLISTIC_AI_API_TOKEN"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        return False

    print("✅ Holistic AI credentials detected")
    return True


def run_agent_smoke_test() -> bool:
    """Instantiate the agent and run a minimal query."""
    from src.agents.news_agent import NewsAgent

    try:
        agent = NewsAgent(enable_search=False)
        status = agent.get_agent_status()
        print("✅ Agent initialized")
        print(f"   Model: {status['model']}")
        print(f"   Metrics enabled: {status['metrics_enabled']}")
    except Exception as exc:
        print(f"❌ Agent initialization failed: {exc}")
        return False

    try:
        result = agent.research("What are some key principles for effective news research and analysis?")
        if result.get("success"):
            response_text = result["response"]
            if isinstance(response_text, list):
                response_text = str(response_text)
            preview = response_text[:120].strip().replace("\n", " ")
            print("✅ Research call succeeded")
            print(f"   Response preview: {preview}...")
            return True

        print(f"⚠️ Research call returned an error: {result.get('error', 'unknown error')}")
        return False
    except Exception as exc:
        print(f"❌ Research call failed: {exc}")
        return False


def main():
    print("🧪 Testing News Agent Setup")
    print("=" * 50)

    if not credentials_available():
        print("\n💡 Populate the missing variables in .env and retry.")
        return

    success = run_agent_smoke_test()
    if success:
        print("\n🎉 All checks passed!")
    else:
        print("\n⚠️ One or more checks failed. Review the log above for details.")

if __name__ == "__main__":
    main()