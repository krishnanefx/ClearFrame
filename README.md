# TheGreatAgentHack - News Article Agent

**Person 1: Agent Architecture Lead** - Advanced ReAct agent for news research and analysis.

## 🚀 Features

### Core Architecture
- **LangGraph ReAct Agent**: Modern function-calling pattern with reasoning + acting loops
- **Holistic AI Bedrock**: Claude models via Holistic AI proxy
- **Advanced Tool Integration**: Valyu AI search for real-time information
- **Robust Error Handling**: Retry-aware timeouts and graceful failures

### Advanced Capabilities
- **Configuration Management**: Environment-based config with validation
- **Performance Metrics**: Query success rates, response times, tool usage analytics
- **Structured Output**: Multiple output formats (summary, bullet points, sources, detailed)
- **Conversation Memory**: Multi-turn conversations with context retention
- **Comprehensive Logging**: Debug and monitoring capabilities

### Agent Architecture Highlights
- **Resilience Strategy**: Configurable retries on Holistic AI Bedrock requests
- **Tool Orchestration**: Dynamic tool selection and execution
- **State Management**: Message history and conversation flow
- **Performance Monitoring**: Real-time metrics collection and reporting
- **Modular Design**: Separated concerns (config, metrics, tools, agent logic)

## 🛠️ Setup

### Prerequisites
```bash
pip install langgraph langchain langchain-core langchain-valyu python-dotenv requests pydantic PyYAML
```

### Environment Configuration
```bash
# Copy and edit environment file
cp config/.env.example .env

# Required: Holistic AI Bedrock (recommended)
HOLISTIC_AI_TEAM_ID="your-team-id"
HOLISTIC_AI_API_TOKEN="your-token"

# Required: Valyu Search
VALYU_API_KEY="your-valyu-key"

# Optional overrides
HOLISTIC_AI_BASE_URL="https://api.holisticai.com/bedrock-proxy"
```

### Censorship Cross-Checker Story
- **Concept**: Track how state-aligned versus independent outlets describe the same events, flagging censorship signals by region.
- **Prompt to share**: `Set up config scaffolding and data directories for the censorship cross-checker`
- **Data staging**: Raw source dumps land in `data/raw/`, intermediate merges live in `data/processed/`.
- **Source registry**: Curate outlets and region tags through `config/censorship_sources.yaml` (or `.json`) so the agent can align tool calls with editorial intent.

#### Config Scaffolding Overview
```yaml
pipeline: censorship_cross_checker
regions:
  us: "North America focus"
sources:
  - id: liberty_watch
    url: https://libertywatch.example.com/rss
    region_tags: ["us", "eu"]
    state_aligned: false
valyu:
  credentials:
    api_key_env: VALYU_API_KEY
  search_defaults:
    freshness_days: 5
```

Use `src.utils.config.load_censorship_config()` to parse the YAML/JSON file into `dataclass` objects (sources, Valyu defaults, and credential env pointers) that the agent can feed into pipelines. The loader automatically picks the YAML config under `config/` unless another path is supplied.

#### Config Validation Helper
Run `python scripts/validate_censorship_config.py` to ensure new source entries follow the schema (unique IDs, known regions, valid URLs). This lightweight gate prevents malformed registry updates from breaking downstream pipelines.

### Source Ingestion Layer
- **Prompt to share**: `Implement the ingestion layer with retry/backoff and local caching; add hooks for Valyu search`
- **Fetcher service**: `src.ingestion.fetcher.SourceFetcher` pulls RSS/API/HTML endpoints with exponential backoff, then stores raw HTML and cleaned text into an S3-like local cache under `data/cache_store/`.
- **Valyu hook**: The same service owns a `ValyuSearchGateway` stub so we can either fan queries out to the live tool or return reproducible metadata when offline.
- **Usage sketch**:
```python
from src.ingestion import SourceFetcher

fetcher = SourceFetcher()
results = fetcher.ingest_all_sources()
for item in results:
    print(item.source_id, item.cleaned_path)
```
- **Next ideas**: Emit comparison-ready summaries directly from the cached fetches (so agents can diff narratives without re-downloading) and swap the Valyu stub for the live client as soon as outbound network access is available.
- **Cached context feed**: Every fetch now emits metadata(JSON) + normalized text under `data/cache_store/metadata/`. `NewsAgent` ingests the freshest snippets before calling the LLM, meaning the agent reasons over local evidence even when external calls fail.
- **Valyu cross-checks**: `BiasLangGraphAgent` exposes a `ValyuCrossCheckTool` that fans queries out to Valyu search (stubbed locally when credentials are absent) and logs recall gains so we know whether external search increases coverage for a topic.

### Normalization & Language Detection
- **Prompt to share**: `Build the content normalization module with language detection and tests`
- **Module**: `src.ingestion.normalizer.ContentNormalizer` strips HTML, infers language (ASCII/diacritic heuristics), and records metadata such as character count + fallback usage so downstream reporting can reason about coverage quality.
- **Integration**: `SourceFetcher` now persists both raw HTML and normalized text plus `language` metadata for every cached fetch, enabling later comparison reports to pull from disk instead of live re-fetching.
- **Tests**: Run `python -m unittest tests.test_normalizer` to cover edge cases like broken HTML, short snippets with missing language, and fallback flows.

### Embedding & Clustering Pipeline
- **Prompt to share**: `Create the embedding + clustering module with deterministic fixtures`
- **Embedding provider**: `HashEmbeddingProvider` implements a deterministic hashing-based interface that can later be swapped for NVIDIA Triton or other GPU backends without touching the clustering logic.
- **Clustering**: `cluster_articles` groups normalized articles by cosine similarity **and** entity overlap, so narratives that mention the same actors stay together even if wording diverges.
- **Fixtures/tests**: `tests/test_embedding_cluster.py` ships deterministic article snippets to ensure clustering behavior is predictable in CI; just run `python -m unittest tests.test_embedding_cluster`.

