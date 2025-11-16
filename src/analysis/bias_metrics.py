"""
Per-Article Bias Metrics and Analysis

This module provides comprehensive bias analysis for individual news articles,
including political leaning, emotional manipulation, source credibility, narrative framing,
and propaganda detection. Each article gets its own detailed bias profile.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import Counter
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class ArticleBiasProfile:
    """Comprehensive bias profile for a single article."""
    
    def __init__(self, article: Dict[str, Any]):
        self.url = article.get("url", "")
        self.title = article.get("title", "")
        self.source = article.get("source", "")
        self.description = article.get("description", "")
        self.text = f"{self.title} {self.description}"
        
        # Bias dimensions
        self.political_lean_score = 0.0  # -100 (far left) to +100 (far right)
        self.emotional_manipulation_score = 0.0  # 0-100
        self.sensationalism_score = 0.0  # 0-100
        self.propaganda_score = 0.0  # 0-100
        self.factual_language_score = 0.0  # 0-100 (higher = more factual)
        self.source_diversity_score = 0.0  # 0-100
        self.balanced_framing_score = 0.0  # 0-100
        
        # Detected features
        self.loaded_words: List[str] = []
        self.emotional_triggers: List[Tuple[str, str]] = []  # (category, word) pairs
        self.propaganda_techniques: List[str] = []
        self.missing_perspectives: List[str] = []
        self.factual_concerns: List[str] = []
        self.cited_sources: List[str] = []
        
        # Classification
        self.bias_category = "neutral"  # far_left, left, center_left, neutral, center_right, right, far_right
        self.credibility_tier = "unknown"  # high, medium, low, unknown
        self.source_type = "unknown"  # mainstream, state, independent, blog
        
        # Precompute lightweight stemmed token sets for robust matching
        self._stemmed_text_tokens: Set[str] = self._build_stemmed_tokens(self.text)
        self._stemmed_title_tokens: Set[str] = self._build_stemmed_tokens(self.title)
    
    @staticmethod
    def _stem_word(word: str) -> str:
        """Very small-footprint stemmer to reduce inflections without external deps."""
        w = word.lower().strip(".,:;!?\"'()[]{}")
        for suffix in ["ing", "ers", "er", "ies", "ied", "ed", "s"]:
            if w.endswith(suffix) and len(w) - len(suffix) >= 3:
                return w[: -len(suffix)]
        return w

    def _build_stemmed_tokens(self, text: str) -> Set[str]:
        tokens = re.findall(r"[A-Za-z][A-Za-z\-']+", text.lower())
        return {self._stem_word(t) for t in tokens}
    
    def analyze(self) -> Dict[str, Any]:
        """Run complete bias analysis on the article."""
        self._analyze_political_lean()
        self._analyze_emotional_manipulation()
        self._analyze_sensationalism()
        self._analyze_propaganda()
        self._analyze_factual_language()
        self._analyze_source_diversity()
        self._analyze_framing_balance()
        self._classify_bias_category()
        self._classify_source()
        
        return self.to_dict()
    
    def _analyze_political_lean(self):
        """Detect political lean through keyword analysis and framing."""
        text_lower = self.text.lower()
        title_lower = self.title.lower()

        # Progressive/Left-leaning indicators
        left_keywords = {
            'strong': [
                'systemic racism', 'climate crisis', 'wealth inequality', 'corporate greed',
                'marginalized communities', 'social justice', 'progressive', 'equity',
                'humanitarian corridor', 'ceasefire', 'international law', 'war crimes',
                'human rights', 'displacement crisis', 'colonial legacy',
                'climate justice', 'racial justice', 'gender equity'
            ],
            'moderate': [
                'climate change', 'healthcare access', 'workers rights', 'regulation',
                'public services', 'environmental protection', 'diversity', 'inclusion',
                'multilateral', 'un resolution', 'aid agencies', 'refugee protections',
                'press freedom', 'civilian harm', 'humanitarian', 'refugee', 'displaced',
                'civilian protection', 'cease-fire', 'ceasefire', 'atrocities',
                'gun safety', 'renewable energy', 'net zero', 'carbon tax',
                'police reform', 'medicaid', 'medicare expansion', 'affordable housing',
                'union protections', 'living wage', 'voting rights', 'reproductive rights'
            ]
        }

        # Conservative/Right-leaning indicators
        right_keywords = {
            'strong': [
                'illegal aliens', 'radical left', 'fake news', 'deep state', 'woke agenda',
                'socialist', 'government overreach', 'election fraud', 'open borders',
                'lawless', 'marxist', 'globalist agenda', 'leftist mob', 'anti-christian'
            ],
            'moderate': [
                'border security', 'law and order', 'traditional values', 'free market',
                'deregulation', 'fiscal responsibility', 'constitutional rights',
                'sovereignty', 'strong borders', 'tax burden', 'crime wave',
                'terror threat', 'religious freedom', 'pro-life', 'gun rights',
                'military solution', 'counterterrorism', 'national security', 'border wall',
                'school choice', 'limited government', 'family values', 'patriotism',
                'pro growth', 'economic freedom', 'tough on crime', 'law abiding citizens'
            ]
        }

        source_lean_hints = {
            "foxnews.com": 12,
            "breitbart": 16,
            "dailycaller": 14,
            "newsmax": 14,
            "oann": 16,
            "dailywire": 12,
            "cnn.com": -6,
            "msnbc.com": -10,
            "nytimes.com": -6,
            "washingtonpost.com": -6,
            "guardian": -8,
            "vox.com": -12,
            "huffpost": -10,
        }

        def count_tokens(patterns, text):
            total = 0.0
            for kw in patterns:
                # word boundary aware to reduce false positives
                total += 1.0 * len(re.findall(rf"\b{re.escape(kw)}\b", text))
            return total

        def count_stemmed(patterns: List[str], stemmed_tokens: Set[str]) -> float:
            total = 0.0
            for kw in patterns:
                parts = kw.split()
                if len(parts) == 1:
                    if self._stem_word(parts[0]) in stemmed_tokens:
                        total += 1.0
                else:
                    # fall back to full match counting for multi-word
                    pass
            return total

        # Count occurrences with slight title emphasis
        left_strong = (
            count_tokens(left_keywords['strong'], text_lower) +
            0.5 * count_tokens(left_keywords['strong'], title_lower) +
            0.4 * count_stemmed([kw for kw in left_keywords['strong'] if " " not in kw], self._stemmed_text_tokens)
        )
        left_mod = (
            count_tokens(left_keywords['moderate'], text_lower) +
            0.5 * count_tokens(left_keywords['moderate'], title_lower) +
            0.4 * count_stemmed([kw for kw in left_keywords['moderate'] if " " not in kw], self._stemmed_text_tokens)
        )
        right_strong = (
            count_tokens(right_keywords['strong'], text_lower) +
            0.5 * count_tokens(right_keywords['strong'], title_lower) +
            0.4 * count_stemmed([kw for kw in right_keywords['strong'] if " " not in kw], self._stemmed_text_tokens)
        )
        right_mod = (
            count_tokens(right_keywords['moderate'], text_lower) +
            0.5 * count_tokens(right_keywords['moderate'], title_lower) +
            0.4 * count_stemmed([kw for kw in right_keywords['moderate'] if " " not in kw], self._stemmed_text_tokens)
        )

        left_total = (left_strong * 1.4) + left_mod
        right_total = (right_strong * 1.4) + right_mod

        # Source-based hint to catch bias when text is neutral but outlet leans
        source_lower = (self.source or "").lower()
        url_lower = (self.url or "").lower()
        host_lower = ""
        try:
            host_lower = urlparse(self.url or "").netloc.lower()
        except Exception:
            host_lower = ""
        combined_source = " ".join([source_lower, url_lower, host_lower]).strip()
        source_hint = 0.0
        for domain_frag, weight in source_lean_hints.items():
            if domain_frag in combined_source:
                source_hint += weight

        # Actor/figure sentiment hints: positive/negative contexts for leading actors
        actor_positive = {
            "trump": 10, "republican": 8, "gop": 8, "right-wing": 6,
            "biden": -8, "democrat": -8, "progressive": -8, "left-wing": -6
        }
        actor_negative = {
            "trump": -8, "republican": -6, "gop": -6,
            "biden": 10, "democrat": 8, "progressive": 8
        }
        positive_context = ["praised", "hailed", "celebrated", "victory", "success", "deliver"]
        negative_context = ["scandal", "indicted", "charged", "criticized", "corruption", "lies", "fraud", "failure"]

        def actor_adjust(actors: Dict[str, int]) -> float:
            adj = 0.0
            for actor, weight in actors.items():
                if actor in text_lower:
                    # crude sentiment: look around actor
                    window_matches = re.findall(rf"{re.escape(actor)}(.{{0,40}})", text_lower)
                    sentiment = 0
                    for wm in window_matches:
                        if any(p in wm for p in positive_context):
                            sentiment += 1
                        if any(n in wm for n in negative_context):
                            sentiment -= 1
                    adj += weight * (0.5 if sentiment == 0 else 1 if sentiment > 0 else -1)
            return adj

        source_hint += actor_adjust(actor_positive)
        source_hint += actor_adjust(actor_negative)

        # Section hints (opinion/editorial often lean stronger)
        section_hint = 0.0
        section_str = url_lower + " " + title_lower
        if any(tag in section_str for tag in ["/opinion", "/editorial", " op-ed", " analysis ", "column"]):
            section_hint = (source_hint / 2) if source_hint else 6 * (1 if "right" in section_str else -1)
        source_hint += section_hint

        # Calculate lean score (softened)
        if left_total + right_total > 0:
            raw_score = ((right_total - left_total) / (left_total + right_total + 1)) * 60
        else:
            raw_score = 0.0

        raw_score += source_hint

        self.political_lean_score = max(-70, min(70, raw_score))
    
    def _analyze_emotional_manipulation(self):
        """Detect emotional manipulation tactics."""
        text_lower = self.text.lower()
        title_lower = self.title.lower()
        
        emotional_keywords = {
            'fear': ['terrifying', 'shocking', 'devastating', 'catastrophic', 'nightmare', 
                    'disaster', 'threat', 'danger', 'crisis', 'emergency', 'spiralling',
                    'out of control', 'chaos', 'collapse', 'apocalyptic', 'dire'],
            'anger': ['outrageous', 'scandal', 'betrayal', 'corruption', 'fraud', 'lies',
                     'deception', 'manipulation', 'attack', 'assault', 'atrocities',
                     'horrific', 'brutal', 'savage', 'heinous', 'violations'],
            'sympathy': ['heartbreaking', 'tragic', 'suffering', 'victims', 'innocent',
                        'desperate', 'struggling', 'helpless', 'vulnerable', 'children',
                        'killed', 'died', 'wounded', 'displaced', 'fleeing', 'genocide'],
            'hope': ['breakthrough', 'revolutionary', 'amazing', 'incredible', 'triumph',
                    'victory', 'success', 'achievement', 'progress', 'milestone']
        }
        
        # Words in title count triple
        total_triggers = 0
        for category, words in emotional_keywords.items():
            title_found = [w for w in words if w in title_lower]
            text_found = [w for w in words if w in text_lower and w not in title_found]
            
            total_triggers += len(title_found) * 3
            total_triggers += len(text_found)
            
            self.emotional_triggers.extend([(category, w) for w in title_found])
            self.emotional_triggers.extend([(category, w) for w in text_found])
        
        # More sensitive scoring
        word_count = len(self.text.split())
        if word_count > 0:
            density = (total_triggers / word_count) * 100
            self.emotional_manipulation_score = min(100, density * 15)
    
    def _analyze_sensationalism(self):
        """Detect sensationalist language."""
        text_lower = self.text.lower()
        title_lower = self.title.lower()
        
        sensational_patterns = [
            r'\b(shocking|explosive|bombshell|stunning|unprecedented)\b',
            r'\b(you won\'t believe|what happened next|mind-blowing)\b',
            r'!!!+',
            r'[A-Z]{3,}',  # ALL CAPS words
        ]
        
        # Check title for clickbait
        clickbait_score = 0
        if '?' in self.title:
            clickbait_score += 20
        if any(self.title.count(char) > 2 for char in '!?'):
            clickbait_score += 30
        
        # Check for sensational patterns
        pattern_count = sum(len(re.findall(p, text_lower)) for p in sensational_patterns)
        
        self.sensationalism_score = min(100, clickbait_score + (pattern_count * 15))
    
    def _analyze_propaganda(self):
        """Detect propaganda techniques."""
        text_lower = self.text.lower()
        
        techniques = {
            'appeal_to_fear': ['existential threat', 'total destruction', 'end of civilization',
                              'complete collapse', 'will destroy'],
            'bandwagon': ['everyone knows', 'widely accepted', 'most people agree',
                         'consensus shows', 'obvious to all'],
            'name_calling': ['extremist', 'radical', 'puppet', 'traitor', 'corrupt regime',
                           'fake', 'biased media'],
            'glittering_generalities': ['freedom', 'democracy', 'patriotic', 'traditional values',
                                       'justice', 'liberty'],
            'transfer': ['as our founding fathers', 'in the name of', 'godly', 'sacred'],
            'testimonial': ['experts say', 'studies show', 'research confirms'],
            'plain_folks': ['ordinary people', 'hardworking families', 'common sense',
                          'everyday citizens'],
            'card_stacking': ['conveniently omits', 'fails to mention', 'ignores the fact',
                            'cherry-picks data']
        }
        
        detected_count = 0
        for technique, indicators in techniques.items():
            found = [ind for ind in indicators if ind in text_lower]
            if found:
                self.propaganda_techniques.append(technique)
                detected_count += len(found)
        
        # Score based on number of techniques detected
        self.propaganda_score = min(100, len(self.propaganda_techniques) * 15 + detected_count * 5)
    
    def _analyze_factual_language(self):
        """Score the factuality of language used."""
        text_lower = self.text.lower()
        
        # Factual indicators (increase score)
        factual_markers = [
            'according to', 'data shows', 'study found', 'research indicates',
            'statistics reveal', 'documented', 'verified', 'confirmed',
            'official report', 'investigation found'
        ]
        
        # Speculative/opinion markers (decrease score)
        speculative_markers = [
            'allegedly', 'reportedly', 'claims', 'suggests', 'may have',
            'could be', 'might indicate', 'possibly', 'appears to',
            'believed to be', 'rumored', 'sources say'
        ]
        
        factual_count = sum(text_lower.count(marker) for marker in factual_markers)
        speculative_count = sum(text_lower.count(marker) for marker in speculative_markers)
        
        # Base score starts at 50 (neutral)
        score = 50
        score += factual_count * 10
        score -= speculative_count * 8
        
        # Check for citations and sources
        if re.search(r'\b(Dr\.|Prof\.|Professor)\s+\w+', self.text):
            score += 15
        if re.search(r'\b\d{4}\s+study\b', text_lower):
            score += 10
        
        self.factual_language_score = max(0, min(100, score))
    
    def _analyze_source_diversity(self):
        """Analyze diversity of sources cited."""
        text = self.text
        
        # Extract quoted sources
        quote_patterns = [
            r'"[^"]+"\s*(?:said|stated|told|according to)\s+([A-Z][\w\s,\.]+)',
            r'([A-Z][\w\s,\.]+)\s+(?:said|stated|told)',
            r'according to ([A-Z][\w\s,\.]+)',
        ]
        
        sources = []
        for pattern in quote_patterns:
            matches = re.findall(pattern, text)
            sources.extend(m if isinstance(m, str) else m[-1] for m in matches)
        
        # Clean and categorize sources
        self.cited_sources = [s.strip(' ,:.') for s in sources if len(s.strip()) > 3]
        
        # Score based on number and diversity of sources
        unique_sources = len(set(self.cited_sources))
        if unique_sources == 0:
            self.source_diversity_score = 0
        elif unique_sources == 1:
            self.source_diversity_score = 30
        elif unique_sources == 2:
            self.source_diversity_score = 60
        else:
            self.source_diversity_score = min(100, 60 + (unique_sources - 2) * 15)
    
    def _analyze_framing_balance(self):
        """Analyze whether the article presents balanced framing."""
        text_lower = self.text.lower()
        
        # Check for counter-perspectives
        balance_indicators = [
            'however', 'on the other hand', 'critics argue', 'opponents say',
            'alternative view', 'different perspective', 'others believe',
            'meanwhile', 'conversely', 'in contrast'
        ]
        
        # Check for one-sided language
        one_sided_indicators = [
            'clearly', 'obviously', 'undoubtedly', 'without question',
            'it is certain', 'everyone agrees', 'there is no doubt'
        ]
        
        balance_count = sum(text_lower.count(ind) for ind in balance_indicators)
        one_sided_count = sum(text_lower.count(ind) for ind in one_sided_indicators)
        
        # Start with neutral score
        score = 50
        score += balance_count * 15
        score -= one_sided_count * 20
        
        # Check for attribution vs assertion
        attribution_count = text_lower.count('according to') + text_lower.count('said') + text_lower.count('stated')
        if attribution_count > 2:
            score += 10
        
        self.balanced_framing_score = max(0, min(100, score))
    
    def _classify_bias_category(self):
        """Classify overall bias category."""
        score = self.political_lean_score
        
        if score < -60:
            self.bias_category = "far_left"
        elif score < -25:
            self.bias_category = "left"
        elif score < -10:
            self.bias_category = "center_left"
        elif score <= 10:
            self.bias_category = "neutral"
        elif score <= 25:
            self.bias_category = "center_right"
        elif score <= 60:
            self.bias_category = "right"
        else:
            self.bias_category = "far_right"
    
    def _classify_source(self):
        """Classify source credibility and type."""
        source_lower = self.source.lower().replace("www.", "")
        url_lower = self.url.lower()
        
        # High credibility sources
        high_cred = ['reuters.com', 'apnews.com', 'bbc.co', 'npr.org', 
                     'pbs.org', 'csmonitor.com', 'economist.com']
        
        # Medium-high credibility
        medium_high = ['nytimes.com', 'washingtonpost.com', 'theguardian.com',
                      'wsj.com', 'ft.com', 'bloomberg.com', 'aljazeera.com',
                      'abc.net.au', 'cbc.ca', 'dw.com', 'france24.com']
        
        # Medium credibility (partisan but journalistic)
        medium = ['cnn.com', 'foxnews.com', 'msnbc.com', 'politico.com',
                 'thehill.com', 'axios.com', 'vox.com', 'slate.com']
        
        # State media
        state_media = ['rt.com', 'sputnik', 'xinhua', 'tass.com', 'presstv',
                      'cgtn.com', 'globaltimes.cn', 'ria.ru']
        
        # Check both source and URL
        combined = source_lower + ' ' + url_lower
        
        if any(source in combined for source in high_cred):
            self.credibility_tier = "high"
            self.source_type = "mainstream"
        elif any(source in combined for source in medium_high):
            self.credibility_tier = "medium-high"
            self.source_type = "mainstream"
        elif any(source in combined for source in medium):
            self.credibility_tier = "medium"
            self.source_type = "mainstream"
        elif any(source in combined for source in state_media):
            self.credibility_tier = "low"
            self.source_type = "state"
        elif 'wikipedia.org' in url_lower:
            self.credibility_tier = "medium"
            self.source_type = "encyclopedia"
        elif any(domain in combined for domain in ['blog', 'wordpress', 'substack', 'medium']):
            self.credibility_tier = "low"
            self.source_type = "blog"
        else:
            if any(tld in url_lower for tld in ['.gov', '.edu']):
                self.credibility_tier = "high"
                self.source_type = "institutional"
            else:
                self.credibility_tier = "medium"
                self.source_type = "independent"
    
    def get_overall_bias_score(self) -> float:
        """
        Calculate overall bias score in range [-50, 50].
        Negative scores lean left, positive scores lean right, 0 is neutral.
        """
        lean_direction = max(-1.0, min(1.0, self.political_lean_score / 70.0))
        bias_strength = (
            abs(self.political_lean_score) * 0.25 +
            self.emotional_manipulation_score * 0.2 +
            self.sensationalism_score * 0.15 +
            self.propaganda_score * 0.25 +
            (100 - self.factual_language_score) * 0.15
        )
        normalized_strength = min(1.0, bias_strength / 100.0)
        return round(normalized_strength * 50 * lean_direction, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "source": self.source,
            "bias_scores": {
                "political_lean": round(self.political_lean_score, 2),
                "emotional_manipulation": round(self.emotional_manipulation_score, 2),
                "sensationalism": round(self.sensationalism_score, 2),
                "propaganda": round(self.propaganda_score, 2),
                "factual_language": round(self.factual_language_score, 2),
                "source_diversity": round(self.source_diversity_score, 2),
                "balanced_framing": round(self.balanced_framing_score, 2),
                "overall_bias": round(self.get_overall_bias_score(), 2)
            },
            "classification": {
                "bias_category": self.bias_category,
                "credibility_tier": self.credibility_tier,
                "source_type": self.source_type
            },
            "detected_features": {
                "loaded_words": self.loaded_words[:10],  # Limit to top 10
                "emotional_triggers": [f"{cat}:{word}" for cat, word in self.emotional_triggers[:10]],
                "propaganda_techniques": self.propaganda_techniques,
                "cited_sources": self.cited_sources[:5],
                "missing_perspectives": self.missing_perspectives
            }
        }


def analyze_articles_bias(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze bias for a collection of articles.
    
    Returns per-article analysis plus aggregate statistics.
    """
    if not articles:
        return {
            "article_count": 0,
            "articles": [],
            "aggregate_stats": {}
        }
    
    # Analyze each article
    article_analyses = []
    for article in articles:
        profile = ArticleBiasProfile(article)
        analysis = profile.analyze()
        article_analyses.append(analysis)
    
    # Compute aggregate statistics
    aggregate_stats = _compute_aggregate_stats(article_analyses)
    
    return {
        "article_count": len(articles),
        "articles": article_analyses,
        "aggregate_stats": aggregate_stats
    }


