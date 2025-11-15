#!/usr/bin/env python3
"""
LangChain Agent with Valyu Search and HolisticAI Integration

This script demonstrates a complete news analysis system that:
1. Uses Valyu Search API to fetch real-time news and information
2. Processes and analyzes the data using HolisticAI for bias detection
3. Provides structured outputs with bias scoring and narrative analysis

Setup Requirements:
1. VALYU_API_KEY in .env file
2. HOLISTIC_AI_TEAM_ID in .env file
3. HOLISTIC_AI_API_TOKEN in .env file
4. All required packages from requirements.txt

Usage:
    python examples/valyu_holisticai_agent.py
"""

import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_valyu import ValyuSearchTool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferMemory

# Local imports for HolisticAI
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from tutorials.holistic_ai_bedrock import get_chat_model

# Load environment variables
load_dotenv()

# Verify API keys
required_env_vars = {
    "VALYU_API_KEY": "Valyu Search API",
    "HOLISTIC_AI_TEAM_ID": "HolisticAI Team ID",
    "HOLISTIC_AI_API_TOKEN": "HolisticAI API Token"
}

for var, name in required_env_vars.items():
    if not os.getenv(var):
        raise ValueError(f"{var} not found in .env file. Please add your {name}.")


# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================

class BiasAnalysis(BaseModel):
    """Structured bias analysis result."""
    coverage_delta: float = Field(
        description="Difference in coverage between state-aligned and independent sources (-1.0 to 1.0)"
    )
    sentiment_delta: float = Field(
        description="Difference in sentiment polarity between source types (-1.0 to 1.0)"
    )
    omission_ratio: float = Field(
        description="Ratio of entities omitted by state-aligned sources (0.0 to 1.0)"
    )
    bias_level: str = Field(
        description="Overall bias classification: 'low', 'medium', or 'high'"
    )
    key_findings: List[str] = Field(
        description="List of key findings from the bias analysis (provide at least 2-3 findings as separate list items)"
    )


class NewsArticleSummary(BaseModel):
    """Summary of a news article."""
    title: str = Field(description="Article title")
    source: str = Field(description="News source name")
    url: str = Field(description="Article URL")
    summary: str = Field(description="Brief summary of the article")
    sentiment: str = Field(description="Overall sentiment: positive, neutral, or negative")
    key_entities: List[str] = Field(description="Key people, places, or organizations mentioned")


class NarrativeComparison(BaseModel):
    """Comparison of narratives across different sources."""
    topic: str = Field(description="The topic being analyzed")
    articles: List[NewsArticleSummary] = Field(description="List of analyzed articles")
    bias_analysis: BiasAnalysis = Field(description="Bias analysis results")
    narrative_differences: List[str] = Field(
        description="Key differences in how different sources cover the topic"
    )
    recommendations: List[str] = Field(
        description="Recommendations for getting balanced information"
    )


# ============================================================================
# Custom Tools for News Analysis
# ============================================================================

@tool
def get_current_date() -> str:
    """
    Returns the current date in YYYY-MM-DD format.
    Use this when you need to search for recent news.
    """
    return datetime.now().strftime("%Y-%m-%d")


