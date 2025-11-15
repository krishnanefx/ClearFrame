from typing import List
from src.ingestion.fetcher import SourceFetcher
from src.pipelines.embedding_cluster import cluster_articles
from src.pipelines.narrative_comparator import compare_cluster
from src.utils.data_models import ArticleRecord

class NewsAgent:
    def __init__(self, config_path: str = 'config/censorship_sources.yaml'):
        self.fetcher = SourceFetcher(config_path)

    def compare_narratives(self, topic: str) -> List:
        """
        Main entry point that orchestrates the full pipeline for a given topic.
        """
        # 1. Ingestion
        fetch_results = self.fetcher.ingest_all_sources(topic)
        
        # Create ArticleRecords
        articles = []
        for result in fetch_results:
            with open(result.normalized_content_path, 'r') as f:
                text = f.read()
            
            # Simple topic filtering
            if topic.lower() in text.lower():
                articles.append(ArticleRecord(
                    source_id=result.source_name,
                    text=text,
                    metadata=result.metadata
                ))

        # 2. Clustering
        clusters = cluster_articles(articles)

        # 3. Scoring and Comparison
        narrative_comparisons = []
        for cluster in clusters:
            if not cluster.articles:
                continue
            comparison = compare_cluster(cluster)
            narrative_comparisons.append(comparison)
            
        return narrative_comparisons
