#!/usr/bin/env python3
"""
Test script for enhanced bias detection features
"""

import json
import requests

def test_enhanced_bias():
    """Test the enhanced bias detection with a real query."""
    print("🧪 Testing Enhanced Bias Detection Features\n")
    print("=" * 70)
    
    # Make API request
    url = "http://localhost:5001/api/analyze"
    payload = {
        "query": "climate change policy",
        "max_results": 5,
        "search_type": "web",
        "response_length": "medium",
        "enable_advanced": False
    }
    
    print(f"📡 Sending request to: {url}")
    print(f"📋 Query: {payload['query']}\n")
    
    response = requests.post(url, json=payload, timeout=60)
    
    if response.status_code != 200:
        print(f"❌ Error: API returned status {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    bias_analysis = data.get('bias_analysis', {})
    articles = bias_analysis.get('articles', [])
    
    if not articles:
        print("❌ No articles in response")
        return
    
    print(f"✅ Received analysis for {len(articles)} articles!\n")
    print("=" * 70)
    
    # Display enhanced features for each article
    for i, article in enumerate(articles[:3], 1):  # Show first 3
        print(f"\n📰 Article {i}: {article.get('title', 'Untitled')[:60]}...")
        print(f"   Source: {article.get('source', 'Unknown')}")
        
        enhanced = article.get('enhanced_analysis', {})
        
        if enhanced:
            print(f"\n   🔍 Enhanced Analysis:")
            
            # Content type
            content_type = enhanced.get('content_type', 'unknown')
            print(f"      Content Type: {content_type}")
            
            # Topic category
            topic = enhanced.get('topic_category', 'unknown')
            print(f"      Topic Category: {topic}")
            
            # Political lean confidence
            confidence = enhanced.get('political_lean_confidence', 0.0)
            print(f"      Political Lean Confidence: {confidence:.2f}")
            
            # Sentiment analysis
            sentiment = enhanced.get('sentiment_analysis', {})
            if sentiment and sentiment.get('textblob_available'):
                polarity = sentiment.get('polarity', 0.0)
                subjectivity = sentiment.get('subjectivity', 0.0)
                sentiment_label = sentiment.get('sentiment_label', 'neutral')
                print(f"\n      📊 Sentiment:")
                print(f"         Polarity: {polarity:+.3f} ({sentiment_label})")
                print(f"         Subjectivity: {subjectivity:.3f}")
                
                emotional_cats = sentiment.get('emotional_categories', {})
                if emotional_cats:
                    print(f"         Emotional Categories: {list(emotional_cats.keys())}")
            
            # Framing analysis
            framing = enhanced.get('framing_analysis', {})
            if framing:
                dominant_frame = framing.get('dominant_frame', 'neutral')
                framing_diversity = framing.get('framing_diversity', 0)
                balance_score = framing.get('framing_balance_score', 0.0)
                
                print(f"\n      🎭 Framing:")
                print(f"         Dominant Frame: {dominant_frame}")
                print(f"         Frame Diversity: {framing_diversity}/8")
                print(f"         Balance Score: {balance_score:.2f}")
            
            # Keyword analysis
            keywords = enhanced.get('keyword_analysis', {})
            if keywords:
                left_total = keywords.get('left_keywords_total', 0)
                right_total = keywords.get('right_keywords_total', 0)
                keyword_confidence = keywords.get('keyword_confidence', 0.0)
                
                print(f"\n      🔑 Keywords:")
                print(f"         Left-leaning: {left_total}")
                print(f"         Right-leaning: {right_total}")
                print(f"         Confidence: {keyword_confidence:.2f}")
            
            # Contributing factors
            factors = enhanced.get('lean_contributing_factors', {})
            if factors:
                print(f"\n      ⚖️  Political Lean Factors:")
                for factor, value in factors.items():
                    print(f"         {factor.capitalize()}: {value:+.2f}")
        
        print("\n" + "-" * 70)
    
    # Aggregate statistics
    aggregate = bias_analysis.get('aggregate_stats', {})
    if aggregate:
        print(f"\n📊 Aggregate Statistics:")
        
        avg_scores = aggregate.get('average_scores', {})
        if avg_scores:
            print(f"\n   Average Scores:")
            for metric, value in avg_scores.items():
                print(f"      {metric.replace('_', ' ').title()}: {value:.2f}")
        
        coverage = aggregate.get('coverage_assessment', {})
        if coverage:
            print(f"\n   Coverage Assessment:")
            print(f"      Left-leaning articles: {coverage.get('left_leaning_articles', 0)}")
            print(f"      Neutral articles: {coverage.get('neutral_articles', 0)}")
            print(f"      Right-leaning articles: {coverage.get('right_leaning_articles', 0)}")
    
    print("\n" + "=" * 70)
    print("✅ Enhanced bias detection test complete!")

if __name__ == "__main__":
    test_enhanced_bias()
