#!/usr/bin/env python3
"""Comprehensive system test for the censorship cross-checker."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules import successfully."""
    print("🔍 Testing module imports...")
    try:
        from agents.news_agent import NewsAgent
        from agents.bias_langgraph_agent import BiasLangGraphAgent
        from ingestion.fetcher import SourceFetcher
        from ingestion.normalizer import ContentNormalizer
        from ingestion.cache_reader import CachedSourceRepository
        from pipelines.bias_scoring import score_bias
        from pipelines.embedding_cluster import cluster_articles
        from utils.config import load_censorship_config
        from utils.model_helper import get_chat_model
        print("   ✅ All modules imported successfully")
        return True
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    print("🔍 Testing configuration...")
    try:
        from utils.config import load_censorship_config
        config = load_censorship_config()
        print(f"   ✅ Config loaded with {len(config.sources)} sources")
        print(f"   ✅ Bias thresholds: low={config.bias_thresholds.low_bias}, high={config.bias_thresholds.high_bias}")
        print(f"   ✅ Clustering: {config.clustering.method} with {config.clustering.num_clusters} clusters")
        return True
    except Exception as e:
        print(f"   ❌ Config test failed: {e}")
        return False


def test_normalizer():
    """Test content normalization."""
    print("🔍 Testing content normalizer...")
    try:
        from ingestion.normalizer import ContentNormalizer
        normalizer = ContentNormalizer()
        html = "<html><body><p>Hello World</p></body></html>"
        result = normalizer.normalize("test_source", html)
        assert "Hello World" in result.text
        assert result.language in ["en", None]
        print("   ✅ Normalizer working correctly")
        return True
    except Exception as e:
        print(f"   ❌ Normalizer test failed: {e}")
        return False


def test_clustering():
    """Test embedding and clustering."""
    print("🔍 Testing clustering...")
    try:
        from pipelines.embedding_cluster import ArticleRecord, cluster_articles
        articles = [
            ArticleRecord("source1", "President announces new policy", {"state_aligned": False}),
            ArticleRecord("source2", "Government reveals policy changes", {"state_aligned": True}),
        ]
        clusters = cluster_articles(articles)
        print(f"   ✅ Clustered {len(articles)} articles into {len(clusters)} cluster(s)")
        return True
    except Exception as e:
        print(f"   ❌ Clustering test failed: {e}")
        return False


def test_bias_scoring():
    """Test bias scoring."""
    print("🔍 Testing bias scoring...")
    try:
        from pipelines.embedding_cluster import ArticleRecord
        from pipelines.bias_scoring import score_bias
        articles = [
            ArticleRecord("source1", "Great progress made today", {"state_aligned": True}),
            ArticleRecord("source2", "Crisis continues unabated", {"state_aligned": False}),
        ]
        score = score_bias(articles)
        print(f"   ✅ Bias score computed: coverage={score.coverage_delta:.2f}, "
              f"sentiment={score.sentiment_delta:.2f}, omission={score.omission_ratio:.2f}")
        return True
    except Exception as e:
        print(f"   ❌ Bias scoring test failed: {e}")
        return False


def test_cache_reader():
    """Test cache reader."""
    print("🔍 Testing cache reader...")
    try:
        from ingestion.cache_reader import CachedSourceRepository
        repo = CachedSourceRepository()
        entries = repo.get_recent_entries(limit=5)
        print(f"   ✅ Cache reader found {len(entries)} cached entries")
        return True
    except Exception as e:
        print(f"   ❌ Cache reader test failed: {e}")
        return False


def main():
    print("=" * 60)
    print("🧪 COMPREHENSIVE SYSTEM TEST")
    print("=" * 60)
    print()
    
    tests = [
        test_imports,
        test_config,
        test_normalizer,
        test_clustering,
        test_bias_scoring,
        test_cache_reader,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("=" * 60)
        print()
        print("🎉 System is ready!")
        print()
        print("Next steps:")
        print("  • Run: python test_agent.py")
        print("  • Run: python test_ingestion.py")
        print("  • Run: python src/agents/news_agent.py")
        return 0
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total} passed)")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
