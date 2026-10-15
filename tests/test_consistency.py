"""
Consistency Tests for Track A: Iron Man

Tests proving that the agent produces consistent, reliable outputs for the same inputs.
This is critical for production readiness.
"""

import pytest
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.basic_cli import (
    analyze_articles_bias,
    fetch_with_category_coverage,
    compute_censorship_radar,
)
from src.analysis.bias_metrics import ArticleBiasProfile, classify_source


# Fixture: Sample articles for deterministic testing
@pytest.fixture
def sample_articles():
    """Fixed set of articles for consistency testing."""
    return [
        {
            "title": "UN calls for humanitarian ceasefire in conflict zone",
            "description": "United Nations officials announced urgent calls for ceasefire to allow humanitarian aid delivery to displaced civilians.",
            "source": "reuters.com",
            "url": "https://reuters.com/article1"
        },
        {
            "title": "Government reports military victory in regional conflict",
            "description": "State media highlights military success and denies civilian casualty reports from international observers.",
            "source": "tass.com",
            "url": "https://tass.com/article2"
        },
        {
            "title": "Activist blog documents humanitarian crisis",
            "description": "Grassroots activists share eyewitness accounts of shortages, displacement, and blocked aid routes.",
            "source": "medium.com",
            "url": "https://medium.com/activist-blog"
        },
        {
            "title": "BBC reports balanced coverage of ongoing crisis",
            "description": "International journalists provide context including government position, opposition voices, and humanitarian concerns.",
            "source": "bbc.com",
            "url": "https://bbc.com/news/article4"
        },
        {
            "title": "State television broadcasts stability message",
            "description": "Official channels emphasize order and security while minimizing international criticism.",
            "source": "cgtn.com",
            "url": "https://cgtn.com/broadcast5"
        }
    ]


class TestBiasAnalysisConsistency:
    """Test that bias analysis produces identical results for identical inputs."""
    
    def test_same_article_same_bias_scores(self, sample_articles):
        """Verify that analyzing the same article twice gives identical bias scores."""
        article = sample_articles[0]
        
        # Analyze twice
        profile1 = ArticleBiasProfile(article)
        result1 = profile1.analyze()
        
        profile2 = ArticleBiasProfile(article)
        result2 = profile2.analyze()
        
        # Scores should be identical (deterministic)
        assert result1['bias_scores'] == result2['bias_scores'], \
            "Bias scores not deterministic for same article"
        
        # Classification should be identical
        assert result1['classification'] == result2['classification'], \
            "Classification not deterministic for same article"
    
    def test_batch_analysis_consistency(self, sample_articles):
        """Verify batch analysis is consistent across runs."""
        # Run analysis twice
        result1 = analyze_articles_bias(sample_articles)
        result2 = analyze_articles_bias(sample_articles)
        
        # Article count should match
        assert result1['article_count'] == result2['article_count']
        
        # Aggregate stats should be identical
        assert result1['aggregate_stats'] == result2['aggregate_stats'], \
            "Aggregate statistics not consistent across runs"
        
        # Per-article scores should match
        for i in range(len(result1['articles'])):
            art1 = result1['articles'][i]
            art2 = result2['articles'][i]
            assert art1['bias_scores'] == art2['bias_scores'], \
                f"Article {i} bias scores differ across runs"
    
    def test_source_classification_deterministic(self):
        """Verify source classification is deterministic."""
        test_sources = [
            "reuters.com",
            "tass.com",
            "medium.com",
            "bbc.com",
            "foxnews.com",
            "rt.com"
        ]
        
        for source in test_sources:
            # Classify multiple times
            results = [classify_source(source) for _ in range(5)]
            
            # All should be identical
            assert all(r == results[0] for r in results), \
                f"Source classification for {source} is not deterministic"


class TestCensorshipRadarConsistency:
    """Test that censorship radar metrics are deterministic."""
    
    def test_radar_deterministic(self, sample_articles):
        """Verify radar computation is deterministic."""
        # Compute radar multiple times
        radar1 = compute_censorship_radar(sample_articles)
        radar2 = compute_censorship_radar(sample_articles)
        
        # Should be identical
        assert radar1 == radar2, "Censorship radar not deterministic"
        
        # Scale should be same
        assert radar1['scale_of_censorship'] == radar2['scale_of_censorship']
        
        # Severity should be same
        assert radar1['severity'] == radar2['severity']
    
    def test_topic_detection_stable(self, sample_articles):
        """Verify topic detection doesn't fluctuate."""
        radar1 = compute_censorship_radar(sample_articles)
        radar2 = compute_censorship_radar(sample_articles)
        
        # Union topics should be identical
        assert set(radar1['union_topics']) == set(radar2['union_topics']), \
            "Topic detection is not stable"


