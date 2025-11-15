import unittest
import os
from unittest.mock import patch, MagicMock
from src.agents.news_agent import NewsAgent

class TestSystem(unittest.TestCase):

    @patch('src.ingestion.fetcher.SourceFetcher.ingest_all_sources')
    @patch('src.pipelines.embedding_cluster.cluster_articles')
    @patch('src.pipelines.narrative_comparator.compare_cluster')
    def test_compare_narratives_workflow(self, mock_compare_cluster, mock_cluster_articles, mock_ingest_all_sources):
        # Mock the ingestion results
        mock_fetch_result = MagicMock()
        mock_fetch_result.normalized_content_path = 'dummy_path.txt'
        mock_fetch_result.source_name = 'dummy_source'
        mock_fetch_result.metadata = {}
        mock_ingest_all_sources.return_value = [mock_fetch_result]

        # Mock the clustering results
        mock_cluster_result = MagicMock()
        mock_cluster_result.articles = [MagicMock()]
        mock_cluster_articles.return_value = [mock_cluster_result]

        # Mock the comparison results
        mock_narrative_comparison = MagicMock()
        mock_compare_cluster.return_value = mock_narrative_comparison

        # Create a dummy file for the agent to read
        with open('dummy_path.txt', 'w') as f:
            f.write('test topic')

        agent = NewsAgent()
        results = agent.compare_narratives(topic='test')

        mock_ingest_all_sources.assert_called_once()
        mock_cluster_articles.assert_called_once()
        mock_compare_cluster.assert_called_once()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], mock_narrative_comparison)

        # Clean up the dummy file
        os.remove('dummy_path.txt')

if __name__ == '__main__':
    unittest.main()