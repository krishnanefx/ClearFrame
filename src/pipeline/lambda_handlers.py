"""AWS Lambda handlers for pipeline stages."""

import json
import logging
import os
import re
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import feedparser
from langdetect import detect

logger = logging.getLogger(__name__)


# ============================================================================
# Stage 1: FetchArticles - Lambda handler for scraping with retry/backoff
# ============================================================================

def fetch_articles_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for fetching articles from configured sources.
    Supports RSS, URL scraping, and API sources.
    
    Args:
        event: Contains 'sources' list and 'execution_id'
        context: Lambda context
        
    Returns:
        Dict with fetched articles and metadata
    """
    try:
        sources = event.get('sources', [])
        execution_id = event.get('execution_id')
        batch_size = event.get('batch_size', 50)
        
        logger.info(f"Fetching articles from {len(sources)} sources")
        
        all_articles = []
        fetch_stats = {
            'total_sources': len(sources),
            'successful_sources': 0,
            'failed_sources': 0,
            'total_articles': 0
        }
        
        for source in sources[:batch_size]:
            try:
                articles = _fetch_from_source(source)
                all_articles.extend(articles)
                fetch_stats['successful_sources'] += 1
                fetch_stats['total_articles'] += len(articles)
                
            except Exception as e:
                logger.error(f"Failed to fetch from {source.get('name')}: {e}")
                fetch_stats['failed_sources'] += 1
                # Send to SQS DLQ for retry
                _send_to_retry_queue(source, str(e))
        
        # Store articles in S3 or pass directly (depending on size)
        if len(all_articles) > 100:
            s3_key = _store_articles_to_s3(all_articles, execution_id)
            result = {
                'article_count': len(all_articles),
                's3_key': s3_key,
                'stats': fetch_stats,
                'execution_id': execution_id
            }
        else:
            result = {
                'article_count': len(all_articles),
                'articles': all_articles,
                'stats': fetch_stats,
                'execution_id': execution_id
            }
        
        logger.info(f"Fetched {len(all_articles)} articles successfully")
        return result
        
    except Exception as e:
        logger.error(f"FetchArticles handler failed: {e}")
        raise


def _fetch_from_source(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch articles from a single source."""
    source_type = source['type']
    
    if source_type == 'rss':
        return _fetch_from_rss(source)
    elif source_type == 'url':
        return _fetch_from_url(source)
    elif source_type == 'api':
        return _fetch_from_api(source)
    else:
        raise ValueError(f"Unknown source type: {source_type}")


