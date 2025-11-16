#!/usr/bin/env python3
"""
Test Per-Article Bias Analysis with Controversial Topics

This script tests the new bias analysis system with highly controversial
and polarizing news topics to validate that it can detect and measure
bias across the political spectrum.
"""

import json
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.basic_cli import main

# Define radical test topics
RADICAL_TEST_TOPICS = [
    {
        "query": "Israel Palestine Gaza conflict civilian casualties",
        "description": "Highly polarized topic with conflicting narratives",
        "expected_findings": ["state_aligned", "international", "emotional_manipulation", "propaganda"]
    },
    {
        "query": "Trump indictment election interference charges",
        "description": "Extreme partisan divide in US politics",
        "expected_findings": ["political_lean", "loaded_language", "bias_category"]
    },
    {
        "query": "Ukraine war Russia invasion NATO expansion",
        "description": "Geopolitical conflict with state propaganda",
        "expected_findings": ["state_aligned", "narrative_bias", "missing_perspectives"]
    },
    {
        "query": "Climate change denial fossil fuel industry funding",
        "description": "Science vs corporate interests",
        "expected_findings": ["corporate_bias", "factual_language", "credibility_tier"]
    },
    {
        "query": "COVID-19 lab leak theory Wuhan origin investigation",
        "description": "Conspiracy theories vs scientific investigation",
        "expected_findings": ["speculation", "credibility", "framing_techniques"]
    },
    {
        "query": "transgender rights children gender affirming care",
        "description": "Cultural wedge issue with strong emotions",
        "expected_findings": ["emotional_manipulation", "loaded_language", "missing_perspectives"]
    },
    {
        "query": "immigration border crisis illegal migrants",
        "description": "Loaded language and political framing",
        "expected_findings": ["political_lean", "framing_bias", "language_bias"]
    },
    {
        "query": "China Uyghur genocide concentration camps Xinjiang",
        "description": "State censorship and human rights",
        "expected_findings": ["state_aligned", "censorship", "propaganda"]
    },
    {
        "query": "abortion rights Supreme Court Roe Wade overturned",
        "description": "Fundamental rights disagreement",
        "expected_findings": ["moral_framing", "political_lean", "emotional_triggers"]
    },
    {
        "query": "Hunter Biden laptop scandal election influence",
        "description": "Partisan media coverage differences",
        "expected_findings": ["source_diversity", "narrative_divergence", "credibility"]
    }
]


RUN_MANUAL_BIAS_TESTS = os.getenv("RUN_BIAS_MANUAL_TESTS") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_MANUAL_BIAS_TESTS,
    reason="Manual bias analysis test requires API access. "
           "Set RUN_BIAS_MANUAL_TESTS=1 to run.",
)


