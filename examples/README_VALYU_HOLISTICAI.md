# Valyu Search + HolisticAI Integration

This directory contains examples demonstrating the integration of **Valyu Search API** with **HolisticAI** for comprehensive news analysis and bias detection.

## Overview

The integration combines:
- **Valyu Search API**: Real-time web search capabilities for fetching news articles
- **HolisticAI Bedrock**: Claude-powered LLM with bias detection and monitoring
- **LangChain**: Agent framework for orchestrating tools and workflows
- **Custom Bias Analysis**: Quantitative metrics for media bias detection

## Files

### `valyu_holisticai_agent.py`
The main integration file that combines all components:
- News search using Valyu API
- Sentiment analysis and entity extraction
- Bias scoring and narrative comparison
- Structured output generation

### `langchain_valyu_agent.py`
Simpler example focusing on Valyu search with LangChain agents.

### `holistic_ai_bedrock.py`
Standalone HolisticAI integration with structured output support.

## Features

### 1. **Real-Time News Search**
```python
# Search for news articles on any topic
agent.invoke({
    "input": "Search for recent news about climate change from BBC and CNN"
})
```

### 2. **Bias Detection**
Quantitative metrics:
- **Coverage Delta**: Difference in coverage volume between source types
- **Sentiment Delta**: Difference in emotional tone
- **Omission Ratio**: Entities mentioned in independent sources but omitted elsewhere

### 3. **Narrative Comparison**
Compare how different sources cover the same topic:
```python
agent.invoke({
    "input": "Compare coverage of Sudan conflict from Al Jazeera and The Guardian"
})
```

### 4. **Structured Output**
Get analysis results in structured format:
```python
structured_analyzer = create_structured_output_analyzer()
result = structured_analyzer.invoke(analysis_prompt)
# Returns: NarrativeComparison(topic=..., articles=..., bias_analysis=...)
```

## Setup

### 1. Environment Variables
Create a `.env` file with:
```bash
# Required for Valyu Search
VALYU_API_KEY=your_valyu_api_key

# Required for HolisticAI
HOLISTIC_AI_TEAM_ID=your_team_id
HOLISTIC_AI_API_TOKEN=your_api_token

# Optional: For alternative OpenAI usage
OPENAI_API_KEY=your_openai_key
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- `langchain>=0.1.0`
- `langchain-valyu>=0.1.0`
- `langchain-anthropic>=0.1.0`
- `python-dotenv>=1.0.0`
- `textblob>=0.18.0`
- `spacy>=3.7.0`

### 3. Download NLP Models (Optional)
For better entity extraction:
```bash
python -m spacy download en_core_web_sm
python -m textblob.download_corpora
```

## Usage Examples

### Basic News Search
```python
from examples.valyu_holisticai_agent import create_news_analysis_agent

agent = create_news_analysis_agent()

response = agent.invoke({
    "input": "Find recent articles about AI regulation in the EU"
})

print(response['output'])
```

### Bias Analysis
```python
response = agent.invoke({
    "input": """
    Search for news about climate policy from:
    1. BBC News (independent)
    2. China Daily (state-aligned)
    
    Compare their coverage and analyze bias.
    """
})
```

### Structured Analysis
```python
from examples.valyu_holisticai_agent import create_structured_output_analyzer

analyzer = create_structured_output_analyzer()

result = analyzer.invoke("""
Analyze the following news comparison:
- BBC: "New Climate Targets Announced" (neutral tone)
- CNN: "Climate Crisis Worsens" (urgent tone)

Provide structured bias analysis.
""")

print(result.bias_analysis.bias_level)  # "medium"
print(result.recommendations)  # List of recommendations
```

## Architecture

```
User Query
    ↓
LangChain Agent
    ↓
├─→ Valyu Search Tool ─→ Fetch Articles
├─→ Sentiment Analysis ─→ Analyze Tone
├─→ Entity Extraction ─→ Extract Names/Places
├─→ Bias Calculator ─→ Compute Metrics
    ↓
HolisticAI Claude Model
    ↓
Structured Output
    ↓
