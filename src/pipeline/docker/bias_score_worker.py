"""ECS worker for bias scoring with Valyu API."""

import os
import json
import logging
from typing import List, Dict, Any
import boto3
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the bias scoring worker."""
    # Get environment variables
    pipeline_bucket = os.getenv('PIPELINE_BUCKET')
    clusters_s3_key = os.getenv('CLUSTERS_S3_KEY')
    execution_id = os.getenv('EXECUTION_ID')
    valyu_api_key = os.getenv('VALYU_API_KEY')
    valyu_endpoint = os.getenv('VALYU_API_ENDPOINT', 'https://api.valyu.ai/v1')
    batch_size = int(os.getenv('BATCH_SIZE', '16'))
    max_workers = int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))
    
    logger.info(f"Starting bias scoring for execution {execution_id}")
    
    # Initialize S3 client
    s3 = boto3.client('s3')
    
    # Load clustered articles from S3
    logger.info(f"Loading articles from s3://{pipeline_bucket}/{clusters_s3_key}")
    response = s3.get_object(Bucket=pipeline_bucket, Key=clusters_s3_key)
    articles = json.loads(response['Body'].read().decode('utf-8'))
    
    logger.info(f"Loaded {len(articles)} articles")
    
    # Score articles in parallel
    logger.info("Scoring articles for bias...")
    
    scored_articles = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(score_article_bias, article, valyu_api_key, valyu_endpoint): article
            for article in articles
        }
        
        for i, future in enumerate(as_completed(futures)):
            try:
                scored_article = future.result()
                scored_articles.append(scored_article)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Scored {i + 1}/{len(articles)} articles")
                    
            except Exception as e:
                article = futures[future]
                logger.error(f"Failed to score article {article.get('id')}: {e}")
                # Add article with default scores
                article['bias_score'] = 0.5
                article['bias_explanation'] = "Scoring failed"
                article['bias_dimensions'] = {}
                scored_articles.append(article)
    
    logger.info(f"Scored {len(scored_articles)} articles")
    
    # Save results to S3
    output_key = f"pipeline/{execution_id}/bias-scores.json"
    logger.info(f"Saving results to s3://{pipeline_bucket}/{output_key}")
    
    s3.put_object(
        Bucket=pipeline_bucket,
        Key=output_key,
        Body=json.dumps(scored_articles),
        ContentType='application/json'
    )
    
    # Write output for Step Functions
    output = {
        'status': 'completed',
        's3_key': output_key,
        'article_count': len(scored_articles)
    }
    
    with open('/tmp/output.json', 'w') as f:
        json.dump(output, f)
    
    logger.info("Bias scoring completed successfully")


def score_article_bias(article: Dict[str, Any], 
                       api_key: str, 
                       endpoint: str) -> Dict[str, Any]:
    """
    Score a single article for bias using Valyu API.
    
    Args:
        article: Article to score
        api_key: Valyu API key
        endpoint: Valyu API endpoint
        
    Returns:
        Article with bias scores added
    """
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'text': article['content'],
        'title': article['title'],
        'source': article['source'],
        'source_tags': article.get('source_tags', {})
    }
    
    try:
        response = requests.post(
            f"{endpoint}/analyze/bias",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        bias_data = response.json()
        
        article['bias_score'] = bias_data.get('overall_score', 0.5)
        article['bias_explanation'] = bias_data.get('explanation', '')
        article['bias_dimensions'] = {
            'political': bias_data.get('political_bias', 0.5),
            'emotional': bias_data.get('emotional_bias', 0.5),
            'framing': bias_data.get('framing_bias', 0.5),
            'source_credibility': bias_data.get('source_credibility', 0.5)
        }
        article['bias_confidence'] = bias_data.get('confidence', 0.5)
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"API request failed for article {article.get('id')}: {e}")
        # Use fallback simple scoring
        article['bias_score'] = _simple_bias_score(article)
        article['bias_explanation'] = "Fallback scoring (API unavailable)"
        article['bias_dimensions'] = {}
        article['bias_confidence'] = 0.3
    
    return article


def _simple_bias_score(article: Dict[str, Any]) -> float:
    """
    Simple fallback bias scoring based on source tags and basic heuristics.
    
    Args:
        article: Article to score
        
    Returns:
        Bias score between 0 and 1
    """
    source_tags = article.get('source_tags', {})
    
    # Start with neutral score
    score = 0.5
    
    # Adjust based on source alignment
    if source_tags.get('state_aligned'):
        score += 0.2
    
    if source_tags.get('independent'):
        score -= 0.1
    
    # Keep score in valid range
    return max(0.0, min(1.0, score))


if __name__ == '__main__':
    main()