### Bias & Censorship Scoring
- **Prompt to share**: `Implement deterministic bias scoring functions with tests`
- **Scoring engine**: `src.pipelines.bias_scoring.score_bias` evaluates each cluster’s state-aligned vs independent coverage counts, sentiment deltas (lexicon-based), and entity omissions to produce reproducible metrics.
- **Integration plan**: Feed `ArticleRecord` objects (with `metadata['state_aligned']` flags) from the clustering pipeline into `score_bias()` before presenting narratives in the report.
- **Tests**: `python -m unittest tests.test_bias_scoring` locks the heuristics to a known fixture so future tweaks remain deterministic.

### LangGraph Bias Explainer Agent
- **Prompt to share**: `Build LangGraph agent skeleton with bias scoring integration`
- **Tools**: The agent wires up `FetchSourcesTool`, `ClusterTool`, `BiasScoreTool`, `ValyuCrossCheckTool`, and `ExplainTool` so that every response follows the pipeline fetch → cluster → score → cross-check → explain.
- **Demo**: Run `python -m src.agents.bias_langgraph_agent` to see a console walkthrough that summarizes cached narratives, cites bias metrics, and mentions Valyu recall gains when available.
- **Reuse**: `BiasLangGraphAgent` can be embedded inside other services or CLI flows—its tools only operate on JSON payloads, so automation/scripting is straightforward.

### Observability (LangSmith & OpenTelemetry)
- **Prompt to share**: `Add LangSmith tracing and OTEL instrumentation to the pipeline`
- **LangSmith**: `observability/tracing.init_langsmith()` toggles `LANGCHAIN_TRACING_V2` on startup so every LangGraph run can be sent to LangSmith whenever `LANGCHAIN_API_KEY`/`LANGCHAIN_PROJECT` are configured.
- **OpenTelemetry**: `observability/tracing.otel_span()` wraps fetch, cluster, score, cross-check, and explanation steps. Spans default to console export, but you can plug in your own collector by adjusting the OTEL exporter in `observability/tracing.py`.
- **Result**: Running the agent (or the ingestion pipeline) now yields both LangSmith traces and OTEL spans, making it easier to inspect latency bottlenecks or recall calculations.
### Quick Start
```python
from src.agents.news_agent import NewsAgent

agent = NewsAgent(
    model_name="claude-3-5-sonnet",
    enable_search=True
)

# Research with structured output
result = agent.research_with_structure(
    "Latest AI developments November 2025",
    output_format="bullet_points"
)

print(result['response'])
```

## 📊 Architecture Improvements

### 1. **Configuration Management**
- Environment-based configuration
- Validation and defaults
- Runtime config updates

### 2. **Metrics & Monitoring**
```python
# Get performance stats
metrics = agent.get_performance_metrics()
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Avg response time: {metrics['average_response_time']:.2f}s")
```

### 3. **Structured Research**
```python
# Different output formats
agent.research_with_structure(query, "summary")      # Concise overview
agent.research_with_structure(query, "bullet_points") # Key facts
agent.research_with_structure(query, "sources_only")  # Source citations
agent.research_with_structure(query, "detailed")      # Comprehensive analysis
```

### 4. **Advanced Error Handling**
- Automatic retry window
- Timeout management
- Graceful degradation
- Detailed error reporting

### 5. **Conversation Management**
```python
# Multi-turn conversations
agent.chat([
    {"role": "user", "content": "What are AI agents?"},
    {"role": "user", "content": "How do they compare to traditional AI?"}
])

# Reset conversation
agent.reset_conversation()
```

## 🔧 API Reference

### NewsAgent Class

#### Initialization
```python
NewsAgent(
    model_name="claude-3-5-sonnet",  # LLM model
    enable_search=True,              # Enable Valyu search
    timeout=30                       # Request timeout
)
```

#### Core Methods
- `research(query)` - Basic research query
- `research_with_structure(query, format)` - Structured output research
- `chat(messages)` - Multi-turn conversation
- `get_performance_metrics()` - Performance statistics
- `get_agent_status()` - Agent health check
- `reset_conversation()` - Clear conversation history

## 🧪 Testing

### Run Basic Test
```bash
python src/agents/news_agent.py
```

### Run Diagnostic Test
```bash
python test_agent.py
```

### Test Structured Output
```python
agent = NewsAgent()
result = agent.research_with_structure(
    "AI agent frameworks 2025",
    "bullet_points"
)
```

## 📈 Performance Metrics

The agent tracks:
- **Query Success Rate**: Percentage of successful research queries
- **Response Times**: Average time per query
- **Tool Usage**: Which tools are used most frequently
- **Error Types**: Common failure patterns
- **Conversation Length**: Multi-turn engagement metrics

## 🔄 Resilience Strategy

- Holistic AI Bedrock as the single provider
- Configurable retry counts for transient failures
- Graceful failure responses when errors persist

## 🎯 Next Steps for Team Integration

### Person 2: Custom Tools Development
- Add news scraping tools
- Implement fact-checking utilities
- Create summarization tools

### Person 3: Integration & Testing
- Connect to web interfaces
- Add comprehensive test suites
- Implement monitoring dashboards

### Person 4: Documentation & Demo
- Create demo applications
- Build presentation materials
- Document API usage

## 🚀 Production Readiness

- ✅ Error handling and logging
- ✅ Configuration management
- ✅ Performance monitoring
- ✅ Modular architecture
- ✅ Retry strategies
- ✅ Comprehensive testing

---

**Built for The Great Agent Hack 2025** - Demonstrating advanced agent architecture principles with production-ready features.
