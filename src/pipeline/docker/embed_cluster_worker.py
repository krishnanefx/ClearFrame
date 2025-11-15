"""ECS worker for embedding and clustering articles."""

import os
import json
import logging
from typing import List, Dict, Any
import boto3
from sentence_transformers import SentenceTransformer
import hdbscan
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the embedding and clustering worker."""
    # Get environment variables
    pipeline_bucket = os.getenv('PIPELINE_BUCKET')
    articles_s3_key = os.getenv('ARTICLES_S3_KEY')
    execution_id = os.getenv('EXECUTION_ID')
    model_name = os.getenv('MODEL_NAME', 'sentence-transformers/all-mpnet-base-v2')
    batch_size = int(os.getenv('BATCH_SIZE', '32'))
    
    logger.info(f"Starting embedding and clustering for execution {execution_id}")
    
    # Initialize S3 client
    s3 = boto3.client('s3')
    
    # Load articles from S3
    logger.info(f"Loading articles from s3://{pipeline_bucket}/{articles_s3_key}")
    response = s3.get_object(Bucket=pipeline_bucket, Key=articles_s3_key)
    articles = json.loads(response['Body'].read().decode('utf-8'))
    
    logger.info(f"Loaded {len(articles)} articles")
    
    # Generate embeddings
    logger.info(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    
    texts = [f"{article['title']} {article['summary']}" for article in articles]
    
    logger.info("Generating embeddings...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    logger.info(f"Generated embeddings with shape: {embeddings.shape}")
    
    # Cluster articles
    logger.info("Clustering articles...")
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=5,
        min_samples=3,
        metric='cosine'
    )
    
    cluster_labels = clusterer.fit_predict(embeddings)
    
    # Count clusters
    unique_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
    logger.info(f"Found {unique_clusters} clusters")
    
    # Add cluster info to articles
    for i, article in enumerate(articles):
        article['embedding'] = embeddings[i].tolist()
        article['cluster_id'] = int(cluster_labels[i])
    
    # Save results to S3
    output_key = f"pipeline/{execution_id}/clusters.json"
    logger.info(f"Saving results to s3://{pipeline_bucket}/{output_key}")
    
    s3.put_object(
        Bucket=pipeline_bucket,
        Key=output_key,
        Body=json.dumps(articles),
        ContentType='application/json'
    )
    
    # Write output for Step Functions
    output = {
        'status': 'completed',
        's3_key': output_key,
        'cluster_count': unique_clusters,
        'article_count': len(articles)
    }
    
    # Write to file that Step Functions can read
    with open('/tmp/output.json', 'w') as f:
        json.dump(output, f)
    
    logger.info("Embedding and clustering completed successfully")


if __name__ == '__main__':
    main()
