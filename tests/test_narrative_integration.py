#!/usr/bin/env python3
"""
Test the integrated narrative comparison feature in NewsAgent.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.news_agent import NewsAgent


def test_compare_narratives_cached():
    """Test narrative comparison using cached articles."""
    print("=" * 70)
    print("Testing NewsAgent.compare_narratives() with cached data")
    print("=" * 70)
    
    # Initialize agent
    agent = NewsAgent(
        model_name="claude-3-5-sonnet",
        enable_search=False  # Use cached data only
    )
    
    # Test with a topic that should be in the cached BBC articles
    topic = "news"  # Generic term likely to match cached content
    
    print(f"\n📰 Analyzing topic: '{topic}'")
    print("Using cached articles from ingestion layer...")
    
    result = agent.compare_narratives(
        topic=topic,
        fetch_fresh=False,  # Use cache
        max_articles=10,
        time_window_hours=72.0
    )
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    print(f"\n✅ Success: {result['success']}")
    
    if result['success']:
        print(f"\n📊 Statistics:")
        print(f"  - Total articles analyzed: {result['total_articles']}")
        print(f"  - Total events detected: {result['total_events']}")
        print(f"  - State-aligned articles: {result.get('total_state_articles', 0)}")
        print(f"  - Independent articles: {result.get('total_independent_articles', 0)}")
        print(f"  - Coverage balance (state/independent): {result.get('coverage_balance', 0.0)}")
        print(f"  - Sentiment delta: {result.get('sentiment_delta', 0.0)}")
        
        if result['events']:
            print(f"\n🎯 Detected Events:")
            for i, event in enumerate(result['events'][:3], 1):  # Show first 3
                print(f"\n  Event {i}:")
                print(f"    - Entities: {', '.join(event['entities'][:5])}")
                print(f"    - Articles: {event['article_count']}")
                print(f"    - State-aligned: {event['state_aligned_count']}")
                print(f"    - Independent: {event['independent_count']}")
                print(f"    - Time range: {event['time_range']}")
        
        if result.get('state_emphasis'):
            print(f"\n🔴 State-Aligned Sources Emphasize:")
            for entity in result['state_emphasis'][:5]:
                print(f"    - {entity}")
        
        if result.get('independent_emphasis'):
            print(f"\n🔵 Independent Sources Emphasize:")
            for entity in result['independent_emphasis'][:5]:
                print(f"    - {entity}")
        
        if result.get('key_omissions'):
            print(f"\n⚠️  Key Omissions (in state media):")
            for entity in result['key_omissions'][:5]:
                print(f"    - {entity}")
    else:
        print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 70)
    return result['success']


def test_compare_narratives_api_format():
    """Test that the output format matches the expected API response."""
    print("\n" + "=" * 70)
    print("Testing API Response Format")
    print("=" * 70)
    
    agent = NewsAgent(model_name="claude-3-5-sonnet", enable_search=False)
    
    result = agent.compare_narratives("news", fetch_fresh=False, max_articles=5)
    
    # Verify expected keys
    expected_keys = [
        'topic', 'success', 'events', 'state_emphasis', 
        'independent_emphasis', 'key_omissions', 'sentiment_delta', 'coverage_balance'
    ]
    
    print("\n✓ Checking response structure...")
    for key in expected_keys:
        if key in result:
            print(f"  ✅ '{key}': present")
        else:
            print(f"  ❌ '{key}': MISSING")
    
    # Check types
    print("\n✓ Checking data types...")
    checks = [
        ('topic', str),
        ('success', bool),
        ('events', list),
        ('state_emphasis', list),
        ('independent_emphasis', list),
        ('key_omissions', list),
        ('sentiment_delta', (int, float)),
        ('coverage_balance', (int, float))
    ]
    
    all_correct = True
    for key, expected_type in checks:
        if key in result:
            actual_type = type(result[key])
            if isinstance(result[key], expected_type):
                print(f"  ✅ '{key}': {actual_type.__name__}")
            else:
                print(f"  ❌ '{key}': expected {expected_type}, got {actual_type}")
                all_correct = False
    
    print("\n" + "=" * 70)
    return all_correct


def main():
    """Run all tests."""
    print("\n🚀 Starting Narrative Comparison Integration Tests\n")
    
    test1_passed = test_compare_narratives_cached()
    test2_passed = test_compare_narratives_api_format()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Test 1 (Cached Narrative Comparison): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (API Format Validation): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
