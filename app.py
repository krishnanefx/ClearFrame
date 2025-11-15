#!/usr/bin/env python3
"""
News Analysis App with Valyu Search + HolisticAI

A Streamlit application for analyzing news bias using:
- Valyu Search API for real-time news retrieval
- HolisticAI for AI-powered analysis
"""

import os
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime
import json

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="News Bias Analyzer",
    page_icon="📰",
    layout="wide"
)

# Import after streamlit config to avoid conflicts
try:
    from langchain_valyu import ValyuSearchTool
    from tutorials.holistic_ai_bedrock import get_chat_model
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()


# Initialize session state
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []


def initialize_tools():
    """Initialize Valyu search and HolisticAI."""
    try:
        # Check API keys
        if not os.getenv("VALYU_API_KEY"):
            st.error("VALYU_API_KEY not found in environment variables")
            return None, None
        
        if not os.getenv("HOLISTIC_AI_TEAM_ID") or not os.getenv("HOLISTIC_AI_API_TOKEN"):
            st.error("HolisticAI credentials not found in environment variables")
            return None, None
        
        # Initialize tools
        valyu_tool = ValyuSearchTool()
        llm = get_chat_model(
            model_name="claude-3-5-sonnet",
            temperature=0.1,
            max_tokens=4096
        )
        
        return valyu_tool, llm
    except Exception as e:
        st.error(f"Error initializing tools: {str(e)}")
        return None, None


def search_news(valyu_tool, query, sources=None, max_results=5):
    """Search for news using Valyu API."""
    try:
        # Build search parameters
        search_params = {
            "query": query,
            "max_num_results": max_results,
        }
        
        if sources:
            # Add source filtering
            search_params["included_sources"] = sources
        
        # Perform search
        result = valyu_tool.invoke(search_params)
        
        if isinstance(result, str):
            # Parse JSON string result
            result = json.loads(result)
        
        return result
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return None


def analyze_with_ai(llm, articles, query):
    """Analyze articles using HolisticAI."""
    try:
        # Build analysis prompt
        articles_text = "\n\n".join([
            f"Title: {article.get('title', 'N/A')}\n"
            f"Source: {article.get('source', 'N/A')}\n"
            f"URL: {article.get('url', 'N/A')}\n"
            f"Description: {article.get('description', 'N/A')}"
            for article in articles[:10]  # Limit to first 10
        ])
        
        system_prompt = """You are an expert news analyst specializing in bias detection and narrative comparison.

Analyze the provided news articles and provide:
1. Overall sentiment and tone
2. Key topics and themes
3. Potential bias indicators
4. Narrative differences across sources
5. Recommendations for balanced information

Be objective, cite specific examples, and provide evidence-based analysis."""

        user_prompt = f"""Analyze these news articles about "{query}":

{articles_text}

Provide a comprehensive analysis covering sentiment, bias, and key narratives."""

        # Get AI analysis
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        st.error(f"Analysis error: {str(e)}")
        return None


def calculate_bias_metrics(articles):
    """Calculate simple bias metrics from articles."""
    if not articles:
        return None
    
    try:
        from textblob import TextBlob
        
        sentiments = []
        sources = set()
        
        for article in articles:
            # Calculate sentiment
            text = article.get('description', '') or article.get('content', '')
            if text:
                blob = TextBlob(str(text)[:500])  # First 500 chars
                sentiments.append(float(blob.sentiment.polarity))  # type: ignore
            
            # Track sources
            source = article.get('source', 'unknown')
            sources.add(source)
        
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        return {
            "num_articles": len(articles),
            "num_sources": len(sources),
            "avg_sentiment": avg_sentiment,
            "sentiment_range": (min(sentiments), max(sentiments)) if sentiments else (0, 0)
        }
    except Exception as e:
        st.warning(f"Could not calculate metrics: {str(e)}")
        return None


# ============================================================================
# Streamlit UI
# ============================================================================

st.title("📰 News Bias Analyzer")
st.markdown("### Powered by Valyu Search + HolisticAI")