@tool
def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyzes the sentiment of a given text using TextBlob.
    
    Args:
        text: The text to analyze
        
    Returns:
        Dictionary with polarity (-1 to 1) and subjectivity (0 to 1)
    """
    from textblob import TextBlob
    blob = TextBlob(text)
    sentiment = blob.sentiment
    polarity = float(sentiment.polarity)  # type: ignore
    subjectivity = float(sentiment.subjectivity)  # type: ignore
    return {
        "polarity": polarity,
        "subjectivity": subjectivity,
        "classification": "positive" if polarity > 0.1 
                         else "negative" if polarity < -0.1 
                         else "neutral"
    }


@tool
def extract_entities(text: str) -> List[str]:
    """
    Extracts named entities (people, places, organizations) from text.
    
    Args:
        text: The text to analyze
        
    Returns:
        List of extracted entities
    """
    try:
        import spacy
        # Try to load spaCy model
        try:
            nlp = spacy.load("en_core_web_sm")
        except:
            # Fallback to simple entity extraction if spaCy model not available
            return _simple_entity_extraction(text)
        
        doc = nlp(text[:1000])  # Limit to first 1000 chars for performance
        entities = [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE"]]
        return list(set(entities))
    except Exception as e:
        # Fallback to simple extraction
        return _simple_entity_extraction(text)


def _simple_entity_extraction(text: str) -> List[str]:
    """Simple fallback for entity extraction."""
    # Extract capitalized words/phrases
    import re
    words = text.split()
    entities = []
    current_entity = []
    
    for word in words:
        if word and word[0].isupper() and not word.isupper():
            current_entity.append(word)
        else:
            if current_entity:
                entities.append(" ".join(current_entity))
                current_entity = []
    
    if current_entity:
        entities.append(" ".join(current_entity))
    
    # Filter common words and return unique entities
    common_words = {"The", "A", "An", "In", "On", "At", "To", "For", "Of", "With"}
    return list(set([e for e in entities if e not in common_words]))[:20]


@tool
def calculate_bias_score(
    state_aligned_count: int,
    independent_count: int,
    state_sentiment: float,
    independent_sentiment: float,
    omission_ratio: float
) -> Dict[str, Any]:
    """
    Calculates bias metrics based on coverage and sentiment differences.
    
    Args:
        state_aligned_count: Number of state-aligned articles
        independent_count: Number of independent articles
        state_sentiment: Average sentiment of state-aligned articles
        independent_sentiment: Average sentiment of independent articles
        omission_ratio: Ratio of entities omitted by state sources
        
    Returns:
        Dictionary with bias metrics and classification
    """
    total = state_aligned_count + independent_count
    coverage_delta = (state_aligned_count - independent_count) / total if total > 0 else 0
    sentiment_delta = state_sentiment - independent_sentiment
    
    # Calculate overall bias level
    bias_score = abs(coverage_delta) * 0.3 + abs(sentiment_delta) * 0.3 + omission_ratio * 0.4
    
    if bias_score < 0.3:
        bias_level = "low"
    elif bias_score < 0.6:
        bias_level = "medium"
    else:
        bias_level = "high"
    
    return {
        "coverage_delta": coverage_delta,
        "sentiment_delta": sentiment_delta,
        "omission_ratio": omission_ratio,
        "bias_score": bias_score,
        "bias_level": bias_level
    }


# ============================================================================
# Agent Creation
# ============================================================================

def create_news_analysis_agent():
    """Create a LangChain agent with Valyu search and HolisticAI processing."""
    
    # Initialize the HolisticAI model
    llm = get_chat_model(
        model_name="claude-3-5-sonnet",
        temperature=0.1,
        max_tokens=4096
    )
    
    # Initialize Valyu search tool
    # Note: ValyuSearchTool uses VALYU_API_KEY from environment automatically
    valyu_tool = ValyuSearchTool()
    
    # Combine all tools
    tools = [
        valyu_tool,
        get_current_date,
        analyze_sentiment,
        extract_entities,
        calculate_bias_score
    ]
    
    # Define the system prompt
    system_prompt = """You are an expert news analyst with access to real-time search and bias detection tools.

Your role is to:
1. Search for news articles on given topics using Valyu search
2. Analyze the articles for sentiment, entities, and narrative patterns
3. Detect and quantify bias in news coverage
4. Compare narratives across different news sources
5. Provide balanced, evidence-based analysis

When analyzing news:
- Search multiple sources including both state-aligned and independent media
- Extract key entities and sentiment from each article
- Calculate bias metrics (coverage delta, sentiment delta, omission ratio)
- Identify narrative differences across sources
- Provide recommendations for balanced information consumption

Available tools:
- valyu_search: Search the web for news articles and information
- get_current_date: Get today's date for searching recent news
- analyze_sentiment: Analyze sentiment of article text
- extract_entities: Extract named entities from text
- calculate_bias_score: Calculate bias metrics

