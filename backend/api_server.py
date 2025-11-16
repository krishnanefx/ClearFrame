#!/usr/bin/env python3
"""
Flask API Server for FactFlow UI
Connects basic_cli.py backend with factflow-ui frontend
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load environment variables from project root
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env", override=False)

# Ensure backend + project root are importable
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Import from backend engine
from .basic_cli import (
    run_valyu_search,
    analyze_articles_bias,
    get_chat_model,
    fetch_with_category_coverage,
    get_metrics,
    start_emissions_tracker,
    stop_emissions_tracker,
)
from src.utils.config_loader import Config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load configuration
config = Config()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "FactFlow API"}), 200


@app.route('/api/analyze', methods=['POST'])
def analyze_claim():
    """
    Main endpoint to analyze a claim/query
    
    Request body:
    {
        "query": "sudan war",
        "max_results": 9,
        "search_type": "web",
        "response_length": "large",
        "enable_advanced": false
    }
    
    Response:
    {
        "query": "sudan war",
        "article_count": 9,
        "bias_analysis": {...},
        "ingestion_summary": {...},
        "observability": {...}
    }
    """
    try:
        # Parse request
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' in request body"}), 400
        
        query = data.get('query')
        max_results = data.get('max_results', 9)
        search_type = data.get('search_type', 'web')
        response_length = data.get('response_length', 'large')
        enable_advanced = data.get('enable_advanced', False)
        
        logger.info(f"Received analysis request for query: {query}")
        
        # Start emissions tracking
        start_emissions_tracker()
        
        # Fetch articles with category coverage
        per_class_min = max(1, min(3, max_results // 2))
        total_cap = max(max_results, 9)
        
        logger.info(f"Fetching articles with coverage: total_cap={total_cap}, per_class_min={per_class_min}")
        covered_articles, ingestion_meta = fetch_with_category_coverage(
            query, 
            total_cap, 
            per_class_min, 
            response_length
        )
        
        if not covered_articles:
            return jsonify({
                "error": "No articles found",
                "query": query,
                "article_count": 0
            }), 404
        
        logger.info(f"Found {len(covered_articles)} articles")
        
        # Get LLM instance
        llm = get_chat_model()
        
        # Analyze bias for each article
        bias_results = analyze_articles_bias(covered_articles)
        
        # Optionally enhance with advanced analysis
        if enable_advanced:
            try:
                from .basic_cli import analyze_bias_advanced
                for i, article in enumerate(covered_articles[:3]):
                    advanced = analyze_bias_advanced(
                        article.get('body', article.get('snippet', '')),
                        llm
                    )
                    if 'articles' in bias_results and i < len(bias_results['articles']):
                        bias_results['articles'][i]['advanced_analysis'] = advanced
            except Exception as e:
                logger.warning(f"Advanced analysis failed: {e}")
        
        # Stop emissions tracking
        stop_emissions_tracker()
        metrics = get_metrics()
        
        # Build response
        result = {
            "query": query,
            "search_type": search_type,
            "article_count": len(covered_articles),
            "bias_analysis": bias_results,
            "ingestion_summary": ingestion_meta,
            "observability": {
                "emissions_kg": metrics.get("emissions_kg"),
                "total_latency_ms": metrics.get("total_latency_ms"),
                "llm_calls": metrics.get("llm_calls", 0),
                "api_calls": metrics.get("api_calls", 0),
            }
        }
        
        logger.info(f"Analysis complete: {len(covered_articles)} articles analyzed")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/search', methods=['POST'])
def search_articles():
    """
    Search endpoint for article discovery
    
    Request body:
    {
        "query": "climate change",
        "max_results": 10,
        "search_type": "web",
        "sources": ["bbc.com", "cnn.com"]  // optional
    }
    """
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' in request body"}), 400
        
        query = data.get('query')
        max_results = data.get('max_results', 10)
        search_type = data.get('search_type', 'web')
        sources = data.get('sources')
        
        logger.info(f"Search request: query={query}, max_results={max_results}")
        
        # Run search
        search_result = run_valyu_search(
            query=query,
            sources=sources,
            search_type=search_type,
            max_results=max_results,
            relevance_threshold=0.0,
            max_price=0.0,
            language=None,
            region=None,
            date_from=None,
            date_to=None,
            response_length="medium",
            fast_mode=False,
            included_sources=None,
            excluded_sources=None,
            category=None,
            country_code=None,
            is_tool_call=True
        )
        
        if not search_result:
            return jsonify({"error": "Search failed"}), 500
        
        articles = search_result.get("results", [])
        
        return jsonify({
            "query": query,
            "article_count": len(articles),
            "articles": articles,
            "cost": search_result.get("total_cost_dollars"),
        }), 200
        
    except Exception as e:
        logger.error(f"Error in search: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    port = int(os.getenv('API_PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting FactFlow API server on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
