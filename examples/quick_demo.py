#!/usr/bin/env python3
"""Quick demo of the Valyu + HolisticAI integration"""

import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

from examples.valyu_holisticai_agent import create_news_analysis_agent

print("=" * 70)
print("🚀 Valyu Search + HolisticAI News Analysis Demo")
print("=" * 70)

# Create the agent
print("\n📊 Initializing agent...")
agent = create_news_analysis_agent()
print("✅ Agent ready!")

# Run a simple analysis
print("\n🔍 Analyzing news coverage...")
print("-" * 70)

query = """
Search for recent news about artificial intelligence from BBC News.
Provide:
1. Article titles and URLs
2. Sentiment analysis
3. Key topics mentioned
"""

print(f"Query: {query.strip()}")
print("\n" + "-" * 70)
print("Agent response:\n")

response = agent.invoke({"input": query})
print(response['output'])

print("\n" + "=" * 70)
print("✅ Demo complete!")
print("\n💡 Try more queries:")
print("  - Compare coverage from multiple sources")
print("  - Analyze bias in specific topics")
print("  - Extract entities and sentiment")
print("\n📖 See examples/README_VALYU_HOLISTICAI.md for full documentation")
print("=" * 70)