st.markdown("""
This tool helps you:
- 🔍 Search for news from multiple sources
- 🤖 Analyze content using AI
- 📊 Detect potential bias
- 💡 Get recommendations for balanced information
""")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Search settings
    max_results = st.slider("Max results per search", 3, 20, 5)
    
    # Source selection
    st.subheader("News Sources")
    source_categories = {
        "All Sources": [],
        "Independent": ["bbc.com", "theguardian.com", "reuters.com", "apnews.com"],
        "Mainstream US": ["cnn.com", "foxnews.com", "nytimes.com"],
        "State-Aligned": ["chinadaily.com.cn", "rt.com", "xinhuanet.com"],
        "Custom": []
    }
    
    source_category = st.selectbox("Source Category", list(source_categories.keys()))
    
    if source_category == "Custom":
        custom_sources = st.text_area(
            "Enter sources (one per line)",
            placeholder="bbc.com\ncnn.com\ntheguardian.com"
        )
        selected_sources = [s.strip() for s in custom_sources.split("\n") if s.strip()]
    else:
        selected_sources = source_categories[source_category]
    
    # Show selected sources
    if selected_sources:
        st.info(f"Searching: {', '.join(selected_sources)}")
    else:
        st.info("Searching: All available sources")

# Main content area
st.markdown("---")

# Search input
query = st.text_input(
    "🔍 Enter your search topic",
    placeholder="e.g., climate change policy, AI regulation, economic outlook",
    help="Enter a topic to search for and analyze news coverage"
)

# Search button
if st.button("🚀 Analyze News", type="primary", use_container_width=True):
    if not query:
        st.warning("Please enter a search topic")
    else:
        # Initialize tools
        with st.spinner("Initializing..."):
            valyu_tool, llm = initialize_tools()
        
        if valyu_tool and llm:
            # Search for news
            with st.spinner(f"🔍 Searching for articles about '{query}'..."):
                search_results = search_news(valyu_tool, query, selected_sources, max_results)
            
            if search_results and isinstance(search_results, dict):
                articles = search_results.get('results', [])
                
                if articles:
                    st.success(f"✅ Found {len(articles)} articles")
                    
                    # Display metrics
                    metrics = calculate_bias_metrics(articles)
                    if metrics:
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Articles", metrics["num_articles"])
                        with col2:
                            st.metric("Sources", metrics["num_sources"])
                        with col3:
                            sentiment_label = (
                                "Positive" if metrics["avg_sentiment"] > 0.1
                                else "Negative" if metrics["avg_sentiment"] < -0.1
                                else "Neutral"
                            )
                            st.metric("Avg Sentiment", sentiment_label)
                        with col4:
                            range_val = metrics["sentiment_range"][1] - metrics["sentiment_range"][0]
                            st.metric("Sentiment Range", f"{range_val:.2f}")
                    
                    # Analyze with AI
                    with st.spinner("🤖 Analyzing with HolisticAI..."):
                        analysis = analyze_with_ai(llm, articles, query)
                    
                    if analysis:
                        # Display analysis
                        st.markdown("---")
                        st.subheader("📊 AI Analysis")
                        st.markdown(analysis)
                        
                        # Display articles
                        st.markdown("---")
                        st.subheader("📰 Articles Found")
                        
                        for i, article in enumerate(articles, 1):
                            with st.expander(f"{i}. {article.get('title', 'Untitled')}"):
                                st.markdown(f"**Source:** {article.get('source', 'Unknown')}")
                                st.markdown(f"**URL:** [{article.get('url', 'N/A')}]({article.get('url', '#')})")
                                st.markdown(f"**Description:** {article.get('description', 'No description available')}")
                                
                                # Show relevance score if available
                                if 'relevance_score' in article:
                                    st.progress(article['relevance_score'])
                                    st.caption(f"Relevance: {article['relevance_score']:.2%}")
                        
                        # Save to history
                        st.session_state.analysis_history.append({
                            "timestamp": datetime.now().isoformat(),
                            "query": query,
                            "num_articles": len(articles),
                            "analysis": analysis[:200] + "..."  # Store preview
                        })
                    else:
                        st.error("Failed to analyze articles")
                else:
                    st.warning("No articles found. Try a different query or sources.")
            else:
                st.error("Search failed. Please check your API keys and try again.")

# Show analysis history in sidebar
if st.session_state.analysis_history:
    with st.sidebar:
        st.markdown("---")
        st.subheader("📜 Recent Analyses")
        for i, item in enumerate(reversed(st.session_state.analysis_history[-5:]), 1):
            with st.expander(f"{item['query'][:30]}..."):
                st.caption(f"🕒 {item['timestamp'][:19]}")
                st.caption(f"📰 {item['num_articles']} articles")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    <p>Powered by <strong>Valyu Search API</strong> + <strong>HolisticAI</strong></p>
    <p>Built for news analysis and bias detection</p>
</div>
""", unsafe_allow_html=True)
