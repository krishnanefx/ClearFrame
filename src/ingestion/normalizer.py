from typing import Optional
import warnings
from bs4 import BeautifulSoup, FeatureNotFound, XMLParsedAsHTMLWarning
from langdetect import detect, LangDetectException
from src.utils.data_models import NormalizedContent

class ContentNormalizer:
    def normalize(self, html_content: str) -> NormalizedContent:
        """
        Strips HTML tags, extracts clean text, and performs basic language detection.
        """
        clean_text = self._strip_html(html_content)
        detected_language = self._detect_language(clean_text)
        return NormalizedContent(clean_text=clean_text, detected_language=detected_language)

    def _strip_html(self, html_content: str) -> str:
        """
        Removes markup from the given content. Chooses an XML parser when the
        payload looks like RSS/Atom to avoid BeautifulSoup warnings.
        """
        parser = self._select_parser(html_content)
        soup = self._parse_with_fallback(html_content, parser)
        return soup.get_text()

    def _select_parser(self, html_content: str) -> str:
        stripped = html_content.lstrip()
        lower = stripped.lower()
        if lower.startswith("<?xml") or lower.startswith("<rss") or lower.startswith("<feed"):
            return "xml"
        return "html.parser"

    def _parse_with_fallback(self, html_content: str, parser: str) -> BeautifulSoup:
        try:
            return BeautifulSoup(html_content, parser)
        except FeatureNotFound:
            # XML parser not available (e.g., lxml missing). Fall back to the HTML
            # parser but silence BeautifulSoup's warning for this conversion.
            if parser == "xml":
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
                    return BeautifulSoup(html_content, "html.parser")
            return BeautifulSoup(html_content, "html.parser")

    def _detect_language(self, text: str) -> Optional[str]:
        """
        Detects the language of the given text.
        """
        try:
            return detect(text)
        except LangDetectException:
            return None
