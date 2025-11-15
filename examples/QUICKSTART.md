# Quick Start: Valyu Search + HolisticAI Integration

Get started with the news analysis system in 5 minutes!

## Prerequisites

- Python 3.8+
- pip or conda
- API keys (see below)

## Step 1: Get API Keys

### Valyu Search API
1. Sign up at [Valyu](https://valyu.app)
2. Get your API key from the dashboard
3. Save as `VALYU_API_KEY`

### HolisticAI
1. Get your team credentials
2. Save `HOLISTIC_AI_TEAM_ID` and `HOLISTIC_AI_API_TOKEN`

## Step 2: Setup Environment

```bash
# Clone or navigate to the project
cd TheGreatAgentHack

# Create virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Download NLP models (optional, for better entity extraction)
python -m spacy download en_core_web_sm
python -m textblob.download_corpora
```

## Step 3: Configure API Keys

Create a `.env` file in the project root:

```bash
# Valyu Search API
VALYU_API_KEY=your_valyu_api_key_here

# HolisticAI Credentials
HOLISTIC_AI_TEAM_ID=your_team_id_here
HOLISTIC_AI_API_TOKEN=your_api_token_here

# Optional: OpenAI (if you want to use as alternative)
OPENAI_API_KEY=your_openai_key_here
```

## Step 4: Test the Integration

```bash
# Run the test suite
python examples/test_integration.py
```

Expected output:
```
🧪 Valyu + HolisticAI Integration Test Suite
======================================================================
🔍 Testing Environment Variables...
  ✅ Valyu Search API: Set
  ✅ HolisticAI Team ID: Set
  ✅ HolisticAI API Token: Set
...
🎉 All tests passed! Integration is working correctly.
```

## Step 5: Run Your First Analysis

### Option A: Interactive Mode

```bash
python examples/news_analysis_pipeline.py --interactive
```

Then try commands like:
```
> search climate change
> analyze AI regulation
> compare bbc vs china_daily on climate policy
> sources
```

### Option B: Command Line

```bash
# Search for a topic
python examples/news_analysis_pipeline.py --topic "climate change" --sources "bbc,cnn"

# Compare two sources
python examples/news_analysis_pipeline.py --topic "AI regulation" --compare "bbc,china_daily"

# Generate a report
python examples/news_analysis_pipeline.py --topic "Sudan conflict" --output report.txt
```

### Option C: Python Script

```python
from examples.valyu_holisticai_agent import create_news_analysis_agent

# Create the agent
agent = create_news_analysis_agent()

# Ask a question
response = agent.invoke({
    "input": "Search for recent climate change news from BBC and CNN. Compare their coverage."
})

print(response['output'])
```

### Option D: Jupyter Notebook

```bash
jupyter notebook examples/valyu_holisticai_demo.ipynb
```

## Example Queries

### 1. Simple News Search
```
"Search for recent articles about AI regulation"
```

### 2. Source Comparison
```
"Compare how BBC and China Daily cover climate change policy"
```

### 3. Bias Analysis
```
"Find articles about the Sudan conflict from Al Jazeera and The Guardian. 
Analyze the bias in their coverage including:
- Coverage volume
- Sentiment differences
- What each source emphasizes or omits"
```

### 4. Multi-Source Analysis
```
"Search for articles about economic policy from:
1. BBC News (independent)
2. China Daily (state-aligned)
3. CNN (mainstream)

Calculate bias metrics and identify narrative differences."
```

## Understanding the Output

### Bias Metrics

**Coverage Delta** (-1.0 to 1.0)
- Positive: More state-aligned coverage
- Negative: More independent coverage
- Near 0: Balanced coverage volume

**Sentiment Delta** (-1.0 to 1.0)
- Positive: State sources more positive
- Negative: Independent sources more positive
- Near 0: Similar sentiment

**Omission Ratio** (0.0 to 1.0)
- Higher: More information omitted by state sources
- Lower: Similar information coverage

**Bias Level**
- Low (< 0.3): Minimal bias
- Medium (0.3-0.6): Moderate bias
- High (> 0.6): Significant bias

## Common Use Cases

### 1. Daily News Monitoring
```bash
# Monitor a topic across multiple sources
python examples/news_analysis_pipeline.py \
  --topic "AI developments" \
  --sources "bbc,cnn,guardian,china_daily,rt"
```

### 2. Research & Analysis
```python
from examples.news_analysis_pipeline import NewsAnalysisPipeline

pipeline = NewsAnalysisPipeline()

# Analyze multiple topics
topics = ["climate policy", "AI regulation", "economic outlook"]
for topic in topics:
    analysis = pipeline.analyze_bias(topic)
    report = pipeline.generate_report(analysis, f"report_{topic}.txt")
```

### 3. Source Credibility Check
```
"Compare coverage of [event] across BBC, Reuters, and state-aligned sources.
Identify factual differences and potential bias."
```

### 4. Narrative Tracking
```
"Track how coverage of [ongoing event] has evolved across different sources 
over the past week. What narrative shifts have occurred?"
```

## Troubleshooting

### "API key not found"
- Check that `.env` file exists in project root
- Verify no extra spaces or quotes around keys
- Ensure file is named exactly `.env` (not `env.txt` or `.env.txt`)

### "Import Error: No module named 'langchain_valyu'"
```bash
pip install --upgrade -r requirements.txt
```

### "spaCy model not found"
```bash
python -m spacy download en_core_web_sm
```
Or the system will automatically fallback to simple entity extraction.

### "Timeout Error"
- Reduce number of sources: `--sources "bbc,cnn"` instead of many
- Increase timeout in code (see advanced configuration)
- Check internet connection

### "Rate Limit Error"
- Wait a few minutes between requests
- Reduce search frequency
- Contact API provider for rate limit increase

## Advanced Configuration

### Custom Timeout
```python
from tutorials.holistic_ai_bedrock import get_chat_model

llm = get_chat_model(
    model_name="claude-3-5-sonnet",
    temperature=0.1,
    max_tokens=4096,
    timeout=120  # 2 minutes
)
```

### Custom Source Categories
```python
from examples.news_analysis_pipeline import NewsAnalysisPipeline

pipeline = NewsAnalysisPipeline()

# Add custom sources
pipeline.source_categories["regional"] = [
    "Al Jazeera",
    "Times of India",
    "Japan Times"
]
```

### Batch Processing
```python
import json

topics = ["climate", "AI", "economy"]
results = []

for topic in topics:
    analysis = pipeline.analyze_bias(topic)
    if analysis:
        results.append({
            "topic": topic,
            "bias_level": analysis.bias_analysis.bias_level,
            "findings": analysis.bias_analysis.key_findings
        })

# Save results
with open("batch_results.json", "w") as f:
    json.dump(results, f, indent=2)
```

## Next Steps

1. **Explore the examples**
   - `valyu_holisticai_agent.py` - Main agent implementation
   - `news_analysis_pipeline.py` - Complete pipeline
   - `valyu_holisticai_demo.ipynb` - Interactive notebook

2. **Read the documentation**
   - `README_VALYU_HOLISTICAI.md` - Full documentation
   - `contributing.md` - Contribution guidelines

3. **Customize for your needs**
   - Add new bias metrics
   - Integrate with your existing pipeline
   - Build a monitoring dashboard

4. **Join the community**
   - Report issues on GitHub
   - Share your use cases
   - Contribute improvements

## Support

- 📖 Documentation: `examples/README_VALYU_HOLISTICAI.md`
- 🧪 Tests: `python examples/test_integration.py`
- 💬 Issues: Create an issue on GitHub
- 📧 Contact: See main README for contact info

---

**Ready to analyze news bias?** Start with:
```bash
python examples/news_analysis_pipeline.py --interactive
```

Happy analyzing! 🚀
