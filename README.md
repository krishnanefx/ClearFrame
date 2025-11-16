# FactFlow: News Bias & Coverage Analyzer

Full‑stack application (Flask API + Vite/React frontend) for multi‑source news retrieval, bias & coverage analysis, and observability metrics. Built for The Great Agent Hack 2025.

## Features

- 🔍 **Real-time News Search** - Search news from multiple sources using Valyu API
- 🤖 **AI-Powered Analysis** - Analyze articles using HolisticAI Claude 3.5
- 📊 **Bias Detection** - Calculate sentiment and detect potential bias
- 💡 **Smart Recommendations** - Get suggestions for balanced information
- 📰 **Multi-Source Support** - Compare coverage across different news sources

git clone https://github.com/krishnanefx/TheGreatAgentHack.git
## Quick Start (Full Stack)

### 1. Clone & Environment

```bash
git clone https://github.com/krishnanefx/TheGreatAgentHack.git
cd TheGreatAgentHack
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure Credentials

Create `.env` in the project root (or edit existing):

```bash
VALYU_API_KEY=your_valyu_api_key
HOLISTIC_AI_TEAM_ID=your_team_id
HOLISTIC_AI_API_TOKEN=your_api_token
# Optional fast LLM override
# FAST_LLM_MODEL=us.anthropic.claude-3-5-haiku-20241022-v1:0
```

Frontend API target is auto‑synced by `start.sh` via `factflow-ui/.env (VITE_API_URL=...)`.

### 3. Start Both Services

```bash
chmod +x start.sh
./start.sh                 # Uses API_PORT=5001 FRONTEND_PORT=5173 by default

# Override ports (optional):
API_PORT=5010 FRONTEND_PORT=5200 ./start.sh
```

Access:
- API: `http://localhost:<API_PORT>/health`
- Frontend UI: `http://localhost:<FRONTEND_PORT>`

### 4. Direct Backend Only (Optional)

```bash
API_PORT=5001 python api_server.py
```

### 5. CLI Mode (Deterministic JSON)

```bash
python basic_cli.py --query "sudan war" --json-only --output-file result.json
cat result.json | jq '.bias_analysis.aggregate_stats.average_scores'
```

## Frontend Usage

1. Enter a topic (e.g., “sudan war”, “AI regulation”).
2. Click Analyze – frontend calls `/api/analyze` (Flask) with deterministic coverage + bias pipeline.
3. View: status assessment, confidence, explanation, source list & bias metrics (omission, sentiment delta, loaded language, censorship radar, source diversity).
4. Toggle Grandma Mode for simplified accessibility styling.

## Source Categories

- **All Sources** - Search across all available sources
- **Independent** - BBC, The Guardian, Reuters, Associated Press
- **Mainstream US** - CNN, Fox News, New York Times
- **State-Aligned** - China Daily, RT, Xinhua
- **Custom** - Add your own sources

## Project Structure (Key Paths)

```
api_server.py                # Flask API (health, /api/analyze, /api/search)
basic_cli.py                 # Deterministic CLI pipeline & benchmarks
start.sh                     # Unified startup script (API + Vite frontend)
factflow-ui/                 # Vite + React + Tailwind frontend
	src/pages/Index.tsx        # Entry page calling /api/analyze
	src/components/            # UI + metrics visualization components
src/analysis/bias_metrics.py # Deterministic per-article bias engine
src/observability/           # Emissions + latency instrumentation
config/config.yaml           # Override defaults
tests/                       # Deterministic + coverage unit tests
```

## Requirements

- Python 3.9+
- Flask + flask-cors
- LangChain / langchain-valyu / langgraph
- HolisticAI access (Claude family models)
- Valyu API key
- Node 18+ (frontend)

## Pricing

Valyu Search API uses tiered pricing based on data source type:
- **Open Databases**: $0.50 per 1k retrievals (arXiv, Wikipedia, PubMed)
- **Web Search**: $1.50 per 1k retrievals (news, blogs, general web)
- **Financial & Market Data**: $8.00 per 1k retrievals (stocks, crypto, markets)
- **Proprietary Databases**: $30-50 per 1k retrievals (journals, premium content)

See [PRICING.md](PRICING.md) for detailed pricing information and cost management tips.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: flask` | Activate venv; run `pip install -r requirements.txt` |
| 404 on `/api/analyze` | Ensure `api_server.py` running & `VITE_API_URL` matches API_PORT |
| Port already in use | Change `API_PORT` env or free process (`lsof -i :5001`) |
| Slow responses | Enable fast mode in CLI (`--fast-mode`) or lower `max_results` |
| Missing advanced analysis | Set `ENABLE_ADVANCED_ANALYSIS=true` in environment |
| Determinism tests failing | Avoid modifying core tokenization or random functions |

### Regenerating Frontend Env
`VITE_API_URL` is auto‑written by `start.sh`. If manually changing ports:
```bash
echo "VITE_API_URL=http://localhost:5010" > factflow-ui/.env
```

### Running Tests
```bash
source .venv/bin/activate
pytest tests/test_bias_metrics_dashboard.py tests/test_consistency.py -q
```

## Contributing

See [contributing.md](contributing.md) for guidelines.

---

**Built for The Great Agent Hack 2025**  
*Powered by Valyu Search + HolisticAI*

---
Maintainers: @krishnanefx

Production note: Use a WSGI server (gunicorn/uwsgi) and proper caching layer for scaling beyond hackathon scope.
