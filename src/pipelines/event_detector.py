"""Event detection and article grouping based on entity overlap and temporal clustering."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set, Tuple

from .embedding_cluster import ArticleRecord, extract_entities


@dataclass
class Event:
    """Represents a detected news event with grouped articles."""
    
    event_id: int
    primary_entities: Set[str]
    articles: List[ArticleRecord] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def article_count(self) -> int:
        return len(self.articles)
    
    @property
    def state_aligned_count(self) -> int:
        return sum(1 for a in self.articles if a.metadata.get("state_aligned", False))
    
    @property
    def independent_count(self) -> int:
        return self.article_count - self.state_aligned_count
    
    @property
    def coverage_balance(self) -> float:
        """Returns value between 0 (balanced) and 1 (imbalanced)."""
        if self.article_count == 0:
            return 0.0
        return abs(self.state_aligned_count - self.independent_count) / self.article_count
    
    def get_summary(self) -> Dict:
        """Get event summary statistics."""
        return {
            "event_id": self.event_id,
            "entities": sorted(self.primary_entities),
            "article_count": self.article_count,
            "state_aligned_count": self.state_aligned_count,
            "independent_count": self.independent_count,
            "coverage_balance": round(self.coverage_balance, 2),
            "sources": [a.source_id for a in self.articles],
        }


class EventDetector:
    """Detects events by clustering articles with similar entities and temporal proximity."""
    
    def __init__(
        self,
        entity_overlap_threshold: float = 0.3,
        time_window_hours: int = 72,
        min_entity_frequency: int = 2,
    ):
        """
        Initialize event detector.
        
        Args:
            entity_overlap_threshold: Minimum Jaccard similarity for entity overlap (0-1)
            time_window_hours: Maximum time difference for articles in same event
            min_entity_frequency: Minimum times an entity must appear to be significant
        """
        self.entity_overlap_threshold = entity_overlap_threshold
        self.time_window_hours = time_window_hours
        self.min_entity_frequency = min_entity_frequency
    
    def detect_events(self, articles: List[ArticleRecord]) -> List[Event]:
        """
        Detect events from a list of articles.
        
        Args:
            articles: List of articles with text and metadata
            
        Returns:
            List of detected events with grouped articles
        """
        if not articles:
            return []
        
        # Extract entities and timestamps from all articles
        article_data = self._prepare_article_data(articles)
        
        # Filter significant entities
        significant_entities = self._get_significant_entities(article_data)
        
        # Build similarity matrix based on entity overlap
        events: List[Event] = []
        assigned: Set[int] = set()
        
        for i, (article, entities, timestamp, tokens) in enumerate(article_data):
            if i in assigned:
                continue
            
            # Filter to significant entities only
            filtered_entities = entities & significant_entities
            if not filtered_entities:
                filtered_entities = set(entities)
            if not filtered_entities and not tokens:
                continue
            
            # Start new event cluster
            event_articles = [article]
            event_entities = filtered_entities.copy()
            event_start = timestamp
            event_end = timestamp
            assigned.add(i)
            
            # Find similar articles
            for j, (other_article, other_entities, other_timestamp, other_tokens) in enumerate(article_data):
                if j <= i or j in assigned:
                    continue
                
                # Check temporal proximity
                time_diff = abs((timestamp - other_timestamp).total_seconds() / 3600)
                if time_diff > self.time_window_hours:
                    continue
                
                # Check entity overlap
                filtered_other = other_entities & significant_entities
                if not filtered_other:
                    filtered_other = set(other_entities)
                overlap = self._jaccard_similarity(event_entities, filtered_other)
                token_similarity = self._jaccard_similarity(tokens, other_tokens)
                
                if max(overlap, token_similarity) >= self.entity_overlap_threshold:
                    event_articles.append(other_article)
                    event_entities.update(filtered_other)
                    event_start = min(event_start, other_timestamp)
                    event_end = max(event_end, other_timestamp)
                    assigned.add(j)
            
            # Create event if we have multiple articles or strong entity signal
            if len(event_articles) >= 2 or len(event_entities) >= 3:
                event = Event(
                    event_id=len(events),
                    primary_entities=event_entities,
                    articles=event_articles,
                    start_time=event_start,
                    end_time=event_end,
                )
                events.append(event)
        
        # Sort events by article count (most covered first)
        events.sort(key=lambda e: e.article_count, reverse=True)
        
        # Reassign event IDs after sorting
        for idx, event in enumerate(events):
            event.event_id = idx
        
        return events
    
    def _prepare_article_data(
        self, articles: List[ArticleRecord]
    ) -> List[Tuple[ArticleRecord, Set[str], datetime, Set[str]]]:
        """Extract entities and timestamps from articles."""
        article_data = []
        
        for article in articles:
            # Extract entities
            entities = set(extract_entities(article.text))
            tokens = self._token_set(article.text)
            
            # Parse timestamp from metadata or use current time
            timestamp = self._parse_timestamp(article.metadata.get("fetched_at"))
            
            article_data.append((article, entities, timestamp, tokens))
        
        return article_data
    
    def _get_significant_entities(
        self, article_data: List[Tuple[ArticleRecord, Set[str], datetime, Set[str]]]
    ) -> Set[str]:
        """Identify entities that appear frequently enough to be significant."""
        entity_counts: Counter = Counter()
        
        for _, entities, _, _ in article_data:
            entity_counts.update(entities)
        
        significant = {
            entity
            for entity, count in entity_counts.items()
            if count >= self.min_entity_frequency
        }
        
        return significant
    
    def _jaccard_similarity(self, set_a: Set[str], set_b: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set_a and not set_b:
            return 0.0
        
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        
        return intersection / union if union > 0 else 0.0
    
    def _parse_timestamp(self, timestamp_str: Any) -> datetime:
        """Parse timestamp from various formats."""
        if isinstance(timestamp_str, datetime):
            return timestamp_str
        
        if isinstance(timestamp_str, (int, float)):
            return datetime.fromtimestamp(timestamp_str)
        
        if isinstance(timestamp_str, str):
            # Try common formats
            formats = [
                "%Y%m%d%H%M%S",  # 20251115154732
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue
        
        # Default to current time if parsing fails
        return datetime.utcnow()

    def _token_set(self, text: str) -> Set[str]:
        tokens = set(re.findall(r"\w+", text.lower()))
        return {token for token in tokens if len(token) >= 4}


def group_articles_by_event(
    articles: List[ArticleRecord],
    entity_overlap_threshold: float = 0.3,
    time_window_hours: int = 72,
) -> List[Event]:
    """
    Convenience function to detect events from articles.
    
    Args:
        articles: List of articles to group
        entity_overlap_threshold: Minimum entity overlap for grouping
        time_window_hours: Maximum time difference for same event
        
    Returns:
        List of detected events
    """
    detector = EventDetector(
        entity_overlap_threshold=entity_overlap_threshold,
        time_window_hours=time_window_hours,
    )
    return detector.detect_events(articles)


def analyze_event_coverage(events: List[Event]) -> Dict:
    """
    Analyze coverage patterns across detected events.
    
    Args:
        events: List of detected events
        
    Returns:
        Summary statistics about event coverage
    """
    if not events:
        return {
            "total_events": 0,
            "total_articles": 0,
            "avg_articles_per_event": 0.0,
            "imbalanced_events": 0,
        }
    
    total_articles = sum(e.article_count for e in events)
    imbalanced = sum(1 for e in events if e.coverage_balance > 0.5)
    
    return {
        "total_events": len(events),
        "total_articles": total_articles,
        "avg_articles_per_event": round(total_articles / len(events), 1),
        "imbalanced_events": imbalanced,
        "imbalance_rate": round(imbalanced / len(events), 2) if events else 0.0,
        "top_events": [e.get_summary() for e in events[:5]],
    }
