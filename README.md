# ClearFrame: News Bias & Coverage Analyzer

Full‑stack app (Flask API + Vite/React frontend) for multi‑source news retrieval, bias coverage analysis, and observability. Built for The Great Agent Hack 2025.

## What’s Inside
- Backend (`backend/`): Flask API, deterministic bias engine, CLI, FastAPI radar server.
- Frontend (`frontend/factflow-ui/`): Vite + React + Tailwind UI.
- Core logic (`src/`): Bias metrics, observability, utilities.
- Docs (`docs/`): Deployment, integration notes, dashboards, assets.

## Quick Start
```bash
git clone https://github.com/krishnanefx/TheGreatAgentHack.git
cd TheGreatAgentHack
python -m venv .venv && source .venv/bin/activate   # macOS/Linux
pip install -r backend/requirements.txt
```

Create `.env` in repo root:
```bash
VALYU_API_KEY=your_valyu_api_key
HOLISTIC_AI_TEAM_ID=your_team_id
HOLISTIC_AI_API_TOKEN=your_api_token
# Optional fast LLM override:
# FAST_LLM_MODEL=us.anthropic.claude-3-5-haiku-20241022-v1:0
```

Start everything (auto-writes `frontend/factflow-ui/.env`):
```bash
chmod +x scripts/start.sh
./scripts/start.sh                 # API_PORT=5001, FRONTEND_PORT=5173
# Override: API_PORT=5010 FRONTEND_PORT=5200 ./scripts/start.sh
```
Access: API `http://localhost:<API_PORT>/health`, UI `http://localhost:<FRONTEND_PORT>`.

Run backend only:
```bash
API_PORT=5001 python -m backend.api_server
```

CLI example (deterministic JSON):
```bash
python -m backend.basic_cli --query "sudan war" --json-only --output-file result.json
```

## Repository Map
```
backend/                  # Python backend package & CLIs
  api_server.py           # Flask API (health, /api/analyze, /api/search)
  basic_cli.py            # Deterministic pipeline & benchmarks
  basic_frontend.py       # Streamlit playground
  radar_server.py         # FastAPI radar service
frontend/factflow-ui/     # Vite + React + Tailwind frontend
src/analysis/             # Bias metrics engine
src/observability/        # Emissions + latency instrumentation
config/config.yaml        # Default configuration
tests/                    # Deterministic + coverage unit tests
docs/                     # Deployment, integration, dashboards, assets
scripts/start.sh          # Unified startup script
```

## Requirements
- Python 3.9+
- Flask + flask-cors
- LangChain / langchain-valyu / langgraph
- HolisticAI access (Claude family models)
- Valyu API key
- Node 18+ (frontend)

## Frontend Usage
1) Enter a topic (e.g., “sudan war”, “AI regulation”).  
2) Click Analyze → calls `/api/analyze`.  
3) View status, confidence, sources, bias metrics (omission, sentiment delta, loaded language, censorship radar, source diversity).  
4) Toggle Grandma Mode for simplified styling.

## Troubleshooting
| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: flask` | Activate venv; run `pip install -r backend/requirements.txt` |
| 404 on `/api/analyze` | Ensure `backend.api_server` is running & `VITE_API_URL` matches API_PORT |
| Port already in use | Change `API_PORT` or free the port (`lsof -i :5001`) |
| Slow responses | Use CLI `--fast-mode` or lower `max_results` |
| Missing advanced analysis | Set `ENABLE_ADVANCED_ANALYSIS=true` |
| Determinism tests failing | Avoid changing tokenization/random functions |

Regenerate frontend env manually (if needed):
```bash
echo "VITE_API_URL=http://localhost:5010" > frontend/factflow-ui/.env
```

Run tests:
```bash
source .venv/bin/activate
pytest tests/test_bias_metrics_dashboard.py tests/test_consistency.py -q
```

See [docs/contributing.md](docs/contributing.md) for contributions and [PRICING.md](PRICING.md) for Valyu pricing.

---
Built for The Great Agent Hack 2025 • Powered by Valyu Search + HolisticAI
