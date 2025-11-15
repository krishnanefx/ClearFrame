import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

ROOT_DIR = Path(__file__).resolve().parents[1]
for path in (ROOT_DIR, ROOT_DIR / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from src.pipelines.embedding_cluster import ArticleRecord, ClusterResult
from src.pipelines.narrative_comparator import compare_cluster
from src.utils.data_models import BiasScore


class TestNarrativeComparator(unittest.TestCase):
    @patch('src.pipelines.narrative_comparator._generate_summary')
    def test_compare_cluster_outputs_summaries(self, mock_generate_summary):
        mock_generate_summary.side_effect = lambda articles: " ".join([a.text for a in articles])
        
        articles = [
            ArticleRecord(source_id="state", text="Government praises growth in Aurora", metadata={"state_aligned": True, "language": "en"}),
            ArticleRecord(source_id="independent", text="Activists cite corruption in Aurora", metadata={"state_aligned": False, "language": "en"}),
        ]
        
        cluster = ClusterResult(cluster_id="cluster_1", articles=articles)

        result = compare_cluster(cluster)
        
        self.assertEqual(result.cluster_id, "cluster_1")
        self.assertIn("Government praises growth in Aurora", result.state_aligned_summary)
        self.assertIn("Activists cite corruption in Aurora", result.independent_summary)
        self.assertTrue(isinstance(result.bias_score, BiasScore))


if __name__ == "__main__":
    unittest.main()
