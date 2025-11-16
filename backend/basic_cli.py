#!/usr/bin/env python3
"""
Enhanced CLI: Valyu Search → LangChain → HolisticAI

Advanced features from LangChain tutorials:
- Custom tools for bias detection, source credibility
- Structured output with Pydantic schemas
- Conversation memory for multi-turn analysis
- LangSmith tracing (optional)
- Streaming responses

Usage examples:
  # Basic pipeline
  python -m backend.basic_cli --query "AI regulation" --mode pipeline
  
  # Agent with custom tools
  python -m backend.basic_cli --query "climate change" --mode agent --tools bias,credibility --trace
  
  # Structured JSON output
  python -m backend.basic_cli --query "quantum computing" --mode structured --output-json
  
  # Multi-turn conversation
  python -m backend.basic_cli --query "AI ethics" --mode conversation
  
  # With LangSmith tracing
  LANGCHAIN_TRACING_V2=true python -m backend.basic_cli --query "tech news" --mode agent
"""

import os
import sys
import json
import argparse
import re
import requests
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import logging

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load environment variables explicitly
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env", override=False)

# Ensure repo root is on the path for src imports when running from backend/
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

# Imports
# Robust import for HolisticAI chat model helper
try:
    from tutorials.holistic_ai_bedrock import get_chat_model  # preferred path
