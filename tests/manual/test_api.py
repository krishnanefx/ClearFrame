#!/usr/bin/env python3
"""
Test script for FactFlow API
Verifies that the API server is working correctly
"""

import requests
import json
import sys

API_BASE = "http://localhost:5001"

def test_health():
    """Test health check endpoint"""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Health check passed")
            return True
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False


def test_analyze():
    """Test analyze endpoint"""
    print("\n🔍 Testing analyze endpoint...")
    try:
        payload = {
            "query": "climate change",
            "max_results": 5,
            "search_type": "web",
            "response_length": "medium",
            "enable_advanced": False
        }
        
        print(f"   Sending request: {payload['query']}")
        response = requests.post(
            f"{API_BASE}/api/analyze",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Analysis completed")
            print(f"   Articles analyzed: {data.get('article_count', 0)}")
            print(f"   Query: {data.get('query')}")
            
            # Print some bias metrics
            bias = data.get('bias_analysis', {})
            aggregate = bias.get('aggregate_stats', {})
            avg_scores = aggregate.get('average_scores', {})
            
            if avg_scores:
                print(f"   Average bias score: {avg_scores.get('overall_bias', 'N/A')}")
            
            return True
        else:
            print(f"   ❌ Analysis failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Analysis failed: {e}")
        return False


def test_search():
    """Test search endpoint"""
    print("\n🔎 Testing search endpoint...")
    try:
        payload = {
            "query": "artificial intelligence",
            "max_results": 5,
            "search_type": "web"
        }
        
        print(f"   Sending request: {payload['query']}")
        response = requests.post(
            f"{API_BASE}/api/search",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Search completed")
            print(f"   Articles found: {data.get('article_count', 0)}")
            return True
        else:
            print(f"   ❌ Search failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        return False


def main():
    print("🧪 FactFlow API Test Suite")
    print("=" * 50)
    
    results = []
    
    # Test health check
    results.append(("Health Check", test_health()))
    
    # Test analyze endpoint (most important)
    results.append(("Analyze Endpoint", test_analyze()))
    
    # Test search endpoint
    results.append(("Search Endpoint", test_search()))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
