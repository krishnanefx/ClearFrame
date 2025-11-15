#!/usr/bin/env python3
"""Test script for the ingestion layer."""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion.fetcher import SourceFetcher

logging.basicConfig(level=logging.INFO)

def test_ingestion():
    """Test the ingestion layer with a single source."""
    print("🧪 Testing Ingestion Layer")
    print("=" * 40)

    try:
        fetcher = SourceFetcher()
        print(f"✅ Loaded config with {len(fetcher.censorship_config.sources)} sources")

        # Test with BBC (real source)
        bbc_source = next((s for s in fetcher.censorship_config.sources if "BBC" in s.name), None)
        if bbc_source:
            source = bbc_source
        elif fetcher.censorship_config.sources:
            source = fetcher.censorship_config.sources[0]
        else:
            print("⚠️ No sources configured")
            return True

        print(f"📡 Testing fetch for: {source.name} ({source.url})")

        result = fetcher.fetch_source(source)
        print("✅ Fetch successful!")
        print(f"   Raw path: {result.raw_path}")
        print(f"   Cleaned path: {result.cleaned_path}")
        print(f"   Metadata: {result.metadata}")

    except Exception as e:
        print(f"❌ Ingestion test failed: {e}")
        return False

    return True

if __name__ == "__main__":
    success = test_ingestion()
    sys.exit(0 if success else 1)