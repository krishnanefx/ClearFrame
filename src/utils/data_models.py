from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class SourceConfigEntry:
    name: str
    url: str
    region: str
    state_aligned: bool

@dataclass
class FetchResult:
    source_name: str
    raw_content_path: str
    normalized_content_path: str
    metadata: dict

@dataclass
class NormalizedContent:
    clean_text: str
    detected_language: Optional[str]

@dataclass
class ArticleRecord:
    source_id: str
    text: str
    metadata: dict

@dataclass
class ClusterResult:
    cluster_id: str
    articles: List[ArticleRecord]

@dataclass
class BiasScore:
    coverage_delta: float
    sentiment_delta: float
    omission_ratio: float

@dataclass
class NarrativeComparison:
    cluster_id: str
    state_aligned_summary: str
    independent_summary: str
    bias_score: BiasScore
    metrics: dict = field(default_factory=dict)
