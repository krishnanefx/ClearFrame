#!/usr/bin/env python3
"""
Smart cache warming - only warms missing entries
"""

import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:5001"

def warm_missing_cache():
    """Only warm cache entries that don't exist"""
    logger.info("Checking cache status...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/cache/status")
        if response.status_code != 200:
            logger.error(f"Failed to get cache status: {response.status_code}")
            return
        
        data = response.json()
        prompts = data.get("prompts", {})
        
        # Check for full analysis cache (not just grandma brief)
        missing = [prompt for prompt, info in prompts.items() if not info.get("cached")]
        
        if not missing:
            logger.info("✅ All demo prompts are fully cached!")
            logger.info("Demo will have instant (<100ms) response times")
            return
        
        logger.info(f"Found {len(missing)} prompts to cache")
        logger.info("This will take ~5-10 minutes total")
        logger.info("")
        
        for i, prompt in enumerate(missing, 1):
            logger.info(f"\n[{i}/{len(missing)}] Caching: {prompt}")
            
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
                    timeout=300
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ Cached successfully")
                else:
                    logger.error(f"❌ Failed: {response.status_code}")
            
            except Exception as e:
                logger.error(f"❌ Error: {e}")
        
        logger.info("\n✅ Smart cache warming complete!")
    
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    warm_missing_cache()
