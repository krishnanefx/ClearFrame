"""
Advanced Bias Detection using LLM Analysis

This module provides sophisticated bias detection using language models
to analyze framing, narrative, omission, and subtle forms of bias that
simple keyword analysis cannot capture.
"""

import json
from typing import Dict, List, Any, Optional
import logging
from src.observability.instrumentation import track_llm_call

logger = logging.getLogger(__name__)


def analyze_bias_advanced(article: Dict[str, Any], llm=None) -> Dict[str, Any]:
    """
    Perform advanced LLM-based bias analysis on a single article.
    
    Args:
        article: Article dict with title, description, url, source
        llm: Language model instance (optional)
    
    Returns:
        Dict with advanced bias metrics
    """
    if llm is None:
        # Return basic analysis if no LLM available
        return {
            "framing_analysis": "LLM not available",
            "narrative_bias": 0,
            "omission_bias": 0,
            "language_bias": 0,
            "recommendations": []
        }
    
    text = f"{article.get('title', '')} {article.get('description', '')}"
    source = article.get('source', 'unknown')
    
    # Build analysis prompt
    system_prompt = """You are an expert media analyst specializing in detecting subtle forms of bias in news articles.

Analyze the provided article excerpt for:

1. FRAMING BIAS: How is the story framed? What perspective is centered? What's the dominant narrative?
2. LANGUAGE BIAS: Loaded language, euphemisms, emotionally charged words, passive vs active voice
3. OMISSION BIAS: What perspectives or facts might be missing? What questions are not asked?
4. SELECTION BIAS: Why was this story selected? What angle is emphasized?
5. NARRATIVE BIAS: Does it fit a pre-existing narrative? Hero/villain framing?

Return a JSON object with this exact structure:
{
  "framing_analysis": "2-3 sentence description of how the story is framed",
  "narrative_bias_score": <0-100>,
  "omission_bias_score": <0-100>,
  "language_bias_score": <0-100>,
  "dominant_perspective": "which viewpoint is centered",
  "missing_perspectives": ["perspective1", "perspective2"],
  "loaded_language_examples": ["example1", "example2"],
  "recommendations": ["recommendation1", "recommendation2"]
}

Be objective and specific. Cite exact phrases from the text."""

    user_prompt = f"""Source: {source}

Article:
{text[:1500]}

Provide your bias analysis as JSON:"""

    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        
        track_llm_call()  # Track emissions
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        content = getattr(response, "content", str(response)).strip()
        
        # Extract JSON from response - try multiple approaches
        import re
        
        # First, try to find a complete JSON object
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            # Clean up any markdown code blocks
            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)
            
            try:
                result = json.loads(json_str)
                
                # Validate and normalize
                return {
                    "framing_analysis": str(result.get("framing_analysis", ""))[:500],  # Limit length
                    "narrative_bias_score": float(result.get("narrative_bias_score", 0)),
                    "omission_bias_score": float(result.get("omission_bias_score", 0)),
                    "language_bias_score": float(result.get("language_bias_score", 0)),
                    "dominant_perspective": str(result.get("dominant_perspective", "unknown"))[:200],
                    "missing_perspectives": [str(p)[:100] for p in (result.get("missing_perspectives", []) or [])[:5]],
                    "loaded_language_examples": [str(e)[:100] for e in (result.get("loaded_language_examples", []) or [])[:5]],
                    "recommendations": [str(r)[:200] for r in (result.get("recommendations", []) or [])[:5]]
                }
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error in LLM response: {e}. Content: {json_str[:300]}")
                return _fallback_analysis(text)
        else:
            logger.warning(f"Could not extract JSON from LLM response: {content[:200]}")
            return _fallback_analysis(text)
            
    except Exception as e:
        logger.error(f"Advanced bias analysis failed: {e}")
        return _fallback_analysis(text)


def _fallback_analysis(text: str) -> Dict[str, Any]:
    """Fallback analysis when LLM is unavailable."""
    text_lower = text.lower()
    
    # Simple heuristics
    loaded_words = ['shocking', 'devastating', 'radical', 'extreme', 'outrageous', 'scandal']
    found_loaded = [w for w in loaded_words if w in text_lower]
    
    return {
        "framing_analysis": "Unable to perform deep analysis without LLM",
        "narrative_bias_score": min(50, len(found_loaded) * 10),
        "omission_bias_score": 50,  # Unknown
        "language_bias_score": min(50, len(found_loaded) * 15),
        "dominant_perspective": "unknown",
        "missing_perspectives": ["Unable to determine without LLM analysis"],
        "loaded_language_examples": found_loaded[:3],
        "recommendations": ["Use LLM-based analysis for better insights"]
    }