Always cite your sources and provide evidence-based analysis."""
    
    # Create the prompt template for ReAct agent
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Create tool calling agent (compatible with Claude)
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    
    # Create agent executor with memory
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        ),
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10,
        max_execution_time=120
    )
    
    return agent_executor


def create_structured_output_analyzer():
    """Create an analyzer that returns structured bias analysis."""
    
    llm = get_chat_model(
        model_name="claude-3-5-sonnet",
        temperature=0.1,
        max_tokens=4096
    )
    
    # Create structured output chain
    structured_llm = llm.with_structured_output(NarrativeComparison)
    
    return structured_llm


# ============================================================================
# Main Demonstration
# ============================================================================

def main():
    """Demonstrate the Valyu + HolisticAI integration."""
    
    print("🚀 News Analysis Agent with Valyu Search + HolisticAI")
    print("=" * 70)
    
    try:
        # Create the agent
        agent = create_news_analysis_agent()
        print("✅ Agent created successfully!")
        
        # Example analysis queries
        example_queries = [
            "Search for recent news about climate change from BBC News and CNN. Compare their coverage and sentiment.",
            "Find articles about AI regulation from different sources. Analyze bias in coverage.",
            "Search for news about the Sudan conflict from Al Jazeera and The Guardian. Compare narratives."
        ]
        
        print("\n🔍 Testing News Analysis Agent:")
        print("-" * 70)
        
        # Test with one example query
        query = example_queries[0]
        print(f"\n📝 Query: {query}")
        print("-" * 40)
        
        try:
            response = agent.invoke({"input": query})
            print(f"\n🤖 Analysis:\n{response['output'][:1000]}...")
            print("\n✅ Analysis complete!")
            
        except Exception as e:
            print(f"❌ Error during analysis: {str(e)}")
        
        # Demonstrate structured output
        print("\n" + "=" * 70)
        print("📊 Testing Structured Output Analysis")
        print("-" * 70)
        
        try:
            structured_analyzer = create_structured_output_analyzer()
            
            # Sample data for structured analysis
            sample_analysis = """
            Topic: Climate Change Policy
            
            Articles analyzed:
            1. BBC News: "UK Announces New Climate Targets" - Neutral tone, focuses on policy details
            2. CNN: "Climate Crisis Worsens as Governments Fail to Act" - Negative tone, emphasizes urgency
            
            Coverage: 2 mainstream sources
            Sentiment: BBC = 0.0 (neutral), CNN = -0.3 (negative)
            Entities: UK Government, UN Climate Summit, Paris Agreement
            
            Key findings:
            - Different framing of same policy announcement
            - CNN emphasizes crisis, BBC focuses on incremental progress
            - Both cite same scientific data but draw different conclusions
            """
            
            result = structured_analyzer.invoke(
                f"Analyze the following news comparison and provide structured bias analysis:\n\n{sample_analysis}"
            )
            
            print("\n📋 Structured Analysis Result:")
            if hasattr(result, 'model_dump'):
                print(json.dumps(result.model_dump(), indent=2))
            else:
                print(json.dumps(result, indent=2))
            print("\n✅ Structured output generated successfully!")
            
        except Exception as e:
            print(f"❌ Structured output error: {str(e)}")
        
        # Interactive mode
        print("\n" + "=" * 70)
        print("💬 Interactive News Analysis Mode")
        print("Type 'quit' to exit")
        print("=" * 70)
        
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if user_input:
                try:
                    response = agent.invoke({"input": user_input})
                    print(f"\n🤖 Agent: {response['output']}")
                except Exception as e:
                    print(f"❌ Error: {str(e)}")
        
        print("\n👋 Thanks for using the News Analysis Agent!")
        
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Check that all API keys are set in .env file:")
        print("   - VALYU_API_KEY")
        print("   - HOLISTIC_AI_TEAM_ID")
        print("   - HOLISTIC_AI_API_TOKEN")
        print("2. Ensure all packages are installed: pip install -r requirements.txt")
        print("3. Verify your API keys are valid")


if __name__ == "__main__":
    main()
