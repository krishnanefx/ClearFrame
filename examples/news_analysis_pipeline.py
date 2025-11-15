#!/usr/bin/env python3
"""
Complete News Analysis Pipeline with Valyu Search and HolisticAI

This script demonstrates an end-to-end news analysis workflow:
1. Search for news using Valyu API
2. Process and analyze using HolisticAI
3. Generate structured bias reports
4. Compare narratives across sources

Usage:
    python examples/news_analysis_pipeline.py --topic "climate change" --sources "bbc,cnn,china_daily"
    python examples/news_analysis_pipeline.py --interactive
"""

import os
import json
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# LangChain imports
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

# Local imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from tutorials.holistic_ai_bedrock import get_chat_model
from examples.valyu_holisticai_agent import (
    create_news_analysis_agent,
    create_structured_output_analyzer,
    NarrativeComparison,
    BiasAnalysis,
    NewsArticleSummary
)

load_dotenv()


# ============================================================================
# Pipeline Components
# ============================================================================

class NewsAnalysisPipeline:
    """Complete pipeline for news analysis with Valyu and HolisticAI."""
    
    def __init__(self):
        self.agent = create_news_analysis_agent()
        self.structured_analyzer = create_structured_output_analyzer()
        self.llm = get_chat_model(model_name="claude-3-5-sonnet", temperature=0.1)
        
        # Source categorization
        self.source_categories = {
            "state_aligned": [
                "China Daily",
                "RT (Russia Today)",
                "Xinhua News Agency",
                "CGTN",
                "Sputnik"
            ],
            "independent": [
                "BBC News",
                "The Guardian",
                "Associated Press",
                "Reuters",
                "NPR"
            ],
            "mainstream": [
                "CNN",
                "Fox News",
                "MSNBC",
                "ABC News",
                "CBS News"
            ]
        }
    
    def search_news(self, topic: str, sources: Optional[List[str]] = None, days: int = 7) -> Dict[str, Any]:
        """
        Search for news articles on a topic.
        
        Args:
            topic: The topic to search for
            sources: List of specific sources to search (optional)
            days: Number of days to look back (default: 7)
            
        Returns:
            Dict with search results and metadata
        """
        print(f"\n🔍 Searching for news about: {topic}")
        print(f"   Sources: {sources if sources else 'All'}")
        print(f"   Timeframe: Last {days} days")
        
        # Build search query
        if sources:
            source_queries = [f"site:{source.lower().replace(' ', '')}.com OR site:{source.lower().replace(' ', '')}.co.uk" 
                            for source in sources]
            site_filter = " ".join(source_queries)
            query = f"{topic} {site_filter}"
        else:
            query = f"{topic} news recent"
        
        # Use agent to search
        search_prompt = f"""
        Search for news articles about "{topic}" from the last {days} days.
        {f"Focus on these sources: {', '.join(sources)}" if sources else ""}
        
        For each article found:
        1. Extract the title, source, URL
        2. Analyze the sentiment
        3. Extract key entities (people, places, organizations)
        4. Provide a brief summary
        
        Return your findings in a structured format.
        """
        
        try:
            response = self.agent.invoke({"input": search_prompt})
            return {
                "success": True,
                "topic": topic,
                "results": response['output'],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }
    
    def analyze_bias(self, topic: str, sources: Optional[List[str]] = None) -> Optional[NarrativeComparison]:
        """
        Analyze bias in news coverage of a topic.
        
        Args:
            topic: The topic to analyze
            sources: List of sources to compare
            
        Returns:
            NarrativeComparison object with bias analysis
        """
        print(f"\n📊 Analyzing bias for: {topic}")
        
        # First, search and gather articles
        search_result = self.search_news(topic, sources)
        
        if not search_result['success']:
            print(f"❌ Search failed: {search_result.get('error')}")
            return None
        
        # Now analyze for bias
        analysis_prompt = f"""
        Analyze the following news coverage for bias:
        
        Topic: {topic}
        
        Search Results:
        {search_result['results']}
        
        Provide a comprehensive bias analysis including:
        1. Coverage delta (difference in volume between source types)
        2. Sentiment delta (difference in tone)
        3. Omission ratio (what's left out)
        4. Key narrative differences
        5. Recommendations for balanced information
        
        Format as a structured NarrativeComparison.
        """
        
        try:
            result = self.structured_analyzer.invoke(analysis_prompt)
            # Type checker workaround - result should be NarrativeComparison
            return result  # type: ignore
        except Exception as e:
            print(f"❌ Analysis failed: {str(e)}")
            return None
    
    def compare_sources(self, topic: str, source_a: str, source_b: str) -> Dict[str, Any]:
        """
        Compare how two sources cover the same topic.
        
        Args:
            topic: The topic to compare
            source_a: First source name
            source_b: Second source name
            
        Returns:
            Comparison results
        """
        print(f"\n⚖️  Comparing: {source_a} vs {source_b}")
        print(f"   Topic: {topic}")
        
        comparison_prompt = f"""
        Compare how these two sources cover "{topic}":
        
        Source A: {source_a}
        Source B: {source_b}
        
        Search for recent articles from both sources and analyze:
        1. What aspects does each source emphasize?
        2. What tone does each source use?
        3. What entities/facts does each mention or omit?
        4. How do their narratives differ?
        5. Which provides more balanced coverage?
        
        Provide specific examples with citations.
        """
        
        try:
            response = self.agent.invoke({"input": comparison_prompt})
            return {
                "success": True,
                "source_a": source_a,
                "source_b": source_b,
                "topic": topic,
                "comparison": response['output'],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_report(self, analysis: NarrativeComparison, output_path: Optional[str] = None) -> str:
        """
        Generate a formatted report from analysis results.
        
        Args:
            analysis: NarrativeComparison object
            output_path: Path to save report (optional)
            
        Returns:
            Formatted report string
        """
        report = f"""
{'=' * 80}
NEWS BIAS ANALYSIS REPORT
{'=' * 80}

Topic: {analysis.topic}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'=' * 80}
BIAS METRICS
{'=' * 80}

Overall Bias Level: {analysis.bias_analysis.bias_level.upper()}

Coverage Delta: {analysis.bias_analysis.coverage_delta:.3f}
  → Measures difference in coverage volume between source types
  
Sentiment Delta: {analysis.bias_analysis.sentiment_delta:.3f}
  → Measures difference in emotional tone
  
Omission Ratio: {analysis.bias_analysis.omission_ratio:.3f}
  → Measures entities omitted by certain sources

{'=' * 80}
KEY FINDINGS
{'=' * 80}

"""
        for i, finding in enumerate(analysis.bias_analysis.key_findings, 1):
            report += f"{i}. {finding}\n"
        
        report += f"\n{'=' * 80}\n"
        report += "ARTICLES ANALYZED\n"
        report += f"{'=' * 80}\n\n"
        
        for i, article in enumerate(analysis.articles, 1):
            report += f"{i}. {article.title}\n"
            report += f"   Source: {article.source}\n"
            report += f"   URL: {article.url}\n"
            report += f"   Sentiment: {article.sentiment}\n"
            report += f"   Key Entities: {', '.join(article.key_entities[:5])}\n"
            report += f"   Summary: {article.summary}\n\n"
        
        report += f"{'=' * 80}\n"
        report += "NARRATIVE DIFFERENCES\n"
        report += f"{'=' * 80}\n\n"
        
        for i, diff in enumerate(analysis.narrative_differences, 1):
            report += f"{i}. {diff}\n"
        
        report += f"\n{'=' * 80}\n"
        report += "RECOMMENDATIONS\n"
        report += f"{'=' * 80}\n\n"
        
        for i, rec in enumerate(analysis.recommendations, 1):
            report += f"{i}. {rec}\n"
        
        report += f"\n{'=' * 80}\n"
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            print(f"\n✅ Report saved to: {output_path}")
        
        return report
    
    def interactive_mode(self):
        """Run in interactive mode for ad-hoc analysis."""
        print("\n" + "=" * 80)
        print("📰 Interactive News Analysis Mode")
        print("=" * 80)
        print("\nCommands:")
        print("  search <topic> - Search for news on a topic")
        print("  analyze <topic> - Analyze bias in coverage")
        print("  compare <source1> vs <source2> on <topic> - Compare two sources")
        print("  sources - Show available sources")
        print("  quit - Exit")
        print("=" * 80)
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                elif user_input.lower() == 'sources':
                    print("\n📋 Available Sources:")
                    for category, sources in self.source_categories.items():
                        print(f"\n{category.upper()}:")
                        for source in sources:
                            print(f"  - {source}")
                
                elif user_input.lower().startswith('search '):
                    topic = user_input[7:].strip()
                    result = self.search_news(topic)
                    if result['success']:
                        print(f"\n{result['results']}")
                    else:
                        print(f"\n❌ Error: {result['error']}")
                
                elif user_input.lower().startswith('analyze '):
                    topic = user_input[8:].strip()
                    analysis = self.analyze_bias(topic)
                    if analysis:
                        report = self.generate_report(analysis)
                        print(report)
                
                elif ' vs ' in user_input.lower() and ' on ' in user_input.lower():
                    parts = user_input.split(' vs ')
                    source_a = parts[0].replace('compare', '').strip()
                    rest = parts[1].split(' on ')
                    source_b = rest[0].strip()
                    topic = rest[1].strip()
                    
                    result = self.compare_sources(topic, source_a, source_b)
                    if result['success']:
                        print(f"\n{result['comparison']}")
                    else:
                        print(f"\n❌ Error: {result['error']}")
                
                else:
                    # Free-form query to agent
                    response = self.agent.invoke({"input": user_input})
                    print(f"\n{response['output']}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Main entry point for the pipeline."""
    parser = argparse.ArgumentParser(
        description="News Analysis Pipeline with Valyu Search and HolisticAI"
    )
    parser.add_argument(
        '--topic',
        type=str,
        help="Topic to analyze"
    )
    parser.add_argument(
        '--sources',
        type=str,
        help="Comma-separated list of sources (e.g., 'bbc,cnn,china_daily')"
    )
    parser.add_argument(
        '--compare',
        type=str,
        help="Compare sources in format 'source1,source2' (e.g., 'bbc,china_daily')"
    )
    parser.add_argument(
        '--output',
        type=str,
        help="Output file path for report"
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help="Run in interactive mode"
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    print("🚀 Initializing News Analysis Pipeline...")
    print("   Valyu Search: ✓")
    print("   HolisticAI: ✓")
    print("   LangChain: ✓")
    
    pipeline = NewsAnalysisPipeline()
    
    # Interactive mode
    if args.interactive:
        pipeline.interactive_mode()
        return
    
    # Comparison mode
    if args.compare and args.topic:
        sources = [s.strip() for s in args.compare.split(',')]
        if len(sources) != 2:
            print("❌ Error: --compare requires exactly 2 sources")
            return
        
        result = pipeline.compare_sources(args.topic, sources[0], sources[1])
        print(result['comparison'] if result['success'] else f"Error: {result['error']}")
        return
    
    # Analysis mode
    if args.topic:
        sources = [s.strip() for s in args.sources.split(',')] if args.sources else None
        analysis = pipeline.analyze_bias(args.topic, sources)
        
        if analysis:
            report = pipeline.generate_report(analysis, args.output)
            if not args.output:
                print(report)
        return
    
    # No arguments - show help
    parser.print_help()
    print("\n💡 Tip: Use --interactive for interactive mode")
    print("   Example: python examples/news_analysis_pipeline.py --interactive")


if __name__ == "__main__":
    main()
