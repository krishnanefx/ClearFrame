#!/usr/bin/env python3
"""
Demonstration of Valyu Search integration in NewsAgent.

This script shows:
1. How Valyu search is enabled by default
2. Real-time news queries using Valyu
3. Narrative comparison with live data
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.news_agent import NewsAgent


def demo_basic_valyu_search():
    """Demonstrate basic Valyu search functionality."""
    print("=" * 70)
    print("DEMO 1: Basic Valyu Search")
    print("=" * 70)
    
    # NewsAgent now has enable_search=True by default
    agent = NewsAgent(model_name="claude-3-5-sonnet")
    
    # Check agent status
    status = agent.get_agent_status()
    print(f"\n📊 Agent Status:")
    print(f"  - Model: {status['model']}")
    print(f"  - Tools available: {status['tools_available']}")
    print(f"  - Valyu enabled: {'ValyuSearchTool' in status['tools_available']}")
    
    # Test query
    query = "Latest news on AI regulations in Europe November 2025"
    print(f"\n🔍 Searching: {query}")
    
    result = agent.research(query, max_sources=5)
    
    print(f"\n✅ Success: {result['success']}")
    if result['success']:
        print(f"📝 Response preview: {result['response'][:200]}...")
        print(f"🔧 Tools used: {result['used_tools']}")
    else:
        print(f"❌ Error: {result.get('error')}")


def demo_narrative_comparison_live():
    """Demonstrate narrative comparison with fresh fetching."""
    print("\n" + "=" * 70)
    print("DEMO 2: Narrative Comparison with Live Fetching")
    print("=" * 70)
    
    agent = NewsAgent(model_name="claude-3-5-sonnet", enable_search=True)
    
    topic = "climate policy"
    print(f"\n📰 Topic: {topic}")
    print("🔄 Fetching fresh articles from all configured sources...")
    
    # This will use Valyu to search for region-specific narratives
    result = agent.compare_narratives(
        topic=topic,
        fetch_fresh=True,  # Enable live fetching with Valyu
        max_articles=15,
        time_window_hours=48.0
    )
    
    if result['success']:
        print(f"\n✅ Analysis Complete")
        print(f"\n📊 Statistics:")
        print(f"  - Total articles: {result['total_articles']}")
        print(f"  - Events detected: {result['total_events']}")
        print(f"  - State-aligned: {result.get('total_state_articles', 0)}")
        print(f"  - Independent: {result.get('total_independent_articles', 0)}")
        print(f"  - Coverage balance: {result.get('coverage_balance', 0.0):.2f}")
        print(f"  - Sentiment delta: {result.get('sentiment_delta', 0.0):.2f}")
        
        if result.get('state_emphasis'):
            print(f"\n🔴 State sources emphasize: {', '.join(result['state_emphasis'][:5])}")
        
        if result.get('independent_emphasis'):
            print(f"🔵 Independent sources emphasize: {', '.join(result['independent_emphasis'][:5])}")
        
        if result.get('key_omissions'):
            print(f"\n⚠️  Omissions in state media:")
            for omission in result['key_omissions'][:5]:
                print(f"    - {omission}")
    else:
        print(f"\n❌ Error: {result.get('error')}")


def demo_cached_vs_live():
    """Compare cached vs live data fetching."""
    print("\n" + "=" * 70)
    print("DEMO 3: Cached vs Live Data Comparison")
    print("=" * 70)
    
    agent = NewsAgent(model_name="claude-3-5-sonnet")
    
    topic = "news"
    
    # Cached analysis
    print("\n📦 Using cached data...")
    cached_result = agent.compare_narratives(
        topic=topic,
        fetch_fresh=False,
        max_articles=10
    )
    
    print(f"  - Articles found (cached): {cached_result.get('total_articles', 0)}")
    print(f"  - Events detected (cached): {cached_result.get('total_events', 0)}")
    
    # Live analysis (with Valyu)
    print("\n🔴 LIVE: Using fresh data with Valyu...")
    print("  (This would fetch real-time data from all sources)")
    print("  (Uncomment below to test with real API calls)")
    
    # Uncomment to test live fetching:
    # live_result = agent.compare_narratives(
    #     topic=topic,
    #     fetch_fresh=True,
    #     max_articles=10
    # )
    # print(f"  - Articles found (live): {live_result.get('total_articles', 0)}")
    # print(f"  - Events detected (live): {live_result.get('total_events', 0)}")


def main():
    """Run all demonstrations."""
    print("\n🚀 Valyu Integration Demonstration")
    print("=" * 70)
    print("NewsAgent now uses Valyu search by default for real-time queries")
    print("=" * 70)
    
    # Demo 1: Basic search
    demo_basic_valyu_search()
    
    # Demo 2: Narrative comparison with live data
    # Uncomment to test with real API calls:
    # demo_narrative_comparison_live()
    
    # Demo 3: Cached vs live comparison
    demo_cached_vs_live()
    
    print("\n" + "=" * 70)
    print("✅ Demonstration complete!")
    print("\nKey features enabled:")
    print("  ✓ Valyu search enabled by default")
    print("  ✓ Real-time news queries")
    print("  ✓ Region-specific narrative detection")
    print("  ✓ Cross-source comparison")
    print("  ✓ Censorship detection via coverage analysis")
    print("=" * 70)


if __name__ == "__main__":
    main()