def _fetch_from_rss(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch articles from RSS feed."""
    feed = feedparser.parse(source['url'])
    articles = []
    
    for entry in feed.entries:
        article = {
            'title': entry.get('title', ''),
            'url': entry.get('link', ''),
            'content': entry.get('summary', '') or entry.get('description', ''),
            'published_date': entry.get('published', ''),
            'source': source['name'],
            'source_tags': source.get('tags', {}),
            'raw_html': entry.get('content', [{}])[0].get('value', '') if entry.get('content') else ''
        }
        articles.append(article)
    
    return articles


def _fetch_from_url(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch articles from URL by scraping."""
    response = requests.get(source['url'], timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Generic article extraction (can be customized per source)
    articles = []
    article_elements = soup.find_all(['article', 'div'], class_=re.compile(r'article|post|story'))
    
    for element in article_elements[:20]:  # Limit to 20 per page
        title_elem = element.find(['h1', 'h2', 'h3'])
        link_elem = element.find('a')
        
        if title_elem and link_elem:
            article = {
                'title': title_elem.get_text(strip=True),
                'url': link_elem.get('href', ''),
                'content': element.get_text(strip=True)[:500],  # Preview
                'source': source['name'],
                'source_tags': source.get('tags', {}),
                'raw_html': str(element)
            }
            articles.append(article)
    
    return articles


def _fetch_from_api(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch articles from API."""
    headers = {}
    params = source.get('params', {})
    
    # Handle authentication
    if source.get('auth_type') == 'api_key':
        auth_key = source.get('auth_key', '')
        if 'Authorization' in source.get('auth_header', {}):
            headers['Authorization'] = f"Bearer {auth_key}"
        else:
            params['apiKey'] = auth_key
    
    response = requests.get(source['url'], params=params, headers=headers, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    articles = []
    
    # Handle different API response formats
    article_list = data.get('articles', data.get('results', data.get('items', [])))
    
    for item in article_list:
        article = {
            'title': item.get('title', ''),
            'url': item.get('url', item.get('link', '')),
            'content': item.get('description', item.get('content', '')),
            'published_date': item.get('publishedAt', item.get('date', '')),
            'source': source['name'],
            'source_tags': source.get('tags', {}),
            'author': item.get('author', '')
        }
        articles.append(article)
    
    return articles


def _send_to_retry_queue(source: Dict[str, Any], error: str) -> None:
    """Send failed source to SQS retry queue."""
    try:
        import boto3
        sqs = boto3.client('sqs')
        queue_url = os.getenv('RETRY_QUEUE_URL')
        
        if queue_url:
            message = {
                'source': source,
                'error': error,
                'timestamp': datetime.utcnow().isoformat(),
                'retry_count': source.get('retry_count', 0) + 1
            }
            
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'RetryCount': {
                        'StringValue': str(message['retry_count']),
                        'DataType': 'Number'
                    }
                }
            )
    except Exception as e:
        logger.error(f"Failed to send to retry queue: {e}")


def _store_articles_to_s3(articles: List[Dict[str, Any]], execution_id: str) -> str:
    """Store articles to S3 and return the key."""
    try:
        import boto3
        s3 = boto3.client('s3')
        bucket = os.getenv('PIPELINE_BUCKET')
        
        key = f"pipeline/{execution_id}/fetched-articles.json"
        
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(articles),
            ContentType='application/json'
        )
        
        return key
    except Exception as e:
        logger.error(f"Failed to store to S3: {e}")
        raise


# ============================================================================
# Stage 2: NormalizeContent - Language detection, HTML stripping
# ============================================================================

def normalize_content_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for normalizing article content.
    - Strips HTML
    - Detects language
    - Cleans and structures text
    
    Args:
        event: Contains 'articles' or 's3_key'
        context: Lambda context
        
    Returns:
        Dict with normalized articles
    """
    try:
        execution_id = event.get('execution_id')
        
        # Load articles
        if 'articles' in event:
            articles = event['articles']
        else:
            articles = _load_articles_from_s3(event['s3_key'])
        
        logger.info(f"Normalizing {len(articles)} articles")
        
        normalized_articles = []
        
        for article in articles:
            try:
                normalized = _normalize_article(article)
                normalized_articles.append(normalized)
            except Exception as e:
                logger.warning(f"Failed to normalize article {article.get('url')}: {e}")
        
        # Store normalized articles
        s3_key = _store_articles_to_s3(normalized_articles, execution_id)
        
        result = {
            'article_count': len(normalized_articles),
            's3_key': s3_key,
            'execution_id': execution_id
        }
        
        logger.info(f"Normalized {len(normalized_articles)} articles")
        return result
        
    except Exception as e:
        logger.error(f"NormalizeContent handler failed: {e}")
        raise


def _normalize_article(article: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single article."""
    # Strip HTML
    if article.get('raw_html'):
        soup = BeautifulSoup(article['raw_html'], 'html.parser')
        clean_text = soup.get_text(separator=' ', strip=True)
    else:
        clean_text = article.get('content', '')
    
    # Clean text
    clean_text = re.sub(r'\s+', ' ', clean_text)
    clean_text = clean_text.strip()
    
    # Detect language
    try:
        detected_language = detect(clean_text[:500]) if clean_text else 'unknown'
    except:
        detected_language = 'unknown'
    
    # Generate content hash for deduplication
    content_hash = hashlib.md5(clean_text.encode()).hexdigest()
    
    normalized = {
        'id': content_hash,
        'title': article.get('title', '').strip(),
        'url': article.get('url', ''),
        'content': clean_text,
        'summary': clean_text[:500] if len(clean_text) > 500 else clean_text,
        'published_date': article.get('published_date', ''),
        'source': article.get('source', ''),
        'source_tags': article.get('source_tags', {}),
        'detected_language': detected_language,
        'word_count': len(clean_text.split()),
        'content_hash': content_hash,
        'author': article.get('author', ''),
        'processed_at': datetime.utcnow().isoformat()
    }
    
    return normalized


def _load_articles_from_s3(s3_key: str) -> List[Dict[str, Any]]:
    """Load articles from S3."""
    try:
        import boto3
        s3 = boto3.client('s3')
        bucket = os.getenv('PIPELINE_BUCKET')
        
        response = s3.get_object(Bucket=bucket, Key=s3_key)
        content = response['Body'].read().decode('utf-8')
        
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to load from S3: {e}")
        raise


# ============================================================================
# Stage 3: EmbedAndCluster - Generate embeddings and cluster
# ============================================================================

def embed_and_cluster_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    ECS task handler for embedding and clustering articles.
    This runs on Fargate with GPU support for faster processing.
    
    Args:
        event: Contains articles data
        context: Lambda/ECS context
        
    Returns:
        Dict with clustered articles
    """
    # This would typically run in an ECS container
    # Placeholder for the actual implementation
    logger.info("EmbedAndCluster handler - runs in ECS Fargate")
    
    return {
        'status': 'completed',
        's3_key': f"pipeline/{event.get('execution_id')}/clusters.json",
        'cluster_count': 0
    }


# ============================================================================
# Stage 4: BiasScoreAndExplain - Calculate bias scores
# ============================================================================

def bias_score_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    ECS task handler for bias scoring using Valyu API.
    This runs on Fargate for longer processing times.
    
    Args:
        event: Contains clustered articles
        context: Lambda/ECS context
        
    Returns:
        Dict with bias-scored articles
    """
    # This would typically run in an ECS container
    # Placeholder for the actual implementation
    logger.info("BiasScoreAndExplain handler - runs in ECS Fargate")
    
    return {
        'status': 'completed',
        's3_key': f"pipeline/{event.get('execution_id')}/bias-scores.json"
    }


# ============================================================================
# Stage 5: StoreResults - Store processed articles
# ============================================================================

def store_results_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for storing final processed results.
    
    Args:
        event: Contains bias scores and metadata
        context: Lambda context
        
    Returns:
        Dict with storage status
    """
    try:
        execution_id = event.get('execution_id')
        bias_scores_s3_key = event.get('bias_scores_s3_key')
        
        logger.info(f"Storing results for execution {execution_id}")
        
        # Load bias-scored articles
        articles = _load_articles_from_s3(bias_scores_s3_key)
        
        # Store to database (DynamoDB, RDS, etc.)
        _store_to_database(articles, execution_id)
        
        # Store final results to S3
        final_s3_key = f"pipeline/{execution_id}/final-results.json"
        _store_articles_to_s3(articles, execution_id)
        
        result = {
            'status': 'success',
            'article_count': len(articles),
            's3_key': final_s3_key,
            'execution_id': execution_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Stored {len(articles)} articles successfully")
        return result
        
    except Exception as e:
        logger.error(f"StoreResults handler failed: {e}")
        raise


def _store_to_database(articles: List[Dict[str, Any]], execution_id: str) -> None:
    """Store articles to database."""
    try:
        import boto3
        dynamodb = boto3.resource('dynamodb')
        table_name = os.getenv('ARTICLES_TABLE')
        
        if table_name:
            table = dynamodb.Table(table_name)
            
            with table.batch_writer() as batch:
                for article in articles:
                    batch.put_item(Item=article)
                    
            logger.info(f"Stored {len(articles)} articles to DynamoDB")
    except Exception as e:
        logger.error(f"Failed to store to database: {e}")
        # Don't raise - S3 storage is primary
