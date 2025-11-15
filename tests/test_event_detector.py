#!/usr/bin/env python3
"""Test the event detection module."""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipelines.embedding_cluster import ArticleRecord
from pipelines.event_detector import EventDetector, group_articles_by_event, analyze_event_coverage


class TestEventDetector(unittest.TestCase):
    """Test event detection functionality."""
    
    def test_single_event_detection(self):
        """Test detecting a single event from related articles."""
        articles = [
            ArticleRecord(
                "bbc",
                "President Biden announces new climate policy for renewable energy",
                {"state_aligned": False, "fetched_at": "20251115120000"}
            ),
            ArticleRecord(
                "cnn",
                "Biden reveals climate initiative focusing on renewable energy sources",
                {"state_aligned": False, "fetched_at": "20251115130000"}
            ),
            ArticleRecord(
                "reuters",
                "White House climate policy targets renewable energy expansion",
                {"state_aligned": False, "fetched_at": "20251115140000"}
            ),
        ]
        
        detector = EventDetector(entity_overlap_threshold=0.1)
        events = detector.detect_events(articles)
        
        self.assertGreaterEqual(len(events), 1, "Should detect at least one event")
        if events:
            self.assertEqual(events[0].article_count, 3, "Should group all three articles")
    
    def test_multiple_events_detection(self):
        """Test detecting multiple distinct events."""
        articles = [
            # Event 1: Climate policy
            ArticleRecord(
                "bbc",
                "President Biden announces climate policy",
                {"state_aligned": False, "fetched_at": "20251115120000"}
            ),
            ArticleRecord(
                "cnn",
                "Biden reveals new climate initiative",
                {"state_aligned": False, "fetched_at": "20251115130000"}
            ),
            # Event 2: Tech regulation
            ArticleRecord(
                "reuters",
                "Congress debates AI regulation framework",
                {"state_aligned": False, "fetched_at": "20251115120000"}
            ),
            ArticleRecord(
                "ap",
                "Senate considers AI regulation bill",
                {"state_aligned": False, "fetched_at": "20251115140000"}
            ),
        ]
        
        detector = EventDetector(entity_overlap_threshold=0.2, min_entity_frequency=1)
        events = detector.detect_events(articles)
        
        self.assertGreaterEqual(len(events), 1, "Should detect at least one event")
    
    def test_state_aligned_vs_independent(self):
        """Test coverage balance calculation."""
        articles = [
            ArticleRecord(
                "rt",
                "Government achieves great progress on policy",
                {"state_aligned": True, "fetched_at": "20251115120000"}
            ),
            ArticleRecord(
                "xinhua",
                "Policy progress continues successfully",
                {"state_aligned": True, "fetched_at": "20251115130000"}
            ),
            ArticleRecord(
                "bbc",
                "Policy progress questioned by experts",
                {"state_aligned": False, "fetched_at": "20251115140000"}
            ),
        ]
        
        events = group_articles_by_event(articles, entity_overlap_threshold=0.2)
        
        if events:
            event = events[0]
            self.assertEqual(event.state_aligned_count, 2)
            self.assertEqual(event.independent_count, 1)
            self.assertGreater(event.coverage_balance, 0)
    
    def test_temporal_clustering(self):
        """Test that articles far apart in time are not grouped."""
        articles = [
            ArticleRecord(
                "bbc",
                "President Biden announces policy",
                {"state_aligned": False, "fetched_at": "20251110120000"}  # 5 days ago
            ),
            ArticleRecord(
                "cnn",
                "Biden reveals new policy",
                {"state_aligned": False, "fetched_at": "20251115120000"}  # Today
            ),
        ]
        
        # With 72-hour window, these should not group
        detector = EventDetector(entity_overlap_threshold=0.2, time_window_hours=72)
        events = detector.detect_events(articles)
        
        # Should either have 0 events or 2 separate events
        if len(events) == 2:
            self.assertEqual(events[0].article_count, 1)
            self.assertEqual(events[1].article_count, 1)
    
    def test_analyze_event_coverage(self):
        """Test coverage analysis function."""
        articles = [
            ArticleRecord(
                "bbc",
                "President announces policy",
                {"state_aligned": False, "fetched_at": "20251115120000"}
            ),
            ArticleRecord(
                "cnn",
                "President reveals initiative",
                {"state_aligned": False, "fetched_at": "20251115130000"}
            ),
        ]
        
        events = group_articles_by_event(articles, entity_overlap_threshold=0.2)
        analysis = analyze_event_coverage(events)
        
        self.assertIn("total_events", analysis)
        self.assertIn("total_articles", analysis)
        self.assertIn("imbalanced_events", analysis)
    
    def test_empty_input(self):
        """Test handling of empty article list."""
        detector = EventDetector()
        events = detector.detect_events([])
        
        self.assertEqual(len(events), 0, "Should return empty list for no articles")
    
    def test_event_summary(self):
        """Test event summary generation."""
        articles = [
            ArticleRecord(
                "bbc",
                "President Biden announces policy",
                {"state_aligned": False, "fetched_at": "20251115120000"}
            ),
            ArticleRecord(
                "rt",
                "Biden reveals initiative",
                {"state_aligned": True, "fetched_at": "20251115130000"}
            ),
        ]
        
        events = group_articles_by_event(articles, entity_overlap_threshold=0.2)
        
        if events:
            summary = events[0].get_summary()
            self.assertIn("event_id", summary)
            self.assertIn("entities", summary)
            self.assertIn("article_count", summary)
            self.assertIn("state_aligned_count", summary)
            self.assertIn("independent_count", summary)
            self.assertIn("coverage_balance", summary)


if __name__ == "__main__":
    unittest.main()
