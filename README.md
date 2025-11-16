# ClearFrame

**Multi-source news aggregation and bias analysis platform with real-time observability.**

ClearFrame retrieves news from diverse sources, analyzes bias patterns across political spectrums, and surfaces coverage gaps. Built with Flask, React, LangChain, and Claude AI models, it provides deterministic bias scoring, propaganda detection, and narrative clustering for journalists, researchers, and news consumers.

---

## Features

- **Multi-Source Aggregation** – Retrieves articles from web sources via Valyu Search API with configurable filters
- **Bias Analysis** – Per-article scoring for political lean, sensationalism, propaganda techniques, emotional/factual language balance
- **Coverage Assessment** – Identifies narrative clusters, omission patterns, and political spectrum representation
- **Credibility Scoring** – Classifies sources by reliability tier and source type (mainstream, independent, state-backed)
- **Observability** – LangSmith integration with cost tracking, emissions monitoring, and latency metrics
- **Accessible Interface** – React UI with Grandma Mode for simplified summaries and readable styling
- **CLI & API** – Headless analysis via command line or HTTP endpoints for integration

---

## Installation

### Prerequisites

- **Python 3.9+** (backend)
- **Node.js 18+** (frontend)
- **API Keys**:
  - [Valyu API](https://valyu.ai) for news search
  - [HolisticAI](https://holisticai.com) for LLM access (Claude models)

### Setup

```bash
# Clone repository
git clone https://github.com/krishnanefx/TheGreatAgentHack.git
cd TheGreatAgentHack

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### Environment Configuration

Create `.env` in the project root:

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
FRONTEND_PORT=5173
```

---

## Usage

### Full Stack (Recommended)

Start both API server and frontend:

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

Access the application at `http://localhost:5173`

**Custom Ports:**
```bash
API_PORT=8000 FRONTEND_PORT=3000 ./scripts/start.sh
```

### API Server Only

```bash
python -m backend.api_server
```

Server runs at `http://localhost:5001` (or `$API_PORT`)

**Test the API:**
```bash
curl http://localhost:5001/health

curl -X POST http://localhost:5001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "climate policy 2024", "max_results": 9}'
```

### Command Line Interface

Run deterministic analysis and export JSON:

```bash
python -m backend.basic_cli \
  --query "sudan war" \
  --max-results 9 \
  --json-only \
  --output-file analysis.json
```

**CLI Options:**
```
--query TEXT            Search query (required)
--max-results INT       Articles to retrieve (default: 9)
--search-type TEXT      web|proprietary|all (default: web)
--response-length TEXT  short|medium|large|max (default: large)
--json-only             Output only JSON results
--output-file PATH      Save results to file
--fast-mode             Use faster, lightweight LLM
--enable-advanced       Enable advanced narrative analysis
```

### Frontend Development

```bash
cd frontend/factflow-ui
npm install
npm run dev
```

Ensure backend is running and `VITE_API_URL` in `frontend/factflow-ui/.env` points to the API server.

---

## API Reference

### Endpoints

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### `POST /api/analyze`
Analyze news coverage and bias for a query.

**Request:**
```json
{
  "query": "AI regulation Europe",
  "max_results": 9,
  "search_type": "web",
  "response_length": "large",
  "enable_advanced": false
}
```

**Response:**
```json
{
  "summary": "Analyzed 9 articles from 7 sources...",
  "status": "success",
  "confidence": 0.85,
  "metrics": {
    "bias_distribution": {...},
    "propaganda_summary": {...},
    "coverage_balance": {...}
  },
  "articles": [...],
  "observability": {
    "latency_ms": 3420,
    "llm_calls": 12,
    "cost_usd": 0.0234
  }
}
```

#### `POST /api/search`
Retrieve raw articles without analysis.

**Request:**
```json
{
  "query": "ukraine conflict",
  "max_results": 10,
  "search_type": "web",
  "sources": ["bbc.com", "reuters.com"]
}
```

---

## Configuration

Edit `config/config.yaml` to customize defaults:

```yaml
valyu:
  search_type: "web"
  max_results: 9
  response_length: "large"
  preferred_sources: "bbc.com,reuters.com,aljazeera.com,apnews.com"

llm:
  model: "claude-3-5-sonnet"
  temperature: 0.1
  max_tokens: 3072

analysis:
  default_mode: "agent"
  auto_detect_tools: true
  include_trace: false
```

Override via environment variables or API request parameters.

---

## Architecture

```
┌─────────────────────────┐
│  Frontend (React/Vite)  │  Port 5173
│  - Analysis Dashboard   │
│  - Grandma Mode         │
└───────────┬─────────────┘
            │ HTTP
            ▼
┌─────────────────────────┐
│   API Server (Flask)    │  Port 5001
│   - /api/analyze        │
│   - /api/search         │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Analysis Engine       │
│   - Bias scoring        │
│   - Narrative clustering│
│   - LangChain pipeline  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  External Services      │
│  - Valyu Search API     │
│  - HolisticAI (Claude)  │
└─────────────────────────┘
```

**Project Structure:**
```
backend/
  api_server.py        # Flask REST API
  basic_cli.py         # Analysis engine & CLI
  factchecking.py      # RSS feed utilities
src/analysis/          # Bias detection modules
src/observability/     # Tracing & emissions tracking
frontend/factflow-ui/  # React application
config/config.yaml     # Default settings
tests/                 # Unit & consistency tests
scripts/start.sh       # Unified startup script
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: flask` | Activate virtual environment: `source .venv/bin/activate`<br>Install dependencies: `pip install -r backend/requirements.txt` |
| API returns 404 | Verify backend is running at correct port<br>Check `VITE_API_URL` in `frontend/factflow-ui/.env` matches API port |
| Port already in use | Change port: `API_PORT=8000 ./scripts/start.sh`<br>Or kill existing process: `lsof -ti:5001 \| xargs kill -9` |
| Slow analysis times | Reduce `max_results` to 5-7<br>Enable fast mode: `--fast-mode` (CLI) or set `FAST_LLM_MODEL` env var |
| Missing bias metrics | Ensure `enable_advanced: true` in request or config |
| CORS errors | Verify `flask-cors` is installed<br>Check frontend is accessing correct API URL |
| Missing API keys | Confirm `.env` file exists in project root<br>Verify all required keys are set: `VALYU_API_KEY`, `HOLISTIC_AI_TEAM_ID`, `HOLISTIC_AI_API_TOKEN` |

**Regenerate Frontend Config:**
```bash
echo "VITE_API_URL=http://localhost:5001" > frontend/factflow-ui/.env
```

**Run Tests:**
```bash
source .venv/bin/activate
pytest tests/ -v
```

---

## Observability

ClearFrame integrates with LangSmith for production tracing:

- **Automatic tagging**: `mode:*`, `tool:*`, `model:*` tags on all traces
- **Cost tracking**: Per-span and aggregate token usage + USD costs
- **Emissions**: CO₂ footprint in grams per analysis
- **Error attribution**: `error_type` metadata for failed spans
- **UI metrics**: Compact observability bar shows API calls, LLM calls, latency, emissions

**Enable LangSmith:**
```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_PROJECT=clearframe-production
```

View dashboards at [smith.langchain.com](https://smith.langchain.com)

---

## Testing

Run deterministic consistency tests:

```bash
pytest tests/test_consistency.py -v
```

Load testing:
```bash
pytest tests/test_load.py
```

Bias metrics validation:
```bash
pytest tests/test_bias_metrics_dashboard.py
```

---

## Deployment

### Docker

Build and run via Docker Compose:

```bash
docker-compose up --build
```

Services start on ports defined in `docker-compose.yml`

### Production Checklist

- [ ] Set all environment variables in production environment
- [ ] Use production-grade WSGI server (gunicorn, uWSGI) instead of Flask dev server
- [ ] Enable HTTPS/TLS for API endpoints
- [ ] Implement rate limiting and authentication
- [ ] Configure CORS allowed origins explicitly
- [ ] Set up log aggregation (CloudWatch, Datadog, etc.)
- [ ] Enable LangSmith tracing with production project name
- [ ] Monitor API response times and error rates

See `docs/PRODUCTION_DEPLOYMENT.md` for detailed deployment guide.

---

## Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes with clear messages
4. Add tests for new functionality
5. Submit a pull request

See `docs/contributing.md` for guidelines.

---

## License

This project is part of The Great Agent Hack 2025.

---

## Credits

- **Valyu Search** – Multi-source news aggregation
- **HolisticAI** – Claude model access for analysis
- **LangChain** – Agent orchestration framework
- **LangSmith** – Observability and tracing

Built by [@krishnanefx](https://github.com/krishnanefx)
