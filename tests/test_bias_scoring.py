import unittest
from src.utils.data_models import ArticleRecord
from src.pipelines.bias_scoring import score_bias

class TestBiasScoring(unittest.TestCase):

    def test_score_bias_balanced(self):
        articles = [
            ArticleRecord(source_id='s1', text='positive happy joy', metadata={'state_aligned': True}),
            ArticleRecord(source_id='i1', text='negative sad anger', metadata={'state_aligned': False}),
        ]
        bias_score = score_bias(articles)
        self.assertEqual(bias_score.coverage_delta, 0.0)
        self.assertTrue(bias_score.sentiment_delta > 0) # state positive, independent negative
        # This will depend on NER, so we can't be too specific
        self.assertGreaterEqual(bias_score.omission_ratio, 0.0)

    def test_score_bias_unbalanced(self):
        articles = [
            ArticleRecord(source_id='s1', text='positive happy joy', metadata={'state_aligned': True}),
            ArticleRecord(source_id='s2', text='positive happy joy', metadata={'state_aligned': True}),
            ArticleRecord(source_id='i1', text='negative sad anger', metadata={'state_aligned': False}),
        ]
        bias_score = score_bias(articles)
        self.assertAlmostEqual(bias_score.coverage_delta, 1/3)
        self.assertTrue(bias_score.sentiment_delta > 0)

    def test_no_articles(self):
        articles = []
        bias_score = score_bias(articles)
        self.assertEqual(bias_score.coverage_delta, 0.0)
        self.assertEqual(bias_score.sentiment_delta, 0.0)
        self.assertEqual(bias_score.omission_ratio, 0.0)

    def test_one_sided_articles(self):
        articles = [
            ArticleRecord(source_id='s1', text='positive happy joy', metadata={'state_aligned': True}),
            ArticleRecord(source_id='s2', text='positive happy joy', metadata={'state_aligned': True}),
        ]
        bias_score = score_bias(articles)
        self.assertEqual(bias_score.coverage_delta, 1.0)
        self.assertEqual(bias_score.sentiment_delta, 0.0) # No independent articles to compare against
        self.assertEqual(bias_score.omission_ratio, 0.0)

if __name__ == '__main__':
    unittest.main()