except Exception:
    try:
        from examples.holistic_ai_bedrock import get_chat_model  # fallback path
    except Exception:
        # Load directly from file as last resort
        import importlib.util
        _candidates = [
            BACKEND_DIR / "tutorials" / "holistic_ai_bedrock.py",
            BACKEND_DIR / "examples" / "holistic_ai_bedrock.py",
            PROJECT_ROOT / "tutorials" / "holistic_ai_bedrock.py",
            PROJECT_ROOT / "examples" / "holistic_ai_bedrock.py",
        ]
        _loaded = False
        for _path in _candidates:
            if _path.exists():
                spec = importlib.util.spec_from_file_location("holistic_ai_bedrock", _path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules["holistic_ai_bedrock"] = mod
                    spec.loader.exec_module(mod)
                    get_chat_model = getattr(mod, "get_chat_model")
                    _loaded = True
                    break
        if not _loaded:
            raise ModuleNotFoundError("Could not locate holistic_ai_bedrock.get_chat_model in tutorials/ or examples/")
from langchain_valyu import ValyuSearchTool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.checkpoint.memory import MemorySaver

# Import new utilities
from src.utils.config_loader import Config
from src.utils.retry_handler import retry_with_backoff, RateLimitError, APIError
from src.observability.instrumentation import instrument, start_emissions_tracker, stop_emissions_tracker, get_metrics, reset_metrics, track_api_request, track_llm_call
from src.analysis.bias_metrics import (
    compute_censorship_radar,
    generate_grandma_brief,
    generate_source_angle_cards,
    compute_framing_comparison,
    build_dashboard_payload,
    classify_source,
    build_unified_deterministic_payload,
    analyze_articles_bias,
    ArticleBiasProfile,
)
from src.analysis.advanced_bias_detector import (
    analyze_bias_advanced,
    compare_article_narratives,
    detect_framing_techniques,
    analyze_power_dynamics,
)

# Optional imports with graceful fallback
try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def mask(s: Optional[str], keep: int = 4) -> str:
    if not s:
        return ""
    return ("*" * max(0, len(s) - keep)) + s[-keep:]


# ============================================================================
# Pydantic Schemas for Structured Output
# ============================================================================

class ArticleBiasDetail(BaseModel):
    """Detailed bias analysis for a single article."""
    url: str
    title: str
    source: str
    bias_scores: Dict[str, float] = Field(description="Multiple bias dimension scores")
    classification: Dict[str, str] = Field(description="Bias category, credibility tier, source type")
    detected_features: Dict[str, List[str]] = Field(description="Detected bias indicators")
    advanced_analysis: Optional[Dict[str, Any]] = Field(description="LLM-based advanced analysis", default=None)


class BiasAnalysis(BaseModel):
    """Structured bias analysis output with per-article details."""
    article_count: int = Field(description="Number of articles analyzed")
    articles: List[ArticleBiasDetail] = Field(description="Per-article bias analysis")
    aggregate_stats: Dict[str, Any] = Field(description="Aggregate statistics across articles")
    narrative_comparison: Optional[Dict[str, Any]] = Field(description="Cross-article narrative analysis", default=None)
    overall_assessment: str = Field(description="High-level summary of bias landscape")
    recommendations: List[str] = Field(description="3-5 recommendations for balanced info")
    cited_urls: List[str] = Field(description="URLs referenced in analysis")


# Legacy model for backwards compatibility
class LegacyBiasAnalysis(BaseModel):
    """Legacy structured bias analysis output."""
    overall_bias_score: float = Field(description="Overall bias score from -1 (left) to 1 (right), 0 is neutral")
    sentiment: str = Field(description="Overall sentiment: positive, negative, or neutral")
    key_themes: List[str] = Field(description="List of 3-5 key themes identified")
    bias_indicators: List[str] = Field(description="Specific bias indicators found")
    source_diversity: str = Field(description="Assessment of source diversity")
    missing_perspectives: List[str] = Field(description="Perspectives not covered or underrepresented", default=[])
    conflict_coverage_balance: Optional[str] = Field(description="For conflict news: balanced/one-sided/unclear", default=None)
    factual_accuracy_concerns: List[str] = Field(description="Potential factual issues or unverified claims", default=[])
    recommendations: List[str] = Field(description="3-5 recommendations for balanced info")
    cited_urls: List[str] = Field(description="URLs referenced in analysis")


class ArticleSummary(BaseModel):
    """Summary of a single article."""
    title: str
    source: str
    url: str
    sentiment: str
    key_points: List[str]
    bias_score: float


class NewsAnalysisReport(BaseModel):
    """Complete structured report with per-article bias analysis."""
    query: str
    num_articles: int
    bias_analysis: BiasAnalysis
    top_articles: List[ArticleBiasDetail] = Field(description="Top articles by relevance", default=[])
    ingestion_summary: Optional[Dict[str, Any]] = Field(description="Metadata about article ingestion", default=None)


# ============================================================================
# Custom Tools (Tutorial 2 Pattern)
# ============================================================================
@tool
def calculate_bias_score(text: str, source: str) -> float:
    """Calculate a bias score for an article using LLM analysis.
    
    Args:
        text: Article text to analyze
        source: Source domain (e.g., 'bbc.com', 'foxnews.com')
        
    Returns:
        Bias score from -50 (left-leaning) to 50 (right-leaning), 0 is neutral
    """
    try:
        # Use a fast LLM model for bias analysis
        llm = get_chat_model(model_name=FAST_LLM_MODEL, temperature=0.0, max_tokens=150)
        
        system_prompt = (
            "You are an expert political bias analyst. Analyze the given text and return ONLY a single number "
            "representing the political bias score from -50 to 50, where:\n"
            "- -50 to -30: Strong left-leaning bias\n"
            "- -29 to -10: Moderate left-leaning bias\n"
            "- -9 to 9: Neutral or balanced\n"
            "- 10 to 29: Moderate right-leaning bias\n"
            "- 30 to 50: Strong right-leaning bias\n\n"
            "Consider factors like: framing, language choice, source selection, emphasis on certain viewpoints, "
            "loaded language, and omission of perspectives. Return ONLY the numeric score, nothing else."
        )
        
        user_prompt = f"Source: {source}\n\nText to analyze:\n{text[:2000]}"  # Limit text to 2000 chars
        
        track_llm_call()  # Track emissions
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        content = getattr(response, "content", str(response)).strip()
        
        # Extract numeric score from response
        import re
        match = re.search(r'-?\d+(?:\.\d+)?', content)
        if match:
            score = float(match.group())
            # Clamp to -50 to 50 range
            score = max(-50.0, min(50.0, score))
            return round(score, 2)
        else:
            logger.warning(f"Could not extract bias score from LLM response: {content}")
            return 0.0
            
    except Exception as e:
        logger.warning(f"LLM bias analysis failed: {e}. Falling back to keyword heuristic.")
        # Fallback to simple keyword-based heuristic
        left_keywords = ['progressive', 'liberal', 'reform', 'diversity', 'climate action']
        right_keywords = ['conservative', 'traditional', 'free market', 'deregulation']
        
        text_lower = text.lower()
        left_count = sum(1 for kw in left_keywords if kw in text_lower)
        right_count = sum(1 for kw in right_keywords if kw in text_lower)
        
        total = left_count + right_count
        if total == 0:
            return 0.0
        
        score = ((right_count - left_count) / total) * 50
        return round(score, 2)


@tool
def check_source_credibility(source: str) -> Dict[str, Any]:
    """Check credibility of a news source.
    
    Args:
        source: Source domain (e.g., 'bbc.com', 'cnn.com')
        
    Returns:
        Dict with credibility_score (0-100) and category
    """
    # Simplified credibility database (in production, use Media Bias/Fact Check API)
    credibility_db = {
        'bbc.com': {'score': 95, 'category': 'High', 'known_for': 'International coverage'},
        'reuters.com': {'score': 95, 'category': 'High', 'known_for': 'Fact-based reporting'},
        'apnews.com': {'score': 95, 'category': 'High', 'known_for': 'Breaking news'},
        'aljazeera.com': {'score': 85, 'category': 'High', 'known_for': 'Middle East/Africa coverage'},
        'cnn.com': {'score': 75, 'category': 'Medium-High', 'known_for': 'US-centric'},
        'foxnews.com': {'score': 65, 'category': 'Medium', 'known_for': 'Conservative lean'},
        'theguardian.com': {'score': 80, 'category': 'High', 'known_for': 'Investigative journalism'},
        'nytimes.com': {'score': 90, 'category': 'High', 'known_for': 'In-depth analysis'},
        'washingtonpost.com': {'score': 88, 'category': 'High', 'known_for': 'Political coverage'},
        'france24.com': {'score': 85, 'category': 'High', 'known_for': 'French perspective'},
    }
    
    domain = source.replace('www.', '').split('/')[0]
    return credibility_db.get(domain, {'score': 50, 'category': 'Unknown', 'known_for': 'Unknown source'})


@tool
def detect_conflict_coverage_gaps(articles_summary: str) -> Dict[str, Any]:
    """Analyze conflict/war coverage for potential gaps or one-sided reporting.
    
    Args:
        articles_summary: Summary text of articles about a conflict
        
    Returns:
        Dict with coverage_balance, missing_perspectives, and recommendations
    """
    # Keywords indicating different perspectives in conflict coverage
    keywords = {
        'civilian_impact': ['civilian', 'humanitarian', 'refugee', 'casualties', 'displaced'],
        'government_narrative': ['official', 'government', 'military', 'defense'],
        'opposition_voice': ['rebel', 'opposition', 'activist', 'protest'],
        'international_response': ['UN', 'sanctions', 'peacekeeping', 'diplomatic'],
        'root_causes': ['history', 'ethnic', 'economic', 'political tensions'],
    }
    
    summary_lower = articles_summary.lower()
    coverage = {}
    for category, words in keywords.items():
        coverage[category] = sum(1 for word in words if word in summary_lower)
    
    missing = [cat for cat, count in coverage.items() if count == 0]
    
    return {
        'coverage_balance': 'balanced' if len(missing) <= 1 else 'one-sided',
        'perspectives_found': [cat for cat in coverage if coverage[cat] > 0],
        'missing_perspectives': missing,
        'recommendation': 'Seek sources covering: ' + ', '.join(missing) if missing else 'Good coverage balance'
    }


@tool
def detect_corruption_indicators(text: str, country: str) -> Dict[str, Any]:
    """Detect potential corruption-related keywords and patterns in news text.
    
    Args:
        text: News article text to analyze
        country: Country name for context
        
    Returns:
        Dict with corruption_signals, severity, and key_terms
    """
    # Common corruption indicators
    indicators = {
        'high_severity': ['bribery', 'embezzlement', 'money laundering', 'kickback', 'slush fund'],
        'medium_severity': ['nepotism', 'cronyism', 'conflict of interest', 'insider trading'],
        'investigation_keywords': ['investigation', 'probe', 'charges', 'indictment', 'whistleblower'],
        'transparency_issues': ['opacity', 'secret deal', 'offshore', 'shell company', 'undisclosed'],
    }
    
    text_lower = text.lower()
    found_signals = {}
    for category, terms in indicators.items():
        found = [term for term in terms if term in text_lower]
        if found:
            found_signals[category] = found
    
    severity = 'high' if found_signals.get('high_severity') else 'medium' if found_signals.get('medium_severity') else 'low'
    
    return {
        'country': country,
        'severity': severity,
        'signals_found': found_signals,
        'has_investigation': bool(found_signals.get('investigation_keywords')),
        'transparency_concerns': bool(found_signals.get('transparency_issues')),
    }


@tool
@retry_with_backoff(max_retries=2, exceptions=(requests.RequestException,))
def fact_check_claim(claim: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Check if a claim has been fact-checked using Google Fact Check API.
    
    Args:
        claim: The claim to fact-check
        api_key: Google Fact Check API key (optional, reads from env)
        
    Returns:
        Dict with fact_check_results, ratings, and sources
    """
    if not api_key:
        api_key = os.getenv('GOOGLE_FACT_CHECK_API_KEY')
    
    if not api_key:
        return {'error': 'Google Fact Check API key not configured', 'results': []}
    
    try:
        url = 'https://factchecktools.googleapis.com/v1alpha1/claims:search'
        params = {'query': claim, 'key': api_key, 'languageCode': 'en'}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        claims = data.get('claims', [])
        
        if not claims:
            return {'found': False, 'message': 'No fact-checks found for this claim'}
        
        results = []
        for c in claims[:3]:  # Top 3 results
            review = c.get('claimReview', [{}])[0]
            results.append({
                'claim': c.get('text', claim),
                'rating': review.get('textualRating', 'Unknown'),
                'publisher': review.get('publisher', {}).get('name', 'Unknown'),
                'url': review.get('url', ''),
                'date': review.get('reviewDate', '')
            })
        
        return {'found': True, 'results': results, 'count': len(results)}
    
    except requests.RequestException as e:
        logger.warning(f"Fact check API error: {e}")
        return {'error': str(e), 'results': []}


@tool
def extract_citations(text: str) -> Dict[str, Any]:
    """Extract quoted sources and citations from article text.
    
    Args:
        text: Article text to analyze
        
    Returns:
        Dict with quoted_sources, citation_count, and credibility_assessment
    """
    # Patterns for detecting citations
    quote_patterns = [
        r'"([^"]+)"\s*(?:said|stated|claimed|told|according to)\s+([A-Z][\w\s,\.]+)',
        r'([A-Z][\w\s,\.]+)\s+(?:said|stated|claimed|told)\s*[:"]',
        r'according to ([A-Z][\w\s,\.]+)',
    ]
    
    citations = []
    for pattern in quote_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            source = match[-1] if isinstance(match, tuple) else match
            source = source.strip(' ,:.')
            if len(source) > 3 and len(source) < 100:  # Filter noise
                citations.append(source)
    
    # Categorize sources
    categories = {
        'official': ['official', 'government', 'minister', 'spokesperson', 'president', 'secretary'],
        'expert': ['professor', 'doctor', 'researcher', 'analyst', 'expert'],
        'witness': ['witness', 'resident', 'civilian', 'victim', 'survivor'],
        'anonymous': ['anonymous', 'unnamed', 'sources say', 'officials say'],
    }
    
    categorized = {'official': [], 'expert': [], 'witness': [], 'anonymous': [], 'other': []}
    for citation in citations:
        citation_lower = citation.lower()
        matched = False
        for category, keywords in categories.items():
            if any(kw in citation_lower for kw in keywords):
                categorized[category].append(citation)
                matched = True
                break
        if not matched:
            categorized['other'].append(citation)
    
    return {
        'total_citations': len(citations),
        'unique_sources': len(set(citations)),
        'by_category': {k: v for k, v in categorized.items() if v},
        'source_diversity': 'high' if len(categorized) > 3 else 'medium' if len(categorized) > 1 else 'low'
    }


@tool
def detect_language(text: str) -> Dict[str, str]:
    """Detect language of text using langdetect.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dict with language code and confidence
    """
    if not LANGDETECT_AVAILABLE:
        return {'language': 'unknown', 'error': 'langdetect not installed'}
    
    try:
        lang = detect(text)
        return {'language': lang, 'confidence': 'high'}
    except LangDetectException:
        return {'language': 'unknown', 'confidence': 'low'}


@tool
@retry_with_backoff(max_retries=2, exceptions=(requests.RequestException,))
def translate_text(text: str, target_lang: str = 'en', source_lang: Optional[str] = None) -> Dict[str, str]:
    """Translate text using LibreTranslate API (free, self-hosted option).
    
    Args:
        text: Text to translate
        target_lang: Target language code (default: 'en')
        source_lang: Source language (auto-detect if None)
        
    Returns:
        Dict with translated text and detected source language
    """
    # Use LibreTranslate free API (can be self-hosted)
    url = os.getenv('LIBRETRANSLATE_URL', 'https://libretranslate.com/translate')
    
    payload = {
        'q': text,
        'target': target_lang,
        'format': 'text'
    }
    
    if source_lang:
        payload['source'] = source_lang
    else:
        payload['source'] = 'auto'
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        return {
            'translated_text': data.get('translatedText', text),
            'detected_language': data.get('detectedLanguage', {}).get('language', 'unknown')
        }
    except Exception as e:
        logger.warning(f"Translation failed: {e}")
        return {'translated_text': text, 'error': str(e)}


@tool
def analyze_bias_nlp(text: str) -> Dict[str, Any]:
    """Analyze political bias using NLP model (transformers).
    
    Args:
        text: Text to analyze
        
    Returns:
        Dict with bias prediction, confidence, and political lean
    """
    if not TRANSFORMERS_AVAILABLE:
        return {'error': 'transformers library not installed', 'bias': 'neutral'}
    
    try:
        # Use pre-trained sentiment model as proxy for bias detection
        # In production, use fine-tuned bias detection model
        classifier = pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english')
        result = classifier(text[:512])[0]  # Limit to 512 tokens
        
        # Map sentiment to political bias (simplified)
        score = result['score']
        label = result['label']
        
        if label == 'POSITIVE':
            bias_direction = 'slightly right' if score > 0.7 else 'neutral'
        else:
            bias_direction = 'slightly left' if score > 0.7 else 'neutral'
        
        return {
            'bias_direction': bias_direction,
            'confidence': score,
            'method': 'NLP-based (DistilBERT)',
            'note': 'Using sentiment as bias proxy - production needs fine-tuned model'
        }
    except Exception as e:
        logger.warning(f"NLP bias analysis failed: {e}")
        return {'error': str(e), 'bias': 'neutral'}


def check_env() -> None:
    print("\n🔑 Environment:")
    v = os.getenv("VALYU_API_KEY")
    t = os.getenv("HOLISTIC_AI_TEAM_ID")
    k = os.getenv("HOLISTIC_AI_API_TOKEN")
    ls = os.getenv("LANGCHAIN_TRACING_V2")
    print("  VALYU_API_KEY:", bool(v), mask(v))
    print("  HOLISTIC_AI_TEAM_ID:", bool(t), mask(t))
    print("  HOLISTIC_AI_API_TOKEN:", bool(k), mask(k))
    if ls:
        print("  🔍 LangSmith tracing enabled")


def build_search_query(query: str, sources: Optional[List[str]]) -> str:
    if sources:
        site_filters = " OR ".join([f"site:{s.strip()}" for s in sources if s.strip()])
        return f"{query} ({site_filters})"
    return query


@retry_with_backoff(
    max_retries=3,
    exceptions=(Exception,),
    rate_limit_exceptions=(RateLimitError,),
    rate_limit_delay=10.0
)
@instrument("valyu_search")
def run_valyu_search(query: str,
                     sources: Optional[List[str]],
                     search_type: str,
                     max_results: int,
                     relevance_threshold: Optional[float],
                     max_price: Optional[float],  # Pricing: Open DB $0.50/1k, Web $1.50/1k, Financial $8/1k, Proprietary $30-50/1k
                     language: Optional[str] = None,  # Not currently supported by API
                     region: Optional[str] = None,    # Not currently supported by API
                     date_from: Optional[str] = None,
                     date_to: Optional[str] = None,
                     response_length: str = "large",
                     fast_mode: bool = False,
                     included_sources: Optional[List[str]] = None,
                     excluded_sources: Optional[List[str]] = None,
                     category: Optional[str] = None,
                     country_code: Optional[str] = None,
                     is_tool_call: bool = True):
    # Track API request and LLM call for emissions calculation (5g CO2e per request)
    # Valyu uses LLMs under the hood, so it counts as both API and LLM call
    track_api_request()
    track_llm_call()
    
    tool = ValyuSearchTool(valyu_api_key=os.getenv("VALYU_API_KEY"))
    q = build_search_query(query, sources)
    kwargs = {
        "query": q,
        "search_type": search_type,
        "max_num_results": int(max_results),
    }
    if relevance_threshold is not None and relevance_threshold >= 0:
        kwargs["relevance_threshold"] = float(relevance_threshold)
    if max_price is not None and max_price > 0:
        kwargs["max_price"] = float(max_price)
    
    # Advanced filters supported by Valyu API
    if date_from:
        kwargs["start_date"] = date_from  # Valyu uses start_date
    if date_to:
        kwargs["end_date"] = date_to  # Valyu uses end_date
    if response_length:
        kwargs["response_length"] = response_length  # large, medium, small
    if fast_mode:
        kwargs["fast_mode"] = True
    if included_sources:
        kwargs["included_sources"] = included_sources
    if excluded_sources:
        kwargs["excluded_sources"] = excluded_sources
    if category:
        kwargs["category"] = category
    if country_code:
        kwargs["country_code"] = country_code.upper()[:2]
    kwargs["is_tool_call"] = bool(is_tool_call)
    
    # Note: language and region filters not currently supported by Valyu API
    if language or region:
        logger.info(f"Language/region filters not supported by Valyu API: language={language}, region={region}")

    result = tool._run(**kwargs)
    
    # Handle different return types from ValyuSearchTool
    fallback_used = False
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            fallback_used = True
            result = {"results": [{"title": "Search Result", "description": result, "source": "web"}]}
    # Only attempt model conversion if not already a dict
    elif not isinstance(result, dict):
        if hasattr(result, "model_dump"):
            try:
                result = result.model_dump()
            except Exception:
                pass
        elif hasattr(result, "dict"):
            try:
                result = result.dict()
            except Exception:
                pass
    # Annotate fallback_used flag in the result dict (non-breaking addition)
    if isinstance(result, dict) and "fallback_used" not in result:
        result["fallback_used"] = fallback_used
    
    return result


@instrument("analyze_pipeline")
def analyze_pipeline(query: str, articles: List[dict], llm) -> str:
    # First, run per-article bias analysis
    bias_results = analyze_articles_bias(articles)
    
    # Build enhanced article text with bias scores
    articles_text_parts = []
    for i, a in enumerate(articles[:10]):
        bias_info = ""
        if i < len(bias_results['articles']):
            bias_detail = bias_results['articles'][i]
            bias_scores = bias_detail.get('bias_scores', {})
            classification = bias_detail.get('classification', {})
            bias_info = f"\n  Bias: {classification.get('bias_category', 'unknown')} | Political Lean: {bias_scores.get('political_lean', 0):.0f} | Overall Bias: {bias_scores.get('overall_bias', 0):.0f}/50"
        
        articles_text_parts.append(
            f"Article {i+1}:\n"
            f"Title: {a.get('title','N/A')}\n"
            f"Source: {a.get('source','N/A')} (Credibility: {bias_results['articles'][i].get('classification', {}).get('credibility_tier', 'unknown') if i < len(bias_results['articles']) else 'unknown'})\n"
            f"URL: {a.get('url','N/A')}\n"
            f"Description: {a.get('description','N/A')}"
            f"{bias_info}"
        )
    
    articles_text = "\n\n".join(articles_text_parts)
    
    # Add aggregate bias statistics
    aggregate = bias_results.get('aggregate_stats', {})
    bias_summary = f"""
BIAS ANALYSIS SUMMARY:
- Articles analyzed: {bias_results.get('article_count', 0)}
- Average overall bias: {aggregate.get('average_scores', {}).get('overall_bias', 0):.1f}/50
- Political distribution: {aggregate.get('coverage_assessment', {}).get('left_leaning_articles', 0)} left, {aggregate.get('coverage_assessment', {}).get('neutral_articles', 0)} neutral, {aggregate.get('coverage_assessment', {}).get('right_leaning_articles', 0)} right
- Credibility: {aggregate.get('coverage_assessment', {}).get('high_credibility_count', 0)} high, {aggregate.get('coverage_assessment', {}).get('low_credibility_count', 0)} low
- Propaganda techniques detected: {aggregate.get('propaganda_analysis', {}).get('total_techniques_detected', 0)}
- Source types: {aggregate.get('category_breakdown', {}).get('source_types', {})}
"""
    
    # Detect query type
    query_lower = query.lower()
    is_conflict = any(word in query_lower for word in ['war', 'conflict', 'fighting', 'violence', 'crisis', 'attack'])
    is_corruption = any(word in query_lower for word in ['corruption', 'scandal', 'fraud', 'bribery', 'embezzlement'])
    
    if is_conflict:
        focus_areas = (
            "Focus on:\n"
            "- Civilian impact and humanitarian situation\n"
            "- Balance between government, opposition, and civilian perspectives\n"
            "- Verification of casualty figures and claims\n"
            "- Historical context and root causes\n"
            "- International response and diplomacy"
        )
    elif is_corruption:
        focus_areas = (
            "Focus on:\n"
            "- Distinguishing allegations from proven facts\n"
            "- Credibility of sources (whistleblowers, official investigations)\n"
            "- Financial evidence and transparency\n"
            "- Political context and potential bias\n"
            "- Legal proceedings and accountability"
        )
    else:
        focus_areas = "Focus on balanced, fact-based analysis."
    
    system_prompt = (
        "You are an expert investigative journalist and news analyst specializing in conflict reporting, corruption investigations, and bias detection.\n\n"
        "You have been provided with per-article bias analysis scores. Use this data to inform your analysis.\n\n"
        "Analyze the provided news articles and provide:\n"
        "1) Summary of key facts and claims\n"
        "2) Source credibility and diversity assessment (use the bias scores provided)\n"
        "3) Potential bias indicators and narrative differences (reference the detected bias categories)\n"
        "4) Missing perspectives or coverage gaps\n"
        "5) Factual concerns or unverified claims\n"
        "6) Recommendations for seeking balanced information\n\n"
        f"{focus_areas}\n\n"
        "Be objective, cite specific examples with URLs, and clearly mark unverified information.\n"
        "Reference the bias scores in your analysis to explain which sources lean left/right and why."
    )
    user_prompt = f"""Analyze these news articles about "{query}":\n\n{bias_summary}\n\n{articles_text}\n\nProvide a comprehensive, fact-checked analysis with citations, incorporating the bias scores provided."""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    track_llm_call()  # Track emissions
    resp = llm.invoke(messages)
    return getattr(resp, "content", str(resp))


@instrument("analyze_agent")
def analyze_agent(query: str, sources: Optional[List[str]], trace: bool, custom_tools: Optional[List[str]] = None, config: Optional[Config] = None, llm: Any = None) -> Tuple[str, List]:
    """Run agent with configurable tools."""
    if not config:
        config = Config()
    if llm is None:
        llm_config = config.get('llm', {})
        llm = get_chat_model(
            model_name=llm_config.get('model', 'claude-3-5-sonnet'),
            temperature=llm_config.get('temperature', 0.1),
            max_tokens=llm_config.get('max_tokens', 3072)
        )
    
    # Build tool list - include news-focused tools by default
    tools: List[Any] = [ValyuSearchTool(valyu_api_key=os.getenv("VALYU_API_KEY"))]
    
    # Auto-detect query type and add relevant tools
    query_lower = query.lower()
    is_conflict = any(word in query_lower for word in ['war', 'conflict', 'fighting', 'violence', 'crisis', 'attack'])
    is_corruption = any(word in query_lower for word in ['corruption', 'scandal', 'fraud', 'bribery', 'embezzlement'])
    
    if custom_tools:
        if 'bias' in custom_tools and config.is_tool_enabled('bias_scoring'):
            tools.append(calculate_bias_score)
        if 'credibility' in custom_tools and config.is_tool_enabled('credibility_check'):
            tools.append(check_source_credibility)
        if 'conflict' in custom_tools or is_conflict:
            if config.is_tool_enabled('conflict_analysis'):
                tools.append(detect_conflict_coverage_gaps)
        if 'corruption' in custom_tools or is_corruption:
            if config.is_tool_enabled('corruption_detection'):
                tools.append(detect_corruption_indicators)
        if 'fact_check' in custom_tools and config.is_tool_enabled('fact_checking'):
            tools.append(fact_check_claim)
        if 'citations' in custom_tools and config.is_tool_enabled('citation_extraction'):
            tools.append(extract_citations)
        if 'language' in custom_tools and config.is_tool_enabled('citation_extraction'):
            tools.append(detect_language)
            tools.append(translate_text)
        if 'nlp_bias' in custom_tools:
            tools.append(analyze_bias_nlp)
    else:
        # Auto-add tools based on query type and config
        if config.is_tool_enabled('credibility_check'):
            tools.append(check_source_credibility)
        if is_conflict and config.is_tool_enabled('conflict_analysis'):
            tools.append(detect_conflict_coverage_gaps)
        if is_corruption and config.is_tool_enabled('corruption_detection'):
            tools.append(detect_corruption_indicators)
        if config.is_tool_enabled('citation_extraction'):
            tools.append(extract_citations)
        if config.is_tool_enabled('fact_checking') and config.get_api_key('google_fact_check'):
            tools.append(fact_check_claim)
    
    agent = create_react_agent(llm, tools=tools)

    site_hint = f"\nPrefer results from: {', '.join(sources)}." if sources else "\nSearch across diverse international sources (BBC, Al Jazeera, Reuters, etc.)."
    
    # Tailored prompt based on query type
    if is_conflict:
        specific_guidance = (
            "\nFor conflict/war coverage, specifically analyze:\n"
            "- Civilian impact and humanitarian situation\n"
            "- Multiple perspectives (government, opposition, civilians, international)\n"
            "- Historical context and root causes\n"
            "- Fact-check claims from all sides\n"
            "- Identify any propaganda or one-sided reporting"
        )
    elif is_corruption:
        specific_guidance = (
            "\nFor corruption coverage, specifically analyze:\n"
            "- Evidence vs allegations\n"
            "- Sources of information (whistleblowers, investigations, leaked documents)\n"
            "- Political context and potential motivations\n"
            "- Financial trails and transparency issues\n"
            "- Legal proceedings or lack thereof"
        )
    else:
        specific_guidance = ""
    
    prompt = (
        "You are an expert investigative journalist and news analyst specializing in conflict reporting, corruption investigations, and bias detection.\n\n"
        f"Research the topic: '{query}'. Use the Valyu search tool to gather current news from multiple international sources.{site_hint}\n"
        f"{specific_guidance}\n\n"
        "Provide a comprehensive analysis including:\n"
        "1. Summary of key facts and developments\n"
        "2. Source diversity and credibility assessment\n"
        "3. Bias indicators and narrative differences\n"
        "4. Missing perspectives or coverage gaps\n"
        "5. Factual concerns or unverified claims\n"
        "6. Recommendations for seeking balanced information\n\n"
        "Always cite specific URLs and sources. Be objective, fact-based, and highlight when information is disputed or unverified."
    )
    result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    messages = result.get("messages", []) if isinstance(result, dict) else []
    content = ""
    if messages:
        last = messages[-1]
        content = getattr(last, "content", "") or ""
    if not content:
        content = str(result)
    return content, messages if trace else []


def analyze_structured(query: str, articles: List[dict], llm) -> Any:
    """Analyze with structured per-article bias output."""
    
    # Run per-article bias analysis
    bias_results = analyze_articles_bias(articles)
    
    # Optionally enhance with LLM-based advanced analysis for top articles
    if len(articles) > 0:
        try:
            # Analyze top 5 articles with advanced LLM analysis
            for i, article in enumerate(articles[:5]):
                advanced = analyze_bias_advanced(article, llm)
                framing = detect_framing_techniques(article, llm)
                power = analyze_power_dynamics(article)
                
                # Add to the article's analysis
                if i < len(bias_results['articles']):
                    bias_results['articles'][i]['advanced_analysis'] = {
                        **advanced,
                        'framing_techniques': framing,
                        'power_dynamics': power
                    }
        except Exception as e:
            logger.warning(f"Advanced analysis failed for some articles: {e}")
    
    # Add narrative comparison across all articles
    try:
        narrative_comparison = compare_article_narratives(articles, llm)
        bias_results['narrative_comparison'] = narrative_comparison
    except Exception as e:
        logger.warning(f"Narrative comparison failed: {e}")
    
    # Generate overall assessment and recommendations
    aggregate = bias_results.get('aggregate_stats', {})
    avg_bias = aggregate.get('average_scores', {}).get('overall_bias', 0)
    coverage = aggregate.get('coverage_assessment', {})
    
    # Build assessment
    assessment_parts = []
    if avg_bias > 60:
        assessment_parts.append("High overall bias detected across sources.")
    elif avg_bias > 40:
        assessment_parts.append("Moderate bias present in coverage.")
    else:
        assessment_parts.append("Relatively balanced coverage overall.")
    
    left_count = coverage.get('left_leaning_articles', 0)
    right_count = coverage.get('right_leaning_articles', 0)
    neutral_count = coverage.get('neutral_articles', 0)
    
    if left_count > right_count * 2:
        assessment_parts.append("Coverage skews left-leaning.")
    elif right_count > left_count * 2:
        assessment_parts.append("Coverage skews right-leaning.")
    elif neutral_count > (left_count + right_count):
        assessment_parts.append("Most sources maintain neutral framing.")
    else:
        assessment_parts.append("Mixed political perspectives represented.")
    
    high_cred = coverage.get('high_credibility_count', 0)
    low_cred = coverage.get('low_credibility_count', 0)
    if high_cred > low_cred * 2:
        assessment_parts.append("Strong source credibility overall.")
    elif low_cred > high_cred:
        assessment_parts.append("Caution: many low-credibility sources.")
    
    overall_assessment = " ".join(assessment_parts)
    
    # Generate recommendations
    recommendations = []
    if avg_bias > 50:
        recommendations.append("Seek additional sources from different political perspectives")
    if low_cred > 2:
        recommendations.append("Verify claims with high-credibility sources (AP, Reuters, BBC)")
    if left_count == 0 or right_count == 0:
        recommendations.append("Read sources from both left and right to understand all viewpoints")
    
    propaganda_count = aggregate.get('propaganda_analysis', {}).get('total_techniques_detected', 0)
    if propaganda_count > 5:
        recommendations.append("High propaganda detected - critically evaluate emotional language and framing")
    
    if neutral_count == 0:
        recommendations.append("All sources show bias - seek neutral international sources")
    
    recommendations.append("Cross-reference facts across multiple independent sources")
    
    # Get all URLs
    cited_urls = [a.get('url', '') for a in articles if a.get('url')]
    
    # Build BiasAnalysis model
    articles_detail = []
    for article_analysis in bias_results.get('articles', []):
        articles_detail.append(ArticleBiasDetail(
            url=article_analysis.get('url', ''),
            title=article_analysis.get('title', ''),
            source=article_analysis.get('source', ''),
            bias_scores=article_analysis.get('bias_scores', {}),
            classification=article_analysis.get('classification', {}),
            detected_features=article_analysis.get('detected_features', {}),
            advanced_analysis=article_analysis.get('advanced_analysis')
        ))
    
    result = BiasAnalysis(
        article_count=len(articles),
        articles=articles_detail,
        aggregate_stats=aggregate,
        narrative_comparison=bias_results.get('narrative_comparison'),
        overall_assessment=overall_assessment,
        recommendations=recommendations[:5],
        cited_urls=cited_urls
    )
    
    return result


@instrument("analyze_conversation")
def analyze_conversation(query: str, memory: MemorySaver, thread_id: str = "default", llm: Any = None) -> Tuple[str, List]:
    """Multi-turn conversation with memory."""
    if llm is None:
        llm = get_chat_model(model_name="claude-3-5-sonnet", temperature=0.1, max_tokens=2048)
    tools = [ValyuSearchTool(valyu_api_key=os.getenv("VALYU_API_KEY"))]
    
    agent = create_react_agent(llm, tools=tools, checkpointer=memory)
    
    config: Any = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke({"messages": [HumanMessage(content=query)]}, config=config)
    
    messages = result.get("messages", [])
    content = messages[-1].content if messages else ""
    return content, messages


# ============================= Advanced Narrative & Evidence Tools =============================
# Prefer HolisticAI fast LLMs for lightweight tasks over local embeddings
FAST_LLM_MODEL = os.getenv("FAST_LLM_MODEL", "us.anthropic.claude-3-5-haiku-20241022-v1:0")


@tool
@instrument("cluster_narratives")
def cluster_narratives(titles_and_descriptions: List[Dict[str, str]], num_clusters: int = 3) -> Dict[str, Any]:
    """Cluster articles by narrative framing using a fast HolisticAI LLM.

    Args:
        titles_and_descriptions: List of {title, description}
        num_clusters: Desired number of narrative clusters (soft target; model can choose fewer)

    Returns:
        Dict with clusters: [{cluster_id, representative_title, size, shared_terms, items}]
    """
    items = [
        {
            "index": i,
            "title": x.get("title", ""),
            "description": x.get("description", "")
        }
        for i, x in enumerate(titles_and_descriptions or [])
    ]
    if not items:
        return {"clusters": []}

    # Use a super-fast model via HolisticAI; configurable with FAST_LLM_MODEL
    llm = get_chat_model(model_name=FAST_LLM_MODEL, temperature=0.0, max_tokens=900)

    system = (
        "You cluster short news items by narrative framing. "
        "Return compact JSON only. Avoid commentary."
    )
    # Strict JSON schema to simplify parsing
    user = (
        "Cluster the following items into up to {k} coherent narrative groups.\n"
        "Output strictly this JSON schema: {{\n"
        "  \"clusters\": [{{\n"
        "    \"cluster_id\": <int>,\n"
        "    \"representative_title\": <string>,\n"
        "    \"size\": <int>,\n"
        "    \"shared_terms\": <list of 3-8 lowercase keywords>,\n"
        "    \"items\": [{{\"title\": <string>, \"description\": <string>}}]\n"
        "  }}]\n"
        "}}\n\nItems:\n{items}"
    ).format(k=max(1, num_clusters), items=json.dumps(items)[:12000])

    resp = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=user)
    ])
    content = getattr(resp, "content", "") if resp is not None else ""

    # Robust JSON extraction
    def _extract_json(s: str) -> Any:
        try:
            return json.loads(s)
        except Exception:
            # Try to salvage largest JSON object
            m = re.search(r"\{[\s\S]*\}", s)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    return None
            return None

    parsed = _extract_json(content) if isinstance(content, str) else None
    if not isinstance(parsed, dict) or "clusters" not in parsed:
        # Fallback: single cluster with all items and lightweight shared terms
        all_text = " ".join([x.get("description", "") for x in titles_and_descriptions]).lower()
        tokens = re.findall(r"[a-zA-Z]{5,}", all_text)
        freq: Dict[str, int] = {}
        for w in tokens:
            freq[w] = freq.get(w, 0) + 1
        shared = [w for w, _c in sorted(freq.items(), key=lambda kv: -kv[1])[:6]]
        return {
            "clusters": [
                {
                    "cluster_id": 0,
                    "representative_title": titles_and_descriptions[0].get("title", ""),
                    "size": len(titles_and_descriptions),
                    "shared_terms": shared,
                    "items": titles_and_descriptions,
                }
            ]
        }

    # Normalize structure
    clusters_in = parsed.get("clusters") or []
    norm_clusters: List[Dict[str, Any]] = []
    for idx, c in enumerate(clusters_in):
        if not isinstance(c, dict):
            continue
        rep = c.get("representative_title") or (c.get("items", [{}])[0].get("title") if c.get("items") else "")
        its_raw = c.get("items")
        its: List[Dict[str, Any]] = its_raw if isinstance(its_raw, list) else []
        size_val = c.get("size")
        size_int = int(size_val) if isinstance(size_val, int) else len(its)
        norm_clusters.append({
            "cluster_id": int(c.get("cluster_id", idx)),
            "representative_title": rep or "",
            "size": size_int,
            "shared_terms": [t for t in (c.get("shared_terms") or []) if isinstance(t, str)][:8],
            "items": [
                {"title": (it.get("title") or ""), "description": (it.get("description") or "")}
                for it in its if isinstance(it, dict)
            ],
        })
    return {"clusters": norm_clusters}


@tool
@instrument("evidence_strength")
def evidence_strength(text: str) -> Dict[str, Any]:
    """Score evidence strength in article text.

    Categories considered: eyewitness, official, expert, leaked, anonymous, speculative.
    Returns normalized score and counts per category.
    """
    t = text.lower()
    patterns = {
        "eyewitness": ["witness", "saw", "reported by residents", "on the ground"],
        "official": ["minister", "government", "official statement", "spokesperson", "agency"],
        "expert": ["researcher", "professor", "analyst", "expert", "study"],
        "leaked": ["leaked", "documents obtained", "internal memo", "whistleblower"],
        "anonymous": ["anonymous", "unnamed", "sources say", "according to sources"],
        "speculative": ["may", "might", "could", "potential", "believed to"],
    }
    counts = {}
    total = 0
    for cat, kws in patterns.items():
        c = sum(t.count(k) for k in kws)
        counts[cat] = c
        total += c
    # Strength heuristic: (positive evidence categories) - (speculative + anonymous weight)
    positive = counts["eyewitness"] + counts["official"] + counts["expert"] + counts["leaked"]
    penalty = counts["anonymous"] * 0.5 + counts["speculative"] * 0.3
    raw = positive - penalty
    norm = max(0.0, min(1.0, raw / (positive + penalty + 1)))
    return {"score": round(norm, 3), "counts": counts, "raw_score": raw}


@tool
@instrument("detect_propaganda")
def detect_propaganda(text: str) -> Dict[str, Any]:
    """Detect basic propaganda techniques via keyword heuristics.
    Techniques: appeal_to_fear, bandwagon, whataboutism, demonizing, loaded_language.
    """
    t = text.lower()
    techniques = {
        "appeal_to_fear": ["catastrophic", "existential threat", "devastating", "annihilation"],
        "bandwagon": ["everyone knows", "widely accepted", "it is clear to all"],
        "whataboutism": ["what about", "while ignoring", "instead of addressing"],
        "demonizing": ["barbaric", "evil regime", "savage", "inhuman"],
        "loaded_language": ["betrayal", "collapse", "treason", "puppet", "corrupt"],
    }
    found = {}
    for tech, kws in techniques.items():
        hits = [k for k in kws if k in t]
        if hits:
            found[tech] = hits
    return {"techniques_found": found, "count": len(found)}


@instrument("analyze_debate")
def analyze_debate(query: str, sources: Optional[List[str]], trace: bool, llm: Any = None) -> str:
    """Run a multi-agent debate with left/right/neutral framings."""
    if llm is None:
        llm = get_chat_model(model_name="claude-3-5-sonnet", temperature=0.3, max_tokens=1536)
    # Single search tool shared; agents adopt different system prompts
    search_tool = ValyuSearchTool(valyu_api_key=os.getenv("VALYU_API_KEY"))
    base_prompt = f"Topic: {query}. Use search tool for evidence, cite URLs." + (f" Preferred sources: {', '.join(sources)}." if sources else "")
    roles = {
        "left": "Progressive policy emphasis, social impact, equity lens. Avoid exaggeration.",
        "right": "Conservative emphasis on stability, economic/liberty concerns. Avoid strawman.",
        "neutral": "Balanced synthesis focusing on verifiable facts and multiple perspectives.",
    }
    outputs = {}
    for role, desc in roles.items():
        agent = create_react_agent(llm, tools=[search_tool])
        prompt = f"Role: {role}\nGuidance: {desc}\n{base_prompt}\nProduce a concise argument (facts + 3 claims + 2 caveats)."
        track_llm_call()  # Track emissions for agent invocation
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        msgs = result.get("messages", []) if isinstance(result, dict) else []
        content = ""
        if msgs:
            content = getattr(msgs[-1], "content", "") or ""
        outputs[role] = content or str(result)
    # Synthesis
    synth_prompt = (
        "Compare the three arguments and produce a debate summary:\n"
        "- Shared factual ground\n- Key divergences\n- Potential biases\n- Most evidence-backed claims\n- Missing perspectives\n"
    )
    track_llm_call()  # Track emissions
    synthesis = llm.invoke([
        SystemMessage(content="You synthesize debate viewpoints objectively."),
        HumanMessage(content=synth_prompt + json.dumps(outputs))
    ])
    return json.dumps({"arguments": outputs, "synthesis": getattr(synthesis, "content", str(synthesis))}, indent=2)


def print_articles(articles: List[dict], limit: int = 10) -> None:
    print("\n📰 Articles (preview):")
    for i, a in enumerate(articles[:limit], 1):
        title = a.get("title", "Untitled")
        src = a.get("source", "unknown")
        url = a.get("url", "")
        print(f"  {i}. {title} [{src}] {url}")


def run_benchmark(set_name: str, benchmark_file: str = "data/benchmarks/queries.json", metrics: bool = True, llm: Any = None) -> None:
    """Run a predefined benchmark set and print aggregated scoreboard.

    Args:
        set_name: Name of the benchmark set in queries.json (e.g. 'standard_news','investigative','all').
        benchmark_file: Path to JSON file containing benchmark definitions.
        metrics: Whether to print instrumentation metrics at end.
    """
    if not os.path.exists(benchmark_file):
        print(f"\n❌ Benchmark file not found: {benchmark_file}")
        return
    with open(benchmark_file, "r") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"\n❌ Failed parsing benchmark file: {e}")
            return
    if set_name == "all":
        # Merge all sets
        queries: List[Dict[str, Any]] = []
        for v in data.values():
            if isinstance(v, list):
                queries.extend(v)
    else:
        queries = data.get(set_name, [])
    if not queries:
        print(f"\n❌ No queries found for benchmark set '{set_name}'")
        return

    print(f"\n🚀 Running benchmark set: {set_name} (queries={len(queries)})")
    # Build a single LLM for this run if not provided
    if llm is None:
        llm = get_chat_model(model_name="claude-3-5-sonnet", temperature=0.1, max_tokens=3072)
    start_emissions_tracker()
    reset_metrics()
    scoreboard: List[Dict[str, Any]] = []

    for i, q in enumerate(queries, 1):
        q_query = q.get("query")
        mode = q.get("mode", "agent")
        tools = q.get("tools")
        max_results = int(q.get("max_results", 5))
        response_length = q.get("response_length", "large")
        print(f"\n[{i}/{len(queries)}] Query: {q_query} | Mode: {mode} | Tools: {tools or 'auto'}")
        # Search
        search = run_valyu_search(
            query=q_query,
            sources=None,
            search_type="all",
            max_results=max_results,
            relevance_threshold=0.0,
            max_price=0.0,
            response_length=response_length,
            fast_mode=False,
            included_sources=None,
            excluded_sources=None,
            category=None,
            country_code=None,
            is_tool_call=True,
        )
        articles = search.get("results", []) if isinstance(search, dict) else []
        cost = search.get("total_cost_dollars") or search.get("total_deduction_dollars") or 0.0
        # Mode-specific analysis
        if mode == "agent":
            result_text, _msgs = analyze_agent(q_query, None, False, tools.split(",") if tools else None, None, llm)
        elif mode == "pipeline":
            result_text = analyze_pipeline(q_query, articles, llm)
        elif mode == "structured":
            structured = analyze_structured(str(q_query or ""), articles, llm)
            result_text = json.dumps(structured.model_dump(), indent=2) if hasattr(structured, "model_dump") else str(structured)
        elif mode == "debate":
            result_text = analyze_debate(q_query, None, False, llm)
        else:
            result_text = "Unsupported mode"

        # Collect instrumentation snapshot
        current_metrics = get_metrics()
        # Attempt to pull latest function latencies
        by_name = current_metrics.get("by_name", {})
        search_latency = by_name.get("valyu_search", {}).get("avg_ms")
        analysis_latency = None
        for k in ["analyze_agent", "analyze_pipeline", "analyze_structured", "analyze_debate"]:
            if k in by_name:
                analysis_latency = by_name[k]["avg_ms"]
        scoreboard.append({
            "query": q_query,
            "mode": mode,
            "tools": tools or "auto",
            "articles": len(articles),
            "cost_usd": cost,
            "search_latency_ms": search_latency,
            "analysis_latency_ms": analysis_latency,
        })

    stop_emissions_tracker()
    emissions = get_metrics().get("emissions_kg")

    # Summary
    print("\n📊 Benchmark Scoreboard:")
    for row in scoreboard:
        print(f" - {row['query'][:50]:50} | mode={row['mode']:9} | art={row['articles']:2} | cost=${row['cost_usd']:.4f} | search={row['search_latency_ms']}ms | analysis={row['analysis_latency_ms']}ms")
    total_cost = sum(r["cost_usd"] for r in scoreboard)
    avg_search = round(sum(r["search_latency_ms"] for r in scoreboard if r["search_latency_ms"])/max(1, len([r for r in scoreboard if r["search_latency_ms"]])) ,2)
    avg_analysis = round(sum(r["analysis_latency_ms"] for r in scoreboard if r["analysis_latency_ms"])/max(1, len([r for r in scoreboard if r["analysis_latency_ms"]])) ,2)
    print(f"\nTotals: queries={len(scoreboard)} total_cost=${total_cost:.4f} avg_search={avg_search}ms avg_analysis={avg_analysis}ms")
    if emissions is not None:
        print(f"Emissions (kg CO2e): {emissions:.6f}")

    # JSON output file
    out_path = f"benchmark_{set_name}.json"
    with open(out_path, "w") as f:
        json.dump({
            "set": set_name,
            "total_queries": len(scoreboard),
            "total_cost_usd": total_cost,
            "avg_search_latency_ms": avg_search,
            "avg_analysis_latency_ms": avg_analysis,
            "emissions_kg": emissions,
            "rows": scoreboard,
        }, f, indent=2)
    print(f"\n✅ Benchmark JSON saved: {out_path}")


# ============================= Ingestion Helpers =============================
from urllib.parse import urlparse

def _host_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "").lower()
    except Exception:
        return ""

def annotate_mirror_flags(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    mirror_patterns = ["amp.", "m.", "news.google"]
    for a in articles:
        url = a.get("url", "") or ""
        src = a.get("source", "") or ""
        host = _host_from_url(url)
        src_host = src.replace("www.", "").split("/")[0].lower()
        mirror = False
        if host and src_host and host != src_host:
            mirror = True
        if any(p in host for p in mirror_patterns):
            mirror = True
        flags.append({"url": url, "mirror_used": bool(mirror)})
    return flags

def fetch_with_category_coverage(query: str, total_max: int = 9, per_class_min: int = 2, response_length: str = "medium") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch articles ensuring minimum coverage across classes and return ingestion metadata.

    Returns: (articles, meta) where meta contains counts_by_class, missing_classes, total_results, requests, fallback_used, mirror_flags.
    """
    state_seeds = ["rt.com","tass.com","sputniknews.com","xinhua.com","chinadaily.com.cn","globaltimes.cn"]
    intl_seeds = ["bbc.com","cnn.com","reuters.com","apnews.com","aljazeera.com","theguardian.com","nytimes.com","washingtonpost.com","france24.com","dw.com"]
    diaspora_seeds = ["medium.com","substack.com","blogspot.com","wordpress.com"]

    combined: List[Dict[str, Any]] = []
    seen_urls: set = set()
    any_fallback = False
    requests = 0
    total_cost = 0.0

    def _merge(results: List[Dict[str, Any]]):
        for r in results:
            u = r.get("url") or r.get("link") or ""
            if u and u not in seen_urls:
                seen_urls.add(u)
                combined.append(r)

    # Targeted fetches per class
    for seeds, label in [
        (state_seeds, "state_aligned"),
        (intl_seeds, "international"),
        (diaspora_seeds, "diaspora_blog"),
    ]:
        if len(combined) >= total_max:
            break
        requests += 1
        res = run_valyu_search(
            query=query,
            sources=None,
            search_type="all",
            max_results=per_class_min,
            relevance_threshold=0.0,
            max_price=0.0,
            response_length=response_length,
            fast_mode=False,
            included_sources=seeds,
            excluded_sources=None,
            category=None,
            country_code=None,
            is_tool_call=True,
        )
        if isinstance(res, dict):
            any_fallback = any_fallback or bool(res.get("fallback_used"))
            try:
                total_cost += float(res.get("total_cost_dollars") or res.get("total_deduction_dollars") or 0.0)
            except Exception:
                pass
        items = res.get("results", []) if isinstance(res, dict) else []
        _merge(items)

    # If still under total_max, do a general fetch to fill
    remaining = max(0, total_max - len(combined))
    if remaining > 0:
        requests += 1
        res = run_valyu_search(
            query=query,
            sources=None,
            search_type="all",
            max_results=remaining,
            relevance_threshold=0.0,
            max_price=0.0,
            response_length=response_length,
            fast_mode=False,
            included_sources=None,
            excluded_sources=None,
            category=None,
            country_code=None,
            is_tool_call=True,
        )
        if isinstance(res, dict):
            any_fallback = any_fallback or bool(res.get("fallback_used"))
            try:
                total_cost += float(res.get("total_cost_dollars") or res.get("total_deduction_dollars") or 0.0)
            except Exception:
                pass
        items = res.get("results", []) if isinstance(res, dict) else []
        _merge(items)

    # Build meta
    counts: Dict[str, int] = {}
    for a in combined:
        domain_or_url = a.get("url") or a.get("source") or ""
        cls = classify_source(domain_or_url)
        counts[cls] = counts.get(cls, 0) + 1
    required = {"state_aligned", "international", "diaspora_blog"}
    missing = sorted(list(required - set(k for k,v in counts.items() if v>0)))
    mirror_flags = annotate_mirror_flags(combined)
    meta = {
        "counts_by_class": counts,
        "missing_classes": missing,
        "total_results": len(combined),
        "requests": requests,
        "retries": 0,
        "fallback_used": any_fallback,
        "mirror_flags": mirror_flags,
        "mirror_count": sum(1 for f in mirror_flags if f.get("mirror_used")),
        "total_cost_usd": round(total_cost, 6),
    }
    return combined[:total_max], meta


def main():
    p = argparse.ArgumentParser(description="Enhanced Valyu + HolisticAI CLI with Advanced Features (Valyu Deepsearch)")
    p.add_argument("--mode", 
                     choices=["pipeline", "agent", "structured", "conversation", "debate", "unified-deterministic"], 
                     default="unified-deterministic", 
                     help="Execution mode")
    p.add_argument("--query", help="Topic to research (omit when using --benchmark-set)")
    # Modes removed: unified deterministic output only
    p.add_argument("--sources", help="Comma-separated sites, e.g., bbc.com,cnn.com")
    p.add_argument("--search-type", choices=["all", "web", "proprietary"], default="web")
    p.add_argument("--max-results", type=int, default=5)
    p.add_argument("--relevance-threshold", type=float, default=0.0)
    p.add_argument("--max-price", type=float, default=0.0, help="Maximum cost in USD (0.0 = unlimited). Pricing: Open DB $0.50/1k, Web $1.50/1k, Financial $8/1k, Proprietary $30-50/1k")
    p.add_argument("--trace", action="store_true", help="Show agent trace")
    p.add_argument("--tools", help="Custom tools: bias,credibility,conflict,corruption,fact_check,citations,language,nlp_bias,narrative,evidence,propaganda (comma-separated). Auto-detected based on query if not specified.")
    
    # Advanced Valyu parameters
    p.add_argument("--start-date", help="Start date (ISO: 2025-10-15 or relative: -7d, -30d)")
    p.add_argument("--end-date", help="End date (ISO: 2025-11-15 or relative: today)")
    p.add_argument("--response-length", choices=["small", "medium", "large"], default="large", help="Response detail level")
    p.add_argument("--fast-mode", action="store_true", help="Enable fast mode (lower latency, shorter results)")
    p.add_argument("--include-sources", help="Comma-separated included sources/domains/datasets")
    p.add_argument("--exclude-sources", help="Comma-separated excluded sources/domains/datasets")
    p.add_argument("--category", help="Natural language category to guide relevance (e.g. 'agentic use-cases')")
    p.add_argument("--country-code", help="2-letter country code to bias results (e.g. US, GB, FR)")
    p.add_argument("--no-tool-call", action="store_true", help="Mark request as user query (is_tool_call = false)")
    # Deprecated filters (not supported by Valyu API)
    p.add_argument("--language", help="Language filter (not supported - will be ignored)")
    p.add_argument("--region", help="Region filter (not supported - will be ignored)")
    
    # Configuration
    p.add_argument("--config", help="Path to config.yaml file")
    p.add_argument("--output-json", action="store_true", help="Output JSON (structured mode)")
    p.add_argument("--thread-id", default="default", help="Conversation thread ID")
    p.add_argument("--metrics", action="store_true", help="Print latency & emissions metrics summary at end")
    p.add_argument("--benchmark-set", choices=["standard_news", "investigative", "all"], help="Run predefined benchmark set instead of single query")
    # Output control
    p.add_argument("--json-only", action="store_true", help="Suppress all non-JSON output (radar/brief modes) and print only final JSON")
    p.add_argument("--output-file", help="Write radar/brief JSON payload to specified file path (used with --json-only)")
    args = p.parse_args()

    # Environment summary only if not pure JSON mode
    if not args.json_only:
        check_env()
    
    # Load configuration
    config = Config(config_path=args.config)
    
    # Parse date filters using config
    start_date = config.parse_date(args.start_date) if hasattr(args, 'start_date') and args.start_date else None
    end_date = config.parse_date(args.end_date) if hasattr(args, 'end_date') and args.end_date else None
    
    # Benchmark flow
    if args.benchmark_set:
        run_benchmark(args.benchmark_set)
        return

    if not args.query:
        print("\n❌ --query is required unless --benchmark-set is used.")
        return
    query = args.query
    custom_tools = args.tools.split(",") if args.tools else None
    response_length = args.response_length if hasattr(args, 'response_length') else "large"
    included_sources = [s.strip() for s in args.include_sources.split(",")] if getattr(args, "include_sources", None) else None
    excluded_sources = [s.strip() for s in args.excludeSources.split(",")] if getattr(args, "exclude_sources", None) else None
    fast_mode = bool(args.fast_mode) if hasattr(args, 'fast_mode') else False
    category = args.category if hasattr(args, 'category') else None
    country_code = args.country_code if hasattr(args, 'country_code') else None
    is_tool_call = not bool(args.no_tool_call) if hasattr(args, 'no_tool_call') else True
    
    if not args.json_only:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Mode: unified-deterministic")
        print(f"Search Type: {args.search_type}")
    if args.sources:
        print(f"Sources: {args.sources}")
    if custom_tools:
        print(f"Tools: {', '.join(custom_tools)}")
    if not args.json_only:
        if start_date or end_date or fast_mode or included_sources or excluded_sources or category or country_code or not is_tool_call:
            filters = []
            if start_date:
                filters.append(f"start={start_date}")
            if end_date:
                filters.append(f"end={end_date}")
            filters.append(f"detail={response_length}")
            if fast_mode:
                filters.append("fast_mode")
            if included_sources:
                filters.append(f"included={len(included_sources)}")
            if excluded_sources:
                filters.append(f"excluded={len(excluded_sources)}")
            if category:
                filters.append(f"category={category}")
            if country_code:
                filters.append(f"country={country_code}")
            if not is_tool_call:
                filters.append("user_query")
            print(f"Filters: {', '.join(filters)}")
        print(f"{'='*60}\n")

    sources = [s.strip() for s in args.sources.split(",")] if args.sources else None

    # Start emissions tracking before expensive calls
    start_emissions_tracker()
    # Always do a search to show transparency and article list
    search = run_valyu_search(
        query=args.query,
        sources=sources,
        search_type=args.search_type,
        max_results=args.max_results,
        relevance_threshold=args.relevance_threshold,
        max_price=args.max_price,
        language=args.language if hasattr(args, 'language') else None,
        region=args.region if hasattr(args, 'region') else None,
        date_from=start_date,
        date_to=end_date,
        response_length=response_length,
        fast_mode=fast_mode,
        included_sources=included_sources,
        excluded_sources=excluded_sources,
        category=category,
        country_code=country_code,
        is_tool_call=is_tool_call,
    )

    if not search or not isinstance(search, dict):
        print("\n⚠️  Search returned unexpected format. Attempting to convert...")
        print(f"   Type: {type(search)}")
        if hasattr(search, "model_dump"):
            search = search.model_dump()
            print("   ✅ Converted using model_dump()")
        elif hasattr(search, "dict"):
            search = search.dict()
            print("   ✅ Converted using dict()")
        else:
            print(f"\n❌ Cannot convert search result to dict: {search}")
            return

    articles = search.get("results", [])

    # Cost / metrics summary (if available)
    total_cost = search.get("total_cost_dollars") or search.get("total_deduction_dollars")
    total_pcm = search.get("total_deduction_pcm")
    total_chars = search.get("total_characters") or search.get("total_characters_count")
    if total_cost is not None and not args.json_only:
        print("\n💰 Cost Summary:")
        if total_pcm is not None:
            print(f"  CPM Deduction: {total_pcm}")
        print(f"  Total Cost (USD): {total_cost}")
        if total_chars is not None:
            print(f"  Characters Returned: {total_chars}")
        print(f"  Results Returned: {search.get('results_returned', len(articles))}/{search.get('total_results', len(articles))}")
    
    # Handle empty results
    if not articles:
        # For radar/brief, do not early return; radar fetches coverage later,
        # and brief can fallback to coverage-aware fetch to build a summary.
        if args.mode in ["radar", "brief"]:
            if not args.json_only:
                print("\n⚠️  No articles from initial search; falling back to coverage fetch.")
        else:
            if not args.json_only:
                print("\n⚠️  No articles found.")
                if search.get("error"):
                    print(f"   Error: {search['error']}")
                print(f"   Query: {search.get('query', args.query)}")
                print("\n💡 Try:")
                print("   - Broader search terms")
                print("   - Different sources or --search-type")
                print("   - Removing --sources to search all")
            return
    
    # Unified deterministic pipeline: coverage-aware fetch → cluster → metrics → JSON
    per_class_min = max(1, min(3, args.max_results // 2))
    total_cap = max(args.max_results, 9)
    covered_articles, ingestion_meta = fetch_with_category_coverage(args.query, total_cap, per_class_min, response_length)
    
    if not args.json_only:
        print(f"\n📊 Fetched {len(covered_articles)} articles across {len(ingestion_meta.get('counts_by_class', {}))} source categories")
        print(f"   Source distribution: {ingestion_meta.get('counts_by_class', {})}")
        if ingestion_meta.get('missing_classes'):
            print(f"   ⚠️  Missing classes: {', '.join(ingestion_meta['missing_classes'])}")
    
    # Use the new per-article bias system with LLM integration
    llm = get_chat_model()
    
    # Analyze bias for each article
    bias_results = analyze_articles_bias(covered_articles)
    
    # Optionally enhance with LLM-based advanced analysis for top articles
    # Note: Advanced analysis can be enabled by setting ENABLE_ADVANCED_ANALYSIS=true
    enable_advanced = os.getenv('ENABLE_ADVANCED_ANALYSIS', 'false').lower() == 'true'
    
    if enable_advanced and not args.json_only:
        print(f"\n🔍 Analyzing bias dimensions for {min(5, len(covered_articles))} top articles with LLM...")
    
    if enable_advanced:
        for i, article in enumerate(covered_articles[:5]):
            try:
                advanced = analyze_bias_advanced(article, llm)
                framing = detect_framing_techniques(article, llm)
                power = analyze_power_dynamics(article)
                
                if i < len(bias_results['articles']):
                    bias_results['articles'][i]['advanced_analysis'] = {
                        **advanced,
                        'framing_techniques': framing,
                        'power_dynamics': power
                    }
            except Exception as e:
                logger.warning(f"Advanced analysis failed for article {i}: {e}")
    
    # Add narrative comparison (skip for now to avoid LLM JSON issues)
    # try:
    #     narrative_comparison = compare_article_narratives(covered_articles, llm)
    #     bias_results['narrative_comparison'] = narrative_comparison
    # except Exception as e:
    #     logger.warning(f"Narrative comparison failed: {e}")
    
    # Build unified payload
    unified = {
        "query": args.query,
        "search_type": args.search_type,
        "article_count": len(covered_articles),
        "bias_analysis": bias_results,
        "ingestion_summary": ingestion_meta
    }

    # Stop emissions tracker & optionally print metrics
    stop_emissions_tracker()
    if getattr(args, "metrics", False) and not args.json_only:
        metrics = get_metrics()
        print("\n📈 Instrumentation Metrics:")
        if metrics.get("emissions_kg") is not None:
            print(f"  Emissions (kg CO2e): {metrics['emissions_kg']:.6f}")
        print(f"  Total Calls: {metrics['calls']}")
        for name, data in metrics.get("by_name", {}).items():
            print(f"  - {name}: count={data['count']} failures={data['failures']} avg={data['avg_ms']}ms p50={data['p50_ms']}ms max={data['max_ms']}ms")

    # Attach observability snapshot into output
    try:
        unified["observability"] = get_metrics()
    except Exception:
        pass

    # Emit JSON (stdout or file)
    out_json = json.dumps(unified, indent=2)
    if args.get("output_file") if isinstance(args, dict) else getattr(args, "output_file", None):
        try:
            with open(args.output_file, 'w') as f:
                f.write(out_json)
        except Exception as e:
            print(json.dumps({"error":"file_write_failed","detail":str(e),"payload":unified}, indent=2))
    else:
        print(out_json)
    return


if __name__ == "__main__":
    main()
