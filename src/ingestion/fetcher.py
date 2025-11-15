import os
import time
import requests
import yaml
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.data_models import SourceConfigEntry, FetchResult
from src.utils.config import load_config
from src.ingestion.normalizer import ContentNormalizer
from src.resilience.circuit_breakers import SimpleCircuitBreaker, wrap_with_breaker
from src.tools.custom_tools import ValyuSearchTool

class SourceFetcher:
    def __init__(self, config_path: str = 'config/censorship_sources.yaml'):
        self.config = load_config(config_path)
        self.normalizer = ContentNormalizer()
        self.raw_dir = "data/cache_store/raw"
        self.clean_dir = "data/cache_store/clean"
        self._source_breakers: Dict[str, SimpleCircuitBreaker] = {}
        self.search_tool = ValyuSearchTool()
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.clean_dir, exist_ok=True)

    def ingest_all_sources(self, topic: str = None, fetch_fresh: bool = False) -> List[FetchResult]:
        if not topic:
            raise ValueError("Topic must be provided for ingestion.")
        
        print(f"--- Performing fresh fetch for topic: {topic} ---")
        return self._ingest_with_valyu(topic)

    def _ingest_with_valyu(self, topic: str) -> List[FetchResult]:
        """
        Private method to handle ingestion using Valyu search.
        """
        results = []
        for source_config in self.config['sources']:
            source = SourceConfigEntry(**source_config)
            print(f"Searching Valyu for '{topic}' from source: {source.name}")
            try:
                # Use Valyu search for each configured source
                search_results = self.search_tool.search(
                    query=topic,
                    site_filter=source.url,  # Assuming source URL can be a site filter
                    max_results=5  # Limit results per source
                )

                for item in search_results:
                    # The search result gives us a URL, now we fetch it
                    result = self._fetch_and_process_url(item['url'], source)
                    if result:
                        results.append(result)
            except Exception as e:
                print(f"Failed to search or process for {source.name}: {e}")
        return results

    def _fetch_and_process_url(self, url: str, source: SourceConfigEntry) -> Optional[FetchResult]:
        """
        Fetches content from a single URL and processes it.
        """
        try:
            breaker = self._source_breakers.setdefault(url, SimpleCircuitBreaker())
            response = wrap_with_breaker(
                breaker,
                requests.get,
                url,
                timeout=15
            )
            response.raise_for_status()

            timestamp = time.strftime("%Y%m%d%H%M%S")
            source_name_fs = source.name.lower().replace(" ", "_")

            # Create directories
            raw_path = os.path.join(self.raw_dir, source_name_fs)
            clean_path = os.path.join(self.clean_dir, source_name_fs)
            os.makedirs(raw_path, exist_ok=True)
            os.makedirs(clean_path, exist_ok=True)

            # Save raw content
            raw_file_path = os.path.join(raw_path, f"{timestamp}.html")
            with open(raw_file_path, "w", encoding='utf-8') as f:
                f.write(response.text)

            # Normalize and save clean content
            normalized_content = self.normalizer.normalize(response.text)
            clean_file_path = os.path.join(clean_path, f"{timestamp}.txt")
            with open(clean_file_path, "w", encoding='utf-8') as f:
                f.write(normalized_content.clean_text)

            return FetchResult(
                source_name=source.name,
                raw_content_path=raw_file_path,
                normalized_content_path=clean_file_path,
                metadata={
                    "timestamp": timestamp,
                    "source_url": url, # Use the specific article URL
                    "region": source.region,
                    "state_aligned": source.state_aligned
                }
            )
        except Exception as e:
            print(f"Error fetching URL {url}: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def fetch_source(self, source: SourceConfigEntry) -> FetchResult:
        print(f"Fetching {source.name} from {source.url}")
        breaker = self._source_breakers.setdefault(source.url, SimpleCircuitBreaker())
        response = wrap_with_breaker(
            breaker,
            requests.get,
            source.url,
            timeout=10
        )
        response.raise_for_status()

        timestamp = time.strftime("%Y%m%d%H%M%S")
        source_name_fs = source.name.lower().replace(" ", "_")

        raw_path = os.path.join(self.raw_dir, source_name_fs)
        os.makedirs(raw_path, exist_ok=True)
        raw_file_path = os.path.join(raw_path, f"{timestamp}.html")
        with open(raw_file_path, "w", encoding='utf-8') as f:
            f.write(response.text)

        normalized_content = self.normalizer.normalize(response.text)

        clean_path = os.path.join(self.clean_dir, source_name_fs)
        os.makedirs(clean_path, exist_ok=True)
        clean_file_path = os.path.join(clean_path, f"{timestamp}.txt")
        with open(clean_file_path, "w", encoding='utf-8') as f:
            f.write(normalized_content.clean_text)

        return FetchResult(
            source_name=source.name,
            raw_content_path=raw_file_path,
            normalized_content_path=clean_file_path,
            metadata={
                "timestamp": timestamp,
                "source_url": source.url,
                "region": source.region,
                "state_aligned": source.state_aligned
            }
        )