def compare_article_narratives(articles: List[Dict[str, Any]], llm=None) -> Dict[str, Any]:
    """
    Compare narratives across multiple articles to detect systemic bias patterns.
    
    Args:
        articles: List of article dicts
        llm: Language model instance
    
    Returns:
        Dict with comparative narrative analysis
    """
    if not articles or llm is None:
        return {
            "narrative_clusters": [],
            "consensus_points": [],
            "divergent_points": [],
            "overall_bias_pattern": "unknown"
        }
    
    # Create summary of all articles for comparison
    summaries = []
    for i, article in enumerate(articles[:10]):  # Limit to 10 for token efficiency
        summaries.append({
            "index": i,
            "source": article.get('source', 'unknown'),
            "title": article.get('title', ''),
            "excerpt": article.get('description', '')[:200]
        })
    
    system_prompt = """You are analyzing multiple news articles on the same topic to identify narrative patterns and bias.

Compare the articles and identify:
1. Common narrative threads (what all sources agree on)
2. Divergent narratives (how coverage differs)
3. Perspective gaps (what's consistently missing)
4. Bias patterns (systematic slant across sources)

Return JSON:
{
  "consensus_points": ["fact/point all agree on"],
  "divergent_narratives": [{"narrative": "description", "sources": ["source1"]}],
  "missing_perspectives": ["perspective not covered"],
  "bias_pattern": "left/right/state/corporate/balanced",
  "narrative_diversity_score": <0-100>
}"""

    user_prompt = f"""Articles to compare:

{json.dumps(summaries, indent=2)}

Provide comparative analysis as JSON:"""

    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        
        track_llm_call()  # Track emissions
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        content = getattr(response, "content", str(response)).strip()
        
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "consensus_points": result.get("consensus_points", []),
                "divergent_narratives": result.get("divergent_narratives", []),
                "missing_perspectives": result.get("missing_perspectives", []),
                "overall_bias_pattern": result.get("bias_pattern", "unknown"),
                "narrative_diversity_score": float(result.get("narrative_diversity_score", 50))
            }
        else:
            return _fallback_comparison()
            
    except Exception as e:
        logger.error(f"Narrative comparison failed: {e}")
        return _fallback_comparison()


def _fallback_comparison() -> Dict[str, Any]:
    """Fallback when LLM comparison fails."""
    return {
        "consensus_points": ["Unable to determine without LLM"],
        "divergent_narratives": [],
        "missing_perspectives": ["Analysis unavailable"],
        "overall_bias_pattern": "unknown",
        "narrative_diversity_score": 50
    }


def detect_framing_techniques(article: Dict[str, Any], llm=None) -> Dict[str, Any]:
    """
    Detect specific framing techniques used in an article.
    
    Returns:
        Dict with detected framing techniques and examples
    """
    text = f"{article.get('title', '')} {article.get('description', '')}"
    text_lower = text.lower()
    
    techniques = {
        "victim_framing": {
            "indicators": ["victim", "suffering", "helpless", "vulnerable", "innocent"],
            "detected": False,
            "examples": []
        },
        "hero_framing": {
            "indicators": ["brave", "courageous", "hero", "defender", "protector"],
            "detected": False,
            "examples": []
        },
        "villain_framing": {
            "indicators": ["aggressor", "perpetrator", "terrorist", "criminal", "evil"],
            "detected": False,
            "examples": []
        },
        "crisis_framing": {
            "indicators": ["crisis", "emergency", "catastrophe", "disaster", "urgent"],
            "detected": False,
            "examples": []
        },
        "conflict_framing": {
            "indicators": ["battle", "war", "fight", "clash", "confrontation"],
            "detected": False,
            "examples": []
        },
        "economic_framing": {
            "indicators": ["cost", "expense", "price", "economic", "financial"],
            "detected": False,
            "examples": []
        },
        "moral_framing": {
            "indicators": ["right", "wrong", "justice", "injustice", "ethical"],
            "detected": False,
            "examples": []
        }
    }
    
    # Detect techniques
    for technique, data in techniques.items():
        for indicator in data["indicators"]:
            if indicator in text_lower:
                data["detected"] = True
                # Find context
                import re
                pattern = rf'\b\w*{indicator}\w*\b[^.!?]*[.!?]'
                matches = re.findall(pattern, text, re.IGNORECASE)
                data["examples"].extend(matches[:2])
    
    detected_techniques = {
        name: data for name, data in techniques.items() if data["detected"]
    }
    
    return {
        "techniques_detected": list(detected_techniques.keys()),
        "technique_count": len(detected_techniques),
        "details": detected_techniques,
        "dominant_frame": max(detected_techniques.keys(), key=lambda k: len(detected_techniques[k]["examples"])) if detected_techniques else "neutral"
    }


def analyze_power_dynamics(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze how power dynamics are portrayed in the article.
    
    Returns:
        Dict with power dynamic analysis
    """
    text = article.get('description', '') + ' ' + article.get('title', '')
    text_lower = text.lower()
    
    # Identify power actors
    power_actors = {
        "government": ["government", "state", "administration", "officials", "authorities"],
        "corporate": ["corporation", "company", "business", "industry", "executives"],
        "military": ["military", "armed forces", "soldiers", "troops", "defense"],
        "citizens": ["citizens", "people", "public", "protesters", "activists"],
        "media": ["media", "press", "journalists", "reporters"],
        "international": ["UN", "international community", "foreign", "global"]
    }
    
    actor_mentions = {}
    for actor, keywords in power_actors.items():
        count = sum(text_lower.count(kw) for kw in keywords)
        if count > 0:
            actor_mentions[actor] = count
    
    # Analyze portrayal (active vs passive voice, agency)
    active_voice_patterns = [
        r'\b(government|state|officials?)\s+\w+ed\b',
        r'\b(citizens?|people|protesters?)\s+demanded?\b',
        r'\b(company|corporation)\s+announced?\b'
    ]
    
    import re
    active_voice_count = sum(len(re.findall(pattern, text_lower)) for pattern in active_voice_patterns)
    
    return {
        "actor_prominence": actor_mentions,
        "most_prominent_actor": max(actor_mentions.items(), key=lambda x: x[1])[0] if actor_mentions else "none",
        "active_voice_usage": active_voice_count,
        "power_balance": "top-down" if actor_mentions.get("government", 0) > actor_mentions.get("citizens", 0) else "bottom-up" if actor_mentions.get("citizens", 0) > 0 else "neutral"
    }