def run_single_topic(topic: dict, verbose: bool = True):
    """Run bias analysis on a single controversial topic."""
    print(f"\n{'='*80}")
    print(f"Testing: {topic['query']}")
    print(f"Description: {topic['description']}")
    print(f"{'='*80}\n")
    
    # Simulate command-line arguments
    import argparse
    old_argv = sys.argv
    sys.argv = [
        'backend.basic_cli',
        '--query', topic['query'],
        '--mode', 'unified-deterministic',
        '--max-results', '10',
        '--json-only',
        '--output-file', f"test_output_{topic['query'].replace(' ', '_')[:30]}.json"
    ]
    
    try:
        # Run the analysis
        main()
        
        # Load and analyze the output
        output_file = f"test_output_{topic['query'].replace(' ', '_')[:30]}.json"
        try:
            with open(output_file, 'r') as f:
                results = json.load(f)
            
            print("\n✅ Analysis completed successfully!")
            print(f"\n📊 Results Summary:")
            
            bias_analysis = results.get('bias_analysis', {})
            articles = bias_analysis.get('articles', [])
            aggregate = bias_analysis.get('aggregate_stats', {})
            
            print(f"  - Articles analyzed: {len(articles)}")
            print(f"  - Average overall bias: {aggregate.get('average_scores', {}).get('overall_bias', 0):.1f}/50")
            
            avg_scores = aggregate.get('average_scores', {})
            print(f"\n  Bias Dimensions:")
            print(f"    • Political lean: {avg_scores.get('political_lean', 0):.1f}")
            print(f"    • Emotional manipulation: {avg_scores.get('emotional_manipulation', 0):.1f}")
            print(f"    • Sensationalism: {avg_scores.get('sensationalism', 0):.1f}")
            print(f"    • Propaganda: {avg_scores.get('propaganda', 0):.1f}")
            print(f"    • Factual language: {avg_scores.get('factual_language', 0):.1f}")
            
            coverage = aggregate.get('coverage_assessment', {})
            print(f"\n  Coverage Distribution:")
            print(f"    • Left-leaning: {coverage.get('left_leaning_articles', 0)}")
            print(f"    • Neutral: {coverage.get('neutral_articles', 0)}")
            print(f"    • Right-leaning: {coverage.get('right_leaning_articles', 0)}")
            print(f"    • High credibility: {coverage.get('high_credibility_count', 0)}")
            print(f"    • Low credibility: {coverage.get('low_credibility_count', 0)}")
            
            propaganda = aggregate.get('propaganda_analysis', {})
            print(f"\n  Propaganda Detection:")
            print(f"    • Total techniques detected: {propaganda.get('total_techniques_detected', 0)}")
            print(f"    • Unique techniques: {propaganda.get('unique_techniques', 0)}")
            if propaganda.get('top_techniques'):
                print(f"    • Top techniques: {list(propaganda['top_techniques'].keys())}")
            
            if verbose and articles:
                print(f"\n  📰 Sample Article Analysis:")
                for i, article in enumerate(articles[:3]):
                    print(f"\n  Article {i+1}: {article.get('title', 'Untitled')[:80]}")
                    print(f"    Source: {article.get('source', 'unknown')}")
                    scores = article.get('bias_scores', {})
                    classification = article.get('classification', {})
                    print(f"    Category: {classification.get('bias_category', 'unknown')}")
                    print(f"    Credibility: {classification.get('credibility_tier', 'unknown')}")
                    print(f"    Political Lean: {scores.get('political_lean', 0):.1f}")
                    print(f"    Overall Bias: {scores.get('overall_bias', 0):.1f}/50")
                    
                    features = article.get('detected_features', {})
                    if features.get('propaganda_techniques'):
                        print(f"    Propaganda: {', '.join(features['propaganda_techniques'][:3])}")
                    if features.get('emotional_triggers'):
                        print(f"    Emotional Triggers: {', '.join([str(t) for t in features['emotional_triggers'][:3]])}")
            
            # Check for expected findings
            print(f"\n  🔍 Validation against expected findings:")
            for expected in topic.get('expected_findings', []):
                found = False
                if 'political_lean' in expected and abs(avg_scores.get('political_lean', 0)) > 15:
                    found = True
                    print(f"    ✓ {expected}: Political lean detected ({avg_scores.get('political_lean', 0):.1f})")
                elif 'state_aligned' in expected:
                    source_types = aggregate.get('category_breakdown', {}).get('source_types', {})
                    if source_types.get('state', 0) > 0:
                        found = True
                        print(f"    ✓ {expected}: Found {source_types.get('state', 0)} state media sources")
                elif 'propaganda' in expected and propaganda.get('total_techniques_detected', 0) > 0:
                    found = True
                    print(f"    ✓ {expected}: Detected {propaganda.get('total_techniques_detected', 0)} propaganda techniques")
                elif 'emotional_manipulation' in expected and avg_scores.get('emotional_manipulation', 0) > 30:
                    found = True
                    print(f"    ✓ {expected}: High emotional manipulation ({avg_scores.get('emotional_manipulation', 0):.1f})")
                elif 'credibility' in expected:
                    if coverage.get('low_credibility_count', 0) > 0 or coverage.get('high_credibility_count', 0) > 0:
                        found = True
                        print(f"    ✓ {expected}: Credibility variance detected")
                
                if not found:
                    print(f"    ⚠ {expected}: Not clearly detected (may need more articles or refinement)")
            
            return results
            
        except FileNotFoundError:
            print(f"\n❌ Output file not found: {output_file}")
            return None
        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse JSON output: {e}")
            return None
    
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        sys.argv = old_argv


