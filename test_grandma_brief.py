#!/usr/bin/env python3
"""
Test script to verify grandma brief generation with the new LLM-powered approach
"""

import json
import requests

def test_grandma_brief():
    """Test the grandma brief endpoint to ensure it's neutral and grandma-friendly."""
    print("🧪 Testing Grandma-Friendly Brief Generation (LLM-Powered)\n")
    print("=" * 60)
    
    # Make API request
    url = "http://localhost:5001/api/analyze"
    payload = {
        "query": "climate change",
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
    brief = data.get('grandma_brief', '')
    
    if not brief:
        print("❌ Error: No grandma_brief in response")
        return
    
    # Analyze the brief
    print("✅ Received grandma brief!\n")
    print("=" * 60)
    
    words = brief.split()
    sentences = [s.strip() + '.' for s in brief.split('.') if s.strip()]
    
    print(f"📊 Statistics:")
    print(f"  - Word count: {len(words)}")
    print(f"  - Sentence count: {len(sentences)}")
    print(f"  - Character count: {len(brief)}")
    
    # Check for technical jargon that should be avoided
    print(f"\n🔍 Checking for grandma-friendliness...")
    
    avoid_terms = [
        'bias score', 'censorship', 'meta-analysis', 'source type',
        'international outlet', 'state-aligned', 'diaspora', 
        'credibility tier', 'narrative framing'
    ]
    
    found_technical = [term for term in avoid_terms if term.lower() in brief.lower()]
    
    if found_technical:
        print(f"⚠️  Found technical terms (should avoid):")
        for term in found_technical:
            print(f"  - {term}")
    else:
        print(f"✅ No technical meta-analysis terms found!")
    
    # Check word count is in acceptable range
    print(f"\n📏 Word count check:")
    if 250 <= len(words) <= 400:
        print(f"✅ Word count ({len(words)}) is within target range (250-400)")
    elif len(words) < 250:
        print(f"⚠️  Word count ({len(words)}) is below target (250)")
    else:
        print(f"⚠️  Word count ({len(words)}) exceeds target (400)")
    
    print("\n" + "=" * 60)
    
    # Full brief output
    print(f"\n📄 Complete Grandma Brief:")
    print("-" * 60)
    print(brief)
    print("-" * 60)
    
    # Check article count
    article_count = data.get('article_count', 0)
    print(f"\n📰 Articles analyzed: {article_count}")

if __name__ == "__main__":
    test_grandma_brief()