NarrativeComparison
```

## Bias Metrics Explained

### Coverage Delta
Measures the difference in volume of coverage:
```
coverage_delta = (state_aligned_count - independent_count) / total_count
```
- Range: -1.0 to 1.0
- Positive: More state-aligned coverage
- Negative: More independent coverage

### Sentiment Delta
Measures the difference in emotional tone:
```
sentiment_delta = avg_state_sentiment - avg_independent_sentiment
```
- Range: -1.0 to 1.0
- Positive: State sources more positive
- Negative: Independent sources more positive

### Omission Ratio
Measures what state sources leave out:
```
omission_ratio = entities_only_in_independent / total_independent_entities
```
- Range: 0.0 to 1.0
- Higher: More omission by state sources

### Overall Bias Level
Combined score classification:
- **Low** (< 0.3): Minimal bias detected
- **Medium** (0.3-0.6): Moderate bias detected
- **High** (> 0.6): Significant bias detected

## Tools Available to Agent

### Core Tools

1. **valyu_search**
   - Search the web for news articles
   - Parameters: query, site_filter (optional)
   - Returns: List of search results with URLs, titles, snippets

2. **get_current_date**
   - Get today's date for searching recent news
   - Returns: Date in YYYY-MM-DD format

3. **analyze_sentiment**
   - Analyze sentiment of article text
   - Parameters: text
   - Returns: polarity, subjectivity, classification

4. **extract_entities**
   - Extract named entities (people, places, organizations)
   - Parameters: text
   - Returns: List of entities

5. **calculate_bias_score**
   - Calculate bias metrics
   - Parameters: counts and sentiments
   - Returns: Bias scores and classification

## Pydantic Models

### BiasAnalysis
```python
class BiasAnalysis(BaseModel):
    coverage_delta: float
    sentiment_delta: float
    omission_ratio: float
    bias_level: str  # "low", "medium", "high"
    key_findings: List[str]
```

### NewsArticleSummary
```python
class NewsArticleSummary(BaseModel):
    title: str
    source: str
    url: str
    summary: str
    sentiment: str  # "positive", "neutral", "negative"
    key_entities: List[str]
```

### NarrativeComparison
```python
class NarrativeComparison(BaseModel):
    topic: str
    articles: List[NewsArticleSummary]
    bias_analysis: BiasAnalysis
    narrative_differences: List[str]
    recommendations: List[str]
```

## Advanced Usage

### Custom News Sources
```python
sources = {
    "state_aligned": ["China Daily", "RT", "Xinhua"],
    "independent": ["BBC", "Guardian", "Associated Press"]
}

query = f"""
Search for articles about [topic] from these sources:
State-aligned: {', '.join(sources['state_aligned'])}
Independent: {', '.join(sources['independent'])}

Compare their narratives and calculate bias metrics.
"""

response = agent.invoke({"input": query})
```

### Multi-Topic Analysis
```python
topics = ["climate change", "AI regulation", "economic policy"]

for topic in topics:
    response = agent.invoke({
        "input": f"Analyze coverage of {topic} across multiple sources"
    })
    # Process results...
```

### Batch Processing
```python
from typing import List

def batch_analyze(topics: List[str]) -> List[NarrativeComparison]:
    """Analyze multiple topics in batch."""
    analyzer = create_structured_output_analyzer()
    results = []
    
    for topic in topics:
        # Search and analyze
        # ...
        result = analyzer.invoke(analysis_prompt)
        results.append(result)
    
    return results
```

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify all keys are set in `.env`
   - Check key format (no extra spaces/quotes)
   - Ensure keys are valid and active

2. **Import Errors**
   - Install all requirements: `pip install -r requirements.txt`
   - Check Python version (3.8+)

3. **spaCy Model Not Found**
   - The system will fallback to simple entity extraction
   - For better results: `python -m spacy download en_core_web_sm`

4. **Timeout Errors**
   - Increase timeout in agent config
   - Reduce number of search results
   - Split large queries into smaller ones

5. **Structured Output Errors**
   - Ensure HolisticAI API supports response_format
   - Fallback to OpenAI if needed: `use_openai=True`

## Performance Tips

1. **Limit Search Results**
   - Start with 5-10 results per source
   - Increase only if needed

2. **Use Caching**
   - Cache search results for repeated queries
   - Store processed articles locally

3. **Parallel Processing**
   - Search multiple sources in parallel
   - Process articles concurrently

4. **Rate Limiting**
   - Respect API rate limits
   - Add delays between requests if needed

## Integration with Existing Pipeline

The agent integrates with the existing news pipeline:

```python
from src.agents.news_agent import NewsAgent
from examples.valyu_holisticai_agent import create_news_analysis_agent

# Use existing pipeline
news_agent = NewsAgent()
comparisons = news_agent.compare_narratives("climate change")

# Or use new Valyu-powered agent
valyu_agent = create_news_analysis_agent()
response = valyu_agent.invoke({
    "input": "Analyze climate change coverage"
})
```

## Future Enhancements

- [ ] Real-time monitoring dashboard
- [ ] Historical bias tracking
- [ ] Multi-language support
- [ ] Custom bias metrics
- [ ] Export to various formats (PDF, CSV, JSON)
- [ ] Integration with other search APIs
- [ ] Automated report generation

## Contributing

See `contributing.md` for guidelines on contributing to this project.

## License

See main repository LICENSE file.
