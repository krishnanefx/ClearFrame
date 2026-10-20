#!/usr/bin/env python3
"""
Flask API Server for FactFlow UI
Connects basic_cli.py backend with factflow-ui frontend
"""

import os
import sys
import logging
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any
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
from backend.basic_cli import (
    run_valyu_search,
    analyze_articles_bias,
    get_chat_model,
    fetch_with_category_coverage,
    get_metrics,
    start_emissions_tracker,
    stop_emissions_tracker,
    analyze_bias_advanced,
    compare_article_narratives,
    detect_framing_techniques,
    analyze_power_dynamics,
    cluster_narratives,
    evidence_strength,
    detect_propaganda,
    # Observability wrappers
    start_trace,
    end_trace,
    add_span,
    end_span,
    SpanType,
    SpanStatus,
)
from src.analysis.bias_metrics import (
    generate_grandma_brief,
    build_dashboard_payload,
    compute_censorship_radar,
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

# Cache directories
CACHE_DIR = PROJECT_ROOT / "data" / "grandma_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

FULL_CACHE_DIR = PROJECT_ROOT / "data" / "analysis_cache"
FULL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "FactFlow API"}), 200


@app.route('/api/cache/status', methods=['GET'])
def cache_status():
    """Check which demo prompts are cached"""
    demo_prompts = [
        "News about LGBTQ developments",
        "News of the war in Sudan",
        "Taylor Swift current news",
        "News on Trump's tariffs",
    ]
    
    cache_info = {}
    for prompt in demo_prompts:
        cache_key = hashlib.md5(prompt.lower().strip().encode('utf-8')).hexdigest()
        grandma_cache_file = CACHE_DIR / f"{cache_key}.json"
        full_cache_file = FULL_CACHE_DIR / f"{cache_key}.json"
        cache_info[prompt] = {
            "cached": full_cache_file.exists(),
            "grandma_brief_cached": grandma_cache_file.exists(),
            "cache_key": cache_key
        }
    
    return jsonify({
        "cache_dir": str(CACHE_DIR),
        "full_cache_dir": str(FULL_CACHE_DIR),
        "prompts": cache_info
    }), 200


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
        
        # ⚡ FAST PATH: Check full response cache first
        cache_key = hashlib.md5(query.lower().strip().encode()).hexdigest()
        full_cache_file = FULL_CACHE_DIR / f"{cache_key}.json"
        
        if full_cache_file.exists():
            try:
                logger.info(f"⚡ CACHE HIT! Loading complete analysis from cache")
                cache_start = time.perf_counter()
                with open(full_cache_file, 'r', encoding='utf-8') as f:
                    cached_result = json.load(f)
                cache_end = time.perf_counter()
                cache_latency_ms = int((cache_end - cache_start) * 1000)
                
                # Update observability metrics with actual cache latency
                if cached_result.get("observability"):
                    cached_result["observability"]["total_latency_ms"] = cache_latency_ms
                    cached_result["observability"]["cached"] = True
                    
                logger.info(f"✅ Returned cached result in {cache_latency_ms}ms (0 API calls, 0 emissions)")
                return jsonify(cached_result), 200
            except Exception as e:
                logger.warning(f"Cache read failed: {e}, running fresh analysis...")
        
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
                logger.info("Running advanced LLM analysis on top articles...")
                for i, article in enumerate(covered_articles[:5]):
                    advanced = analyze_bias_advanced(article, llm)
                    framing = detect_framing_techniques(article, llm)
                    power = analyze_power_dynamics(article)
                    
                    if 'articles' in bias_results and i < len(bias_results['articles']):
                        bias_results['articles'][i]['advanced_analysis'] = {
                            **advanced,
                            'framing_techniques': framing,
                            'power_dynamics': power
                        }
                
                # Add narrative comparison
                narrative_comparison = compare_article_narratives(covered_articles[:10], llm)
                bias_results['narrative_comparison'] = narrative_comparison
                
            except Exception as e:
                logger.warning(f"Advanced analysis failed: {e}")
        
        # Generate narrative clusters
        try:
            titles_and_descriptions = [
                {"title": a.get("title", ""), "description": a.get("description", "")}
                for a in covered_articles
            ]
            narrative_clusters = cluster_narratives.invoke({
                "titles_and_descriptions": titles_and_descriptions,
                "num_clusters": 3
            })
            bias_results['narrative_clusters'] = narrative_clusters
        except Exception as e:
            logger.warning(f"Narrative clustering failed: {e}")
        
        # Add propaganda detection
        propaganda_summary = []
        for article in covered_articles[:10]:
            body_text = article.get('body', article.get('description', ''))
            if body_text:
                try:
                    propaganda_result = detect_propaganda.invoke({"text": body_text})
                    if propaganda_result.get('count', 0) > 0:
                        propaganda_summary.append({
                            'title': article.get('title', 'Untitled'),
                            'source': article.get('source', 'Unknown'),
                            'techniques': propaganda_result
                        })
                except Exception:
                    pass
        
        if propaganda_summary:
            bias_results['propaganda_summary'] = propaganda_summary
        
        # Generate dashboard payload (includes censorship radar, framing, etc.)
        try:
            dashboard_payload = build_dashboard_payload(covered_articles, query)
            bias_results['dashboard_metrics'] = {
                'scale_of_censorship': dashboard_payload.get('scale_of_censorship', 0),
                'severity': dashboard_payload.get('severity', 'low'),
                'union_topics': dashboard_payload.get('union_topics', []),
                'source_angle_cards': dashboard_payload.get('source_angle_cards', []),
                'coverage_matrix_percent': dashboard_payload.get('coverage_matrix_percent', []),
                'omissions_diff': dashboard_payload.get('omissions_diff', {}),
            }
        except Exception as e:
            logger.warning(f"Dashboard payload generation failed: {e}")
        
        # Stop emissions tracking
        stop_emissions_tracker()
        metrics = get_metrics()
        
        # Calculate total latency from all metrics
        total_latency_ms = 0
        if metrics.get("by_name"):
            for name, stats in metrics["by_name"].items():
                total_latency_ms += stats.get("avg_ms", 0) * stats.get("count", 0)
        
        # Generate grandma brief (neutral, simple summary using LLM)
        # Use cache to avoid redundant LLM calls for the same query
        cache_key = hashlib.md5(query.lower().strip().encode()).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        if cache_file.exists():
            # Load from cache
            logger.info(f"Loading grandma brief from cache for query: {query}")
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    grandma_brief = cached_data.get('brief', '')
                    logger.info(f"✅ Cache hit! Saved LLM call.")
            except Exception as e:
                logger.warning(f"Cache read failed: {e}, regenerating...")
                grandma_brief = generate_grandma_brief(covered_articles, query, llm)
                # Save to cache
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump({'query': query, 'brief': grandma_brief}, f, indent=2)
                except Exception as cache_err:
                    logger.warning(f"Failed to cache grandma brief: {cache_err}")
        else:
            # Generate new brief and cache it
            logger.info(f"Generating new grandma brief for query: {query}")
            grandma_brief = generate_grandma_brief(covered_articles, query, llm)
            # Save to cache
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({'query': query, 'brief': grandma_brief}, f, indent=2)
                logger.info(f"✅ Cached grandma brief for future use")
            except Exception as cache_err:
                logger.warning(f"Failed to cache grandma brief: {cache_err}")
        
        # Build response
        result = {
            "query": query,
            "search_type": search_type,
            "article_count": len(covered_articles),
            "bias_analysis": bias_results,
            "grandma_brief": grandma_brief,
            "ingestion_summary": ingestion_meta,
            "observability": {
                "emissions_kg": metrics.get("emissions_kg") or 0,
                "total_latency_ms": int(total_latency_ms),
                "llm_calls": metrics.get("llm_calls", 0),
                "api_calls": metrics.get("api_requests", 0),  # Changed from api_calls to api_requests
                "total_calls": metrics.get("calls", 0),
                # Bubble up derived costs/tokens if available
                "cost_usd": ingestion_meta.get("total_cost_usd") if isinstance(ingestion_meta, dict) else None,
                "token_usage": ingestion_meta.get("token_usage") if isinstance(ingestion_meta, dict) else None,
            }
        }
        
        # 💾 Cache the complete response for instant future lookups
        try:
            with open(full_cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            logger.info(f"💾 Cached complete analysis for instant future access")
        except Exception as cache_err:
            logger.warning(f"Failed to cache full response: {cache_err}")
        
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
