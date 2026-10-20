#!/usr/bin/env python3
"""
Cache warming script for demo prompts
Pre-analyzes common queries to ensure fast demo performance
"""

import requests
import time
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Demo prompts that should be pre-cached
DEMO_PROMPTS = [
    "News about LGBTQ developments",
    "News of the war in Sudan",
    "Taylor Swift current news",
    "News on Trump's tariffs",
]

API_BASE_URL = "http://localhost:5001"

def warm_cache():
    """Pre-fetch and cache analysis for demo prompts"""
    logger.info("Starting cache warming process...")
    
    for i, prompt in enumerate(DEMO_PROMPTS, 1):
        logger.info(f"\n[{i}/{len(DEMO_PROMPTS)}] Processing: {prompt}")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/analyze",
                json={
                    "query": prompt,
                    "max_results": 9,
                    "search_type": "web",
                    "response_length": "large",
                    "enable_advanced": False
                },
                timeout=300  # 5 minute timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                article_count = data.get("article_count", 0)
                logger.info(f"✅ Successfully cached: {article_count} articles analyzed")
            else:
                logger.error(f"❌ Failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"❌ Error processing '{prompt}': {e}")
        
        # Small delay between requests
        if i < len(DEMO_PROMPTS):
            logger.info("Waiting 2 seconds before next query...")
            time.sleep(2)
    
    logger.info("\n✅ Cache warming complete!")

if __name__ == "__main__":
    warm_cache()
