#!/usr/bin/env python3
"""
Quick test script for Valyu + HolisticAI integration

This script verifies that all components are working correctly.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

def test_environment():
    """Test that all environment variables are set."""
    print("🔍 Testing Environment Variables...")
    
    required = {
        "VALYU_API_KEY": "Valyu Search API",
        "HOLISTIC_AI_TEAM_ID": "HolisticAI Team ID",
        "HOLISTIC_AI_API_TOKEN": "HolisticAI API Token"
    }
    
    all_set = True
    for var, name in required.items():
        if os.getenv(var):
            print(f"  ✅ {name}: Set")
        else:
            print(f"  ❌ {name}: Missing")
            all_set = False
    
    return all_set

def test_imports():
    """Test that all required packages can be imported."""
    print("\n🔍 Testing Package Imports...")
    
    packages = {
        "langchain": "LangChain Core",
        "langchain_valyu": "LangChain Valyu",
        "langchain_core": "LangChain Core",
        "textblob": "TextBlob",
        "pydantic": "Pydantic",
        "dotenv": "Python DotEnv"
    }
    
    all_imported = True
    for package, name in packages.items():
        try:
            __import__(package)
            print(f"  ✅ {name}: Available")
        except ImportError:
            print(f"  ❌ {name}: Not found")
            all_imported = False
    
    return all_imported

def test_holisticai():
    """Test HolisticAI connection."""
    print("\n🔍 Testing HolisticAI Connection...")
    
    try:
        from tutorials.holistic_ai_bedrock import get_chat_model
        
        llm = get_chat_model(model_name="claude-3-5-sonnet", temperature=0.1)
        print("  ✅ HolisticAI model initialized")
        
        # Test simple invocation
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content="Say 'Hello' in one word.")])
        print(f"  ✅ HolisticAI response: {response.content}")
        
        return True
    except Exception as e:
        print(f"  ❌ HolisticAI error: {str(e)}")
        return False

def test_valyu():
    """Test Valyu search tool."""
    print("\n🔍 Testing Valyu Search...")
    
    try:
        from langchain_valyu import ValyuSearchTool
        
        # Initialize without parameters (uses env vars)
        valyu = ValyuSearchTool()
        print("  ✅ Valyu search tool initialized")
        
        # Note: We can't test actual search without making API calls
        # but we can verify the tool is properly configured
        print("  ℹ️  Valyu tool ready (skipping actual search test)")
        
        return True
    except Exception as e:
        print(f"  ❌ Valyu error: {str(e)}")
        return False

def test_agent_creation():
    """Test agent creation."""
    print("\n🔍 Testing Agent Creation...")
    
    try:
        from examples.valyu_holisticai_agent import create_news_analysis_agent
        
        agent = create_news_analysis_agent()
        print("  ✅ News analysis agent created")
        
        return True
    except Exception as e:
        print(f"  ❌ Agent creation error: {str(e)}")
        return False

def test_structured_output():
    """Test structured output."""
    print("\n🔍 Testing Structured Output...")
    
    try:
        from examples.valyu_holisticai_agent import (
            create_structured_output_analyzer,
            BiasAnalysis,
            NewsArticleSummary
        )
        
        # Create analyzer
        analyzer = create_structured_output_analyzer()
        print("  ✅ Structured output analyzer created")
        
        # Test with simple prompt
        test_prompt = """
        Create a bias analysis for news coverage:
        
        Topic: Climate Change Policy
        
        Articles analyzed:
        1. BBC News - "UK Sets New Climate Targets"
           Source: BBC News
           URL: https://bbc.com/news/climate-123
           Summary: The UK announced new climate targets aiming for net zero by 2050.
           Sentiment: neutral
           Key entities: UK Government, Net Zero, 2050
        
        2. CNN - "Climate Crisis Deepens"
           Source: CNN
           URL: https://cnn.com/climate-456
           Summary: Climate crisis worsens as global temperatures continue to rise.
           Sentiment: negative
           Key entities: Global Warming, Climate Crisis, UN
        
        Bias Analysis:
        - Coverage Delta: 0.0 (equal coverage)
        - Sentiment Delta: 0.3 (CNN more negative)
        - Omission Ratio: 0.1 (minimal omission)
        - Bias Level: low
        - Key Findings (as array): 
          * Different framing of same issue
          * BBC focuses on policy while CNN emphasizes urgency
          * Both sources cover main facts
        
        Narrative Differences (as array):
        - BBC frames as policy achievement
        - CNN frames as ongoing crisis
        
        Recommendations (as array):
        - Read both for balanced view
        - Look for factual coverage
        
        IMPORTANT: Return key_findings as an array/list of strings, not a single string.
        Provide this as structured NarrativeComparison output.
        """
        
        result = analyzer.invoke(test_prompt)
        print("  ✅ Structured output generated")
        print(f"  ℹ️  Result type: {type(result)}")
        
        return True
    except Exception as e:
        print(f"  ❌ Structured output error: {str(e)}")
        return False

def test_tools():
    """Test custom tools."""
    print("\n🔍 Testing Custom Tools...")
    
    try:
        from examples.valyu_holisticai_agent import (
            get_current_date,
            analyze_sentiment,
            extract_entities,
            calculate_bias_score
        )
        
        # Test date tool
        date = get_current_date.invoke({})
        print(f"  ✅ Date tool: {date}")
        
        # Test sentiment tool
        sentiment = analyze_sentiment.invoke({"text": "This is a great test!"})
        print(f"  ✅ Sentiment tool: {sentiment['classification']}")
        
        # Test entity extraction
        entities = extract_entities.invoke({"text": "John Smith visited New York."})
        print(f"  ✅ Entity extraction: {len(entities)} entities found")
        
        # Test bias calculator
        bias = calculate_bias_score.invoke({
            "state_aligned_count": 5,
            "independent_count": 5,
            "state_sentiment": 0.5,
            "independent_sentiment": 0.0,
            "omission_ratio": 0.3
        })
        print(f"  ✅ Bias calculator: {bias['bias_level']} bias")
        
        return True
    except Exception as e:
        print(f"  ❌ Tools error: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("=" * 70)
    print("🧪 Valyu + HolisticAI Integration Test Suite")
    print("=" * 70)
    
    results = {}
    
    results['environment'] = test_environment()
    results['imports'] = test_imports()
    
    # Only run integration tests if environment and imports are OK
    if results['environment'] and results['imports']:
        results['holisticai'] = test_holisticai()
        results['valyu'] = test_valyu()
        results['agent'] = test_agent_creation()
        results['structured'] = test_structured_output()
        results['tools'] = test_tools()
    else:
        print("\n⚠️  Skipping integration tests due to missing dependencies")
        results['holisticai'] = False
        results['valyu'] = False
        results['agent'] = False
        results['structured'] = False
        results['tools'] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name.title()}")
    
    print(f"\n{'=' * 70}")
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n🎉 All tests passed! Integration is working correctly.")
        print("\n📚 Next steps:")
        print("  1. Run the main agent: python examples/valyu_holisticai_agent.py")
        print("  2. Try the pipeline: python examples/news_analysis_pipeline.py --interactive")
        print("  3. Read the docs: examples/README_VALYU_HOLISTICAI.md")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("\n🔧 Troubleshooting:")
        print("  1. Ensure all environment variables are set in .env")
        print("  2. Install missing packages: pip install -r requirements.txt")
        print("  3. Verify API keys are valid")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
