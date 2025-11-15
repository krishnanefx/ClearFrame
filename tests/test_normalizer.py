import unittest
from src.ingestion.normalizer import ContentNormalizer

class TestContentNormalizer(unittest.TestCase):

    def setUp(self):
        self.normalizer = ContentNormalizer()

    def test_normalize_simple_html(self):
        html = "<html><body><h1>Title</h1><p>This is a paragraph.</p></body></html>"
        normalized_content = self.normalizer.normalize(html)
        self.assertEqual(normalized_content.clean_text, "TitleThis is a paragraph.")
        self.assertEqual(normalized_content.detected_language, "en")

    def test_normalize_language_detection_failure(self):
        html = "<p>12345</p>"
        normalized_content = self.normalizer.normalize(html)
        self.assertEqual(normalized_content.clean_text, "12345")
        self.assertIsNone(normalized_content.detected_language)

if __name__ == '__main__':
    unittest.main()
