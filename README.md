# ClearFrame

![ClearFrame – Snap into clarity.](docs/assets/Copilot_20251116_005642.png)

**Multi-source news aggregation and bias analysis with built-in observability.**

ClearFrame retrieves news from diverse sources, analyzes bias patterns across the political spectrum, and surfaces coverage gaps. It combines the Valyu Search API, LangChain/LangGraph and Claude models (via HolisticAI) with deterministic bias scoring, propaganda detection and narrative clustering, aimed at journalists, researchers and everyday news readers.

Built for [The Great Agent Hack 2025](https://github.com/holistic-ai/hackathon-2025) (Track A: Agent Iron Man and Track B: Agent Glass Box).

---

## Features

- **Multi-source aggregation** – Article retrieval through Valyu Search with source, date, country and category filters
- **Bias analysis** – Per-article scoring for political lean, sensationalism, emotional vs. factual language and propaganda techniques
- **Coverage assessment** – Narrative clustering, omission detection, coverage matrix and a "censorship radar" across sources
- **Source classification** – Credibility tier and source type (mainstream, independent, state-backed)
- **Grandma Mode** – Plain-language summary ("grandma brief") of the technical metrics
- **Observability** – Optional LangSmith tracing, span-level instrumentation, latency/LLM-call counts and estimated CO₂ emissions per request
- **Caching** – Full-analysis and grandma-brief caches on disk (`data/analysis_cache/`, `data/grandma_cache/`), plus cache-warming scripts for demo prompts
- **Multiple interfaces** – Flask REST API, CLI, a Streamlit app, and a standalone HTML radar dashboard

---

## Quick Start

### Prerequisites

- Python 3.9+
- API keys: [Valyu](https://valyu.ai) (news search) and [HolisticAI](https://holisticai.com) (Claude model access)

### Install

```bash
git clone https://github.com/krishnanefx/ClearFrame.git
cd ClearFrame

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

### Environment

Create `.env` in the project root (`config/.env` is also read):

```bash
# Required
VALYU_API_KEY=your_valyu_api_key
HOLISTIC_AI_TEAM_ID=your_team_id
HOLISTIC_AI_API_TOKEN=your_api_token

# Optional
FAST_LLM_MODEL=us.anthropic.claude-3-5-haiku-20241022-v1:0
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=clearframe-analysis
API_PORT=5001
FLASK_DEBUG=false
ENABLE_ADVANCED_ANALYSIS=false
GOOGLE_FACT_CHECK_API_KEY=...     # only for the fact-check tool
```

---

## Usage

### API server

```bash
python -m backend.api_server     # http://localhost:5001 (or $API_PORT)
```

```bash
curl http://localhost:5001/health

curl -X POST http://localhost:5001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "climate policy 2024", "max_results": 9}'
```

### Command line

```bash
python -m backend.basic_cli \
  --query "sudan war" \
  --max-results 9 \
  --json-only \
  --output-file analysis.json
```

Common options (run `python -m backend.basic_cli --help` for all):

```
--query TEXT              Topic to research
--mode MODE               pipeline|agent|structured|conversation|debate|unified-deterministic
                          (default: unified-deterministic)
--max-results INT         Articles to retrieve (default: 5)
--search-type TEXT        all|web|proprietary (default: web)
--response-length TEXT    small|medium|large (default: large)
--sources / --include-sources / --exclude-sources   Comma-separated domains
--start-date / --end-date ISO date or relative (-7d, today)
--tools LIST              bias,credibility,conflict,corruption,fact_check,citations,
                          language,nlp_bias,narrative,evidence,propaganda
--fast-mode               Lower-latency Valyu retrieval
--benchmark-set NAME      standard_news|investigative|all
--metrics                 Print latency & emissions summary
--json-only               Print only the final JSON
--output-file PATH        Write JSON payload to file
```

### Other front-ends

```bash
# Streamlit app
PYTHONPATH=. streamlit run backend/basic_frontend.py

# Censorship radar: FastAPI server on :8000, then open docs/clearframe_frontend.html
uvicorn backend.radar_server:app --host 127.0.0.1 --port 8000
```

### React UI

`scripts/start.sh` starts the API together with a React/Vite UI from `frontend/factflow-ui` (port 5173). That directory is referenced as a git submodule, but no `.gitmodules` entry is committed, so it is **not included** when you clone this repository. Without it, use the API, CLI, Streamlit or radar dashboard above.

### Cache warming

With the API running, pre-compute the demo prompts:

```bash
./scripts/warm_demo_cache.sh          # all demo prompts
python backend/warm_cache_smart.py    # only prompts missing from the cache
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Returns `{"status": "healthy", "service": "FactFlow API"}` |
| `GET` | `/api/cache/status` | Cache state for the built-in demo prompts |
| `POST` | `/api/analyze` | Full bias/coverage analysis for a query |
| `POST` | `/api/search` | Raw article search, no analysis |

**`POST /api/analyze`**

```json
{
  "query": "AI regulation Europe",
  "max_results": 9,
  "search_type": "web",
  "response_length": "large",
  "enable_advanced": false
}
```

The response includes per-article bias analysis, the censorship-radar dashboard payload (`scale_of_censorship`, `severity`, `source_angle_cards`, `coverage_matrix_percent`, `omissions_diff`, …), the grandma brief and observability metrics. Results are cached by query.

**`POST /api/search`**

```json
{ "query": "ukraine conflict", "max_results": 10, "search_type": "web", "sources": ["bbc.com", "reuters.com"] }
```

Returns `query`, `article_count`, `articles` and `cost`.

---

## Configuration

Defaults live in `config/config.yaml` (Valyu search parameters, LLM model/temperature, enabled tools, analysis mode, retry policy, logging). CLI flags and API request fields override them.

---

## Project Structure

```
backend/
  api_server.py          # Flask REST API
  basic_cli.py           # Analysis engine & CLI
  basic_frontend.py      # Streamlit app
  radar_server.py        # FastAPI censorship-radar endpoint
  factchecking.py        # RSS feed utilities
  warm_cache*.py         # Cache warming
  samples/               # Sample/benchmark JSON payloads
  Dockerfile
src/
  analysis/              # Bias metrics & advanced bias detection
  observability/         # Instrumentation, traces, dashboards, failure analysis
  utils/                 # Config loader, retry handler, frugal-AI helpers
config/config.yaml       # Default settings
docs/                    # Setup/deployment/track docs, radar HTML dashboard, assets
tests/                   # Consistency, bias-metric and load tests
tutorials/               # Hackathon notebooks + holistic_ai_bedrock.py (LLM client)
scripts/                 # start.sh, warm_demo_cache.sh
docker-compose.yml
```

---

## Testing

```bash
pytest tests/test_consistency.py -v          # deterministic scoring
pytest tests/test_bias_metrics_dashboard.py  # dashboard metrics

# Load testing (requires: pip install locust)
locust -f tests/test_load.py --host=http://localhost:5001
```

---

## Deployment

`docker-compose.yml` defines an `api` service (built from `backend/Dockerfile`, port 5001) and a `ui` service. Note that the `ui` service builds from the missing `frontend/factflow-ui` directory, and the Dockerfile copies a `data/` directory that is created at runtime rather than committed, so both need to be present before `docker-compose up --build` will succeed.

See `docs/PRODUCTION_DEPLOYMENT.md`, `docs/FULLSTACK_SETUP.md` and `docs/CACHE_WARMING.md` for more detail.

---

## Hackathon Tracks

- **Track A – Agent Iron Man (reliability):** deterministic local bias scoring with LLMs reserved for synthesis and summaries, a fast Haiku model option, disk caching for repeat queries, retry handling, per-request latency/LLM-call/emissions metrics, and consistency and load tests. Details: `docs/TRACK_A_INTEGRATION.md`.
- **Track B – Agent Glass Box (transparency):** LangSmith tracing with mode/tool/model tags, span-level instrumentation, trace visualisation, a reasoning explainer and failure analyzer, and Grandma Mode summaries for non-technical readers. Details: `docs/TRACK_B_INTEGRATION.md`.

---

## Contributing

See `docs/contributing.md`.

---

## Credits

- **Valyu Search** – Multi-source news retrieval
- **HolisticAI** – Claude model access
- **LangChain / LangGraph** – Agent orchestration
- **LangSmith** – Tracing

Built by
[@krishnanefx](https://github.com/krishnanefx)
[@LCS3002](https://github.com/LCS3002)
[@kayaclaridge-sys](https://github.com/kayaclaridge-sys)
[@cheongbowen07](https://github.com/cheongbowen07)
[@fahmed01](https://github.com/fahmed01)