def test_all_topics():
    """Test all controversial topics."""
    print("\n" + "="*80)
    print("PER-ARTICLE BIAS ANALYSIS - RADICAL NEWS TOPICS TEST SUITE")
    print("="*80)
    print(f"\nTesting {len(RADICAL_TEST_TOPICS)} controversial topics...")
    
    results = {}
    successful = 0
    failed = 0
    
    for i, topic in enumerate(RADICAL_TEST_TOPICS, 1):
        print(f"\n\n[{i}/{len(RADICAL_TEST_TOPICS)}] ", end='')
        result = run_single_topic(topic, verbose=True)
        
        if result:
            results[topic['query']] = result
            successful += 1
        else:
            failed += 1
    
    # Summary
    print("\n\n" + "="*80)
    print("TEST SUITE SUMMARY")
    print("="*80)
    print(f"Total topics tested: {len(RADICAL_TEST_TOPICS)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if results:
        print("\n📈 Aggregate Findings Across All Topics:")
        
        all_avg_bias = []
        all_political_lean = []
        all_propaganda = []
        all_emotional = []
        
        for query, result in results.items():
            bias_analysis = result.get('bias_analysis', {})
            aggregate = bias_analysis.get('aggregate_stats', {})
            avg_scores = aggregate.get('average_scores', {})
            
            all_avg_bias.append(avg_scores.get('overall_bias', 0))
            all_political_lean.append(abs(avg_scores.get('political_lean', 0)))
            all_propaganda.append(aggregate.get('propaganda_analysis', {}).get('total_techniques_detected', 0))
            all_emotional.append(avg_scores.get('emotional_manipulation', 0))
        
        print(f"  Average overall bias: {sum(all_avg_bias)/len(all_avg_bias):.1f}/50")
        print(f"  Average political lean: {sum(all_political_lean)/len(all_political_lean):.1f}")
        print(f"  Average propaganda techniques: {sum(all_propaganda)/len(all_propaganda):.1f}")
        print(f"  Average emotional manipulation: {sum(all_emotional)/len(all_emotional):.1f}")
        
        print(f"\n  Most biased topic: {list(results.keys())[all_avg_bias.index(max(all_avg_bias))][:60]}")
        print(f"  Most balanced topic: {list(results.keys())[all_avg_bias.index(min(all_avg_bias))][:60]}")
    
    print("\n" + "="*80 + "\n")
    
    return results


@pytest.mark.parametrize("topic", RADICAL_TEST_TOPICS)
def test_single_topic(topic):
    """Pytest wrapper to enable single-topic run when manual tests are enabled."""
    result = run_single_topic(topic, verbose=False)
    assert result is not None, "Bias analysis returned no results"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test per-article bias analysis with controversial topics")
    parser.add_argument('--topic-index', type=int, help='Test only a specific topic by index (0-based)')
    parser.add_argument('--quick', action='store_true', help='Run quick test with fewer articles')
    
    args = parser.parse_args()
    
    if args.topic_index is not None:
        if 0 <= args.topic_index < len(RADICAL_TEST_TOPICS):
            test_single_topic(RADICAL_TEST_TOPICS[args.topic_index], verbose=True)
        else:
            print(f"❌ Topic index {args.topic_index} out of range (0-{len(RADICAL_TEST_TOPICS)-1})")
    else:
        test_all_topics()