class TestEdgeCases:
    """Test consistency in edge cases."""
    
    def test_empty_articles_consistent(self):
        """Empty input should consistently return empty results."""
        result1 = analyze_articles_bias([])
        result2 = analyze_articles_bias([])
        
        assert result1 == result2
        assert result1['article_count'] == 0
    
    def test_single_article_consistent(self, sample_articles):
        """Single article analysis should be consistent."""
        single = [sample_articles[0]]
        
        result1 = analyze_articles_bias(single)
        result2 = analyze_articles_bias(single)
        
        assert result1 == result2
    
    def test_identical_articles_handled_consistently(self):
        """Duplicate articles should be handled consistently."""
        duplicate_articles = [
            {
                "title": "Same title",
                "description": "Same description",
                "source": "example.com",
                "url": "https://example.com/1"
            }
        ] * 3  # 3 identical articles
        
        result1 = analyze_articles_bias(duplicate_articles)
        result2 = analyze_articles_bias(duplicate_articles)
        
        assert result1 == result2
        assert result1['article_count'] == 3


class TestPerformanceConsistency:
    """Test that performance remains consistent."""
    
    def test_analysis_time_bounded(self, sample_articles):
        """Analysis should complete within reasonable time."""
        import time
        
        start = time.time()
        analyze_articles_bias(sample_articles)
        duration = time.time() - start
        
        # Should complete within 2 seconds for 5 articles (no LLM calls)
        assert duration < 2.0, f"Analysis too slow: {duration:.2f}s"
    
    def test_large_batch_scalability(self):
        """Test that analysis scales linearly."""
        import time
        
        # Create progressively larger batches
        base_article = {
            "title": "Test article",
            "description": "Test description",
            "source": "test.com",
            "url": "https://test.com/article"
        }
        
        times = []
        for count in [5, 10, 20]:
            articles = [base_article.copy() for _ in range(count)]
            
            start = time.time()
            analyze_articles_bias(articles)
            duration = time.time() - start
            times.append((count, duration))
        
        # Should scale roughly linearly (not exponentially)
        # 20 articles should take less than 5x the time of 5 articles
        ratio = times[2][1] / times[0][1]
        assert ratio < 5.0, f"Analysis not scaling linearly: {ratio}x slower"


class TestJSONSerializability:
    """Test that all outputs are JSON-serializable (important for APIs)."""
    
    def test_bias_results_serializable(self, sample_articles):
        """Bias analysis results should be JSON-serializable."""
        result = analyze_articles_bias(sample_articles)
        
        # Should not raise exception
        json_str = json.dumps(result)
        assert len(json_str) > 0
        
        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed['article_count'] == len(sample_articles)
    
    def test_radar_serializable(self, sample_articles):
        """Radar results should be JSON-serializable."""
        radar = compute_censorship_radar(sample_articles)
        
        json_str = json.dumps(radar)
        parsed = json.loads(json_str)
        
        assert 'scale_of_censorship' in parsed
        assert 'severity' in parsed


class TestRegressionPrevention:
    """Tests to prevent regression in known good behaviors."""
    
    def test_political_lean_calculation(self):
        """Test known political lean calculations."""
        # Strong left-leaning article
        left_article = {
            "title": "Climate crisis demands progressive action",
            "description": "Climate justice, wealth inequality, and systemic racism require immediate progressive policy reforms.",
            "source": "progressive-news.com",
            "url": "https://progressive-news.com/article"
        }
        
        profile = ArticleBiasProfile(left_article)
        result = profile.analyze()
        
        # Should detect left lean
        assert result['bias_scores']['political_lean'] < 0, \
            "Failed to detect left-leaning bias"
        
        # Strong right-leaning article
        right_article = {
            "title": "Free market solutions to border security",
            "description": "Traditional values, fiscal responsibility, and strong borders through deregulation and limited government.",
            "source": "conservative-news.com",
            "url": "https://conservative-news.com/article"
        }
        
        profile = ArticleBiasProfile(right_article)
        result = profile.analyze()
        
        # Should detect right lean
        assert result['bias_scores']['political_lean'] > 0, \
            "Failed to detect right-leaning bias"
    
    def test_credibility_tiers_stable(self):
        """Known credibility sources should maintain their tiers."""
        high_credibility = ["reuters.com", "apnews.com", "bbc.com"]
        low_credibility = ["rt.com", "tass.com"]
        
        for source in high_credibility:
            article = {"title": "Test", "description": "Test", "source": source, "url": f"https://{source}/test"}
            profile = ArticleBiasProfile(article)
            result = profile.analyze()
            
            assert result['classification']['credibility_tier'] in ['high', 'medium-high'], \
                f"{source} should have high credibility"
        
        for source in low_credibility:
            article = {"title": "Test", "description": "Test", "source": source, "url": f"https://{source}/test"}
            profile = ArticleBiasProfile(article)
            result = profile.analyze()
            
            assert result['classification']['credibility_tier'] == 'low', \
                f"{source} should have low credibility"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
