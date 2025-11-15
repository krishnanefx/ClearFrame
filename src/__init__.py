"""
Project-wide initialization utilities.

Currently suppresses noisy third-party warnings that clutter CLI output on
systems using LibreSSL or parsing XML feeds via BeautifulSoup.
"""

from __future__ import annotations

import warnings

try:
    from bs4 import XMLParsedAsHTMLWarning
except Exception:  # pragma: no cover
    XMLParsedAsHTMLWarning = None  # type: ignore

warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL 1.1.1+",
)

if XMLParsedAsHTMLWarning:
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