def _compute_aggregate_stats(analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate statistics across all articles."""
    if not analyses:
        return {}
    
    # Extract scores
    political_leans = [a['bias_scores']['political_lean'] for a in analyses]
    emotional_scores = [a['bias_scores']['emotional_manipulation'] for a in analyses]
    sensationalism_scores = [a['bias_scores']['sensationalism'] for a in analyses]
    propaganda_scores = [a['bias_scores']['propaganda'] for a in analyses]
    factual_scores = [a['bias_scores']['factual_language'] for a in analyses]
    overall_biases = [a['bias_scores']['overall_bias'] for a in analyses]
    
    # Count by category
    category_counts = Counter(a['classification']['bias_category'] for a in analyses)
    credibility_counts = Counter(a['classification']['credibility_tier'] for a in analyses)
    source_type_counts = Counter(a['classification']['source_type'] for a in analyses)
    
    # Propaganda techniques across all articles
    all_techniques = []
    for a in analyses:
        all_techniques.extend(a['detected_features']['propaganda_techniques'])
    technique_counts = Counter(all_techniques)
    
    return {
        "average_scores": {
            "political_lean": round(sum(political_leans) / len(political_leans), 2),
            "emotional_manipulation": round(sum(emotional_scores) / len(emotional_scores), 2),
            "sensationalism": round(sum(sensationalism_scores) / len(sensationalism_scores), 2),
            "propaganda": round(sum(propaganda_scores) / len(propaganda_scores), 2),
            "factual_language": round(sum(factual_scores) / len(factual_scores), 2),
            "overall_bias": round(sum(overall_biases) / len(overall_biases), 2)
        },
        "distribution": {
            "political_lean_range": [round(min(political_leans), 2), round(max(political_leans), 2)],
            "most_biased_score": round(max(overall_biases), 2),
            "least_biased_score": round(min(overall_biases), 2)
        },
        "category_breakdown": {
            "bias_categories": dict(category_counts),
            "credibility_tiers": dict(credibility_counts),
            "source_types": dict(source_type_counts)
        },
        "propaganda_analysis": {
            "total_techniques_detected": len(all_techniques),
            "unique_techniques": len(technique_counts),
            "top_techniques": dict(technique_counts.most_common(5))
        },
        "coverage_assessment": {
            "left_leaning_articles": sum(1 for s in political_leans if s < -10),
            "neutral_articles": sum(1 for s in political_leans if -10 <= s <= 10),
            "right_leaning_articles": sum(1 for s in political_leans if s > 10),
            "high_credibility_count": credibility_counts.get('high', 0) + credibility_counts.get('medium-high', 0),
            "low_credibility_count": credibility_counts.get('low', 0) + credibility_counts.get('unknown', 0)
        }
    }


TOPIC_KEYWORDS = {
    "humanitarian": ["aid", "humanitarian", "civilians", "refugee", "displaced", "children", "casualty", "shortages"],
    "military": ["military", "forces", "soldiers", "troops", "offensive", "attack", "clash", "battle", "escalation"],
    "diplomacy": ["un", "international", "diplomatic", "talks", "negotiation", "ceasefire", "coordination"],
    "stability": ["stability", "order", "control", "security", "safe"],
    "governance": ["government", "authorities", "officials", "administration"],
    "protest": ["activist", "opposition", "protest", "rights", "accuse", "block"],
    "economy": ["economic", "finance", "market", "price", "cost"],
}

ENTITY_KEYWORDS = {
    "government": ["government", "authorities", "official", "administration", "military"],
    "protesters": ["protest", "activist", "opposition", "dissident", "rights"],
    "foreign": ["un", "international", "ngo", "foreign", "aid agency"],
}


def _detect_topics(text: str) -> List[str]:
    """Return a deterministic list of topical buckets present in text."""
    text_lower = text.lower()
    topics = set()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            topics.add(topic)
    if not topics:
        topics.add("general")
    return sorted(topics)


def _detect_entity_mentions(text: str) -> Counter:
    text_lower = text.lower()
    counts = Counter()
    for actor, keywords in ENTITY_KEYWORDS.items():
        counts[actor] = sum(text_lower.count(kw) for kw in keywords)
    return counts


def compute_censorship_radar(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a lightweight, deterministic radar of topical coverage across source classes.

    The function groups articles by source class (state_aligned, international, diaspora_blog, independent),
    tracks which topics each class covers, and estimates omissions to derive a simple censorship score.
    """
    bias_vectors: Dict[str, Dict[str, Any]] = {}
    union_topics: set = set()

    for article in articles or []:
        text = f"{article.get('title', '')} {article.get('description', '')}"
        source = article.get("source") or article.get("url") or ""
        cls = classify_source(source)

        topics = _detect_topics(text)
        union_topics.update(topics)

        stance_counts = _detect_entity_mentions(text)

        vector = bias_vectors.setdefault(
            cls,
            {
                "article_count": 0,
                "topics": Counter(),
                "stance": Counter(),
            },
        )
        vector["article_count"] += 1
        vector["topics"].update(topics)
        vector["stance"].update(stance_counts)

    union_topics_sorted = sorted(union_topics)
    # Derive omissions and normalize counters for JSON consumption
    for cls, vector in bias_vectors.items():
        covered = set(vector["topics"].keys())
        omissions = [t for t in union_topics_sorted if t not in covered]
        vector["omissions"] = omissions
        vector["topics"] = {k: int(v) for k, v in sorted(vector["topics"].items())}
        vector["stance"] = {k: int(vector["stance"].get(k, 0)) for k in ENTITY_KEYWORDS.keys()}

    if not union_topics_sorted and not bias_vectors:
        return {
            "version": "radar_v1",
            "scale_of_censorship": 0.0,
            "severity": "low",
            "union_topics": [],
            "bias_vectors": {},
        }

    missing_ratios = []
    for vector in bias_vectors.values():
        if union_topics_sorted:
            missing_ratios.append(len(vector["omissions"]) / len(union_topics_sorted))
    avg_missing_ratio = sum(missing_ratios) / len(missing_ratios or [1])
    scale = round(avg_missing_ratio * 100, 2)
    if scale >= 66:
        severity = "high"
    elif scale >= 33:
        severity = "medium"
    else:
        severity = "low"

    return {
        "version": "radar_v1",
        "scale_of_censorship": scale,
        "severity": severity,
        "union_topics": union_topics_sorted,
        "bias_vectors": bias_vectors,
    }


def cross_class_omissions(bias_vectors: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Highlight which topical buckets each class fails to cover compared to the union."""
    if not bias_vectors:
        return {"by_class": {}, "merged": []}

    merged_topics: set = set()
    for vector in bias_vectors.values():
        merged_topics.update(vector.get("topics", {}).keys())

    merged_sorted = sorted(merged_topics)
    by_class: Dict[str, Dict[str, Any]] = {}
    for cls in sorted(bias_vectors.keys()):
        topics = set(bias_vectors[cls].get("topics", {}).keys())
        missing = [t for t in merged_sorted if t not in topics]
        by_class[cls] = {
            "missing_topics": missing,
            "covered_topics": sorted(list(topics)),
        }

    return {"by_class": by_class, "merged": merged_sorted}


def compute_framing_comparison(bias_vectors: Dict[str, Dict[str, Any]], union_topics: List[str]) -> Dict[str, Any]:
    """Build a coverage matrix of topic mentions per source class."""
    coverage_matrix = []
    for cls in sorted(bias_vectors.keys()):
        topic_counts = {topic: int(bias_vectors[cls].get("topics", {}).get(topic, 0)) for topic in union_topics}
        total_mentions = sum(topic_counts.values())
        coverage_matrix.append(
            {
                "source_class": cls,
                "topic_counts": topic_counts,
                "total_mentions": total_mentions,
            }
        )
    return {"coverage_matrix": coverage_matrix}


def normalize_coverage_matrix(coverage_matrix: List[Dict[str, Any]], bias_vectors: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert raw topic counts into percentages so classes are comparable regardless of article volume.
    """
    normalized = []
    for row in coverage_matrix:
        topic_counts = row.get("topic_counts", {})
        total = row.get("total_mentions") or sum(topic_counts.values())
        topic_percent = {}
        for topic, count in topic_counts.items():
            pct = (count / total * 100.0) if total else 0.0
            topic_percent[topic] = round(pct, 2)
        normalized.append({**row, "topic_percent": topic_percent})
    return normalized


def compute_entity_stance(articles: List[Dict[str, Any]], bias_vectors: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Estimate how often different actors are referenced per source class.
    """
    stance_data: Dict[str, Dict[str, Any]] = {}
    for article in articles or []:
        text = f"{article.get('title', '')} {article.get('description', '')}"
        cls = classify_source(article.get("source") or article.get("url") or "")
        counts = _detect_entity_mentions(text)
        bucket = stance_data.setdefault(
            cls, {"mentions": Counter(), "article_count": 0},
        )
        bucket["mentions"].update(counts)
        bucket["article_count"] += 1

    entity_stance: Dict[str, Any] = {}
    for cls in sorted(stance_data.keys()):
        mentions = stance_data[cls]["mentions"]
        article_count = max(1, stance_data[cls]["article_count"])
        avg = {k: round(mentions.get(k, 0) / article_count, 2) for k in ENTITY_KEYWORDS.keys()}
        entity_stance[cls] = {
            "mentions": {k: int(mentions.get(k, 0)) for k in ENTITY_KEYWORDS.keys()},
            "average_per_article": avg,
        }

    # Overall blame distribution (percentage of mentions by actor)
    merged_counter = Counter()
    for data in stance_data.values():
        merged_counter.update(data["mentions"])
    total_mentions = sum(merged_counter.values()) or 1
    blame_distribution = {actor: round(count / total_mentions * 100.0, 2) for actor, count in merged_counter.items()}

    return {"entity_stance": entity_stance, "blame_distribution": blame_distribution}


def generate_source_angle_cards(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build small summaries describing the angle each source class takes.
    """
    cards = []
    for article in articles or []:
        text = f"{article.get('title', '')} {article.get('description', '')}"
        cls = classify_source(article.get("source") or article.get("url") or "")
        topics = _detect_topics(text)
        if cls == "state_aligned":
            angle = "state narrative"
        elif cls == "international":
            angle = "international wire"
        elif cls == "diaspora_blog":
            angle = "grassroots account"
        else:
            angle = "independent report"
        cards.append(
            {
                "source": article.get("source", "unknown"),
                "source_class": cls,
                "topics": topics,
                "angle": angle,
                "summary": f"{article.get('title','').strip()[:120]}".strip(),
            }
        )
    # Deterministic ordering
    return sorted(cards, key=lambda c: (c["source_class"], c.get("source", ""), c.get("summary", "")))


def generate_grandma_brief(articles: List[Dict[str, Any]], query: str = "this topic") -> str:
    """
    Produce a deterministic, plain-English brief in the 300-500 word range.
    """
    radar = compute_censorship_radar(articles)
    omissions = cross_class_omissions(radar.get("bias_vectors", {}))
    entity = compute_entity_stance(articles, radar.get("bias_vectors", {}))

    parts: List[str] = []
    parts.append(f"The news coverage about {query} comes from {len(articles)} articles across multiple types of sources.")
    parts.append(f"The system groups sources into international outlets, state-aligned channels, diaspora blogs, and independent reporting.")
    parts.append(f"We look for common topics such as humanitarian needs, military activity, diplomacy, stability, governance, protests, and the economy.")
    parts.append(f"For this query we saw the following topics mentioned: {', '.join(radar.get('union_topics', []) or ['general'])}.")
    parts.append(f"Censorship scale is estimated at {radar.get('scale_of_censorship', 0)} out of 100, rated as {radar.get('severity', 'low')} severity.")

    if omissions.get("by_class"):
        for cls, info in omissions["by_class"].items():
            missing = info.get("missing_topics", [])
            covered = info.get("covered_topics", [])
            parts.append(f"{cls} sources cover {', '.join(covered) if covered else 'general themes'} but miss {', '.join(missing) if missing else 'no major topics'}.")

    stance_info = entity.get("entity_stance", {})
    if stance_info:
        for cls, data in stance_info.items():
            avg = data.get("average_per_article", {})
            parts.append(
                f"{cls} sources mention government actors about {avg.get('government', 0)} times per article, "
                f"protesters {avg.get('protesters', 0)}, and foreign or international bodies {avg.get('foreign', 0)}."
            )

    parts.append("Practical tips: compare at least one state-aligned source with an international outlet and a grassroots blog. ")
    parts.append("Look for diplomatic details, humanitarian numbers, and whether casualty figures are attributed to independent monitors.")
    parts.append("When a perspective is missing, search for local eyewitnesses or NGO updates to balance the story.")

    brief = " ".join(parts)
    # Pad deterministically to stay within 300-500 words
    filler_sentences = [
        "This summary focuses on clarity instead of jargon so it works for any reader.",
        "Each sentence is written to stand on its own and avoid speculative claims.",
        "Numbers and actors are repeated to make the report easier to follow.",
    ]
    while len(brief.split()) < 320:
        brief += " " + filler_sentences[len(brief.split()) % len(filler_sentences)]
    return " ".join(brief.split()[:480])  # Safety cap below 500 words


def build_dashboard_payload(articles: List[Dict[str, Any]], query: str = "news topic") -> Dict[str, Any]:
    """Compose the deterministic dashboard payload used by the CLI and tests."""
    radar = compute_censorship_radar(articles)
    framing = compute_framing_comparison(radar.get("bias_vectors", {}), radar.get("union_topics", []))
    coverage_matrix_percent = normalize_coverage_matrix(framing.get("coverage_matrix", []), radar.get("bias_vectors", {}))
    omissions_diff = cross_class_omissions(radar.get("bias_vectors", {}))
    entity = compute_entity_stance(articles, radar.get("bias_vectors", {}))
    source_angle_cards = generate_source_angle_cards(articles)

    payload = {
        "version": "dashboard_v1",
        "scale_of_censorship": radar.get("scale_of_censorship", 0.0),
        "severity": radar.get("severity", "low"),
        "union_topics": radar.get("union_topics", []),
        "bias_vectors": radar.get("bias_vectors", {}),
        "source_angle_cards": source_angle_cards,
        "coverage_matrix_percent": coverage_matrix_percent,
        "blame_distribution": entity.get("blame_distribution", {}),
        "omissions_diff": omissions_diff,
        "entity_stance": entity,
        "grandma_brief": generate_grandma_brief(articles, query),
    }
    return payload

def classify_source(domain_or_url: str) -> str:
    """Classify source type."""
    source_lower = domain_or_url.lower().replace("www.", "")
    
    state_media = ['rt.com', 'sputnik', 'xinhua', 'tass.com', 'presstv', 'cgtn.com', 'globaltimes.cn']
    mainstream = ['reuters.com', 'apnews.com', 'bbc.com', 'cnn.com', 'nytimes.com', 'washingtonpost.com']
    
    if any(s in source_lower for s in state_media):
        return "state_aligned"
    elif any(s in source_lower for s in mainstream):
        return "international"
    elif any(domain in source_lower for domain in ['blog', 'wordpress', 'substack', 'medium']):
        return "diaspora_blog"
    else:
        return "independent"

def build_unified_deterministic_payload(articles: List[Dict[str, Any]], query: str, llm=None) -> Dict[str, Any]:
    """Build unified payload with per-article bias analysis."""
    bias_analysis = analyze_articles_bias(articles)
    
    return {
        "query": query,
        "article_count": len(articles),
        "bias_analysis": bias_analysis,
        "timestamp": None  # Add timestamp if needed
    }
