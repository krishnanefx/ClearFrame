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

### Offline demo (no API keys, no network)

Runs the deterministic bias scoring and coverage radar on five synthetic sample articles in [`demo/sample_articles.json`](demo/sample_articles.json), then checks the result against the recorded output in [`demo/expected_output.json`](demo/expected_output.json). It needs only Python 3.9+ and TextBlob.

```bash
git clone https://github.com/krishnanefx/ClearFrame.git
cd ClearFrame
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-demo.txt
python demo/run_demo.py
```

Output:

```
Query: city council transit fare increase  (5 sample articles)

source                             lean     category emotion sensat. propag. overall     topic
metro-ledger.example                0.0      neutral     0.0     0.0     0.0     0.0      tech
peoples-voice.blog.example          0.0      neutral   100.0    40.0     0.0     2.0      tech
free-enterprise-daily.example       0.0      neutral    79.5     0.0     0.0     2.0      tech
commuter-guide.example              0.0      neutral     0.0     0.0     0.0     0.0      tech
labour-wire.example                 0.0      neutral   100.0     0.0     0.0     2.0      tech

Lean counts: 0 left, 5 neutral, 0 right
Coverage radar: omission score 30.0 (low), topics seen: diplomacy, economy, governance, humanitarian, protest
  independent    4 article(s), misses: none
  diaspora_blog  1 article(s), misses: economy, governance, humanitarian

Note: 5 article(s) were tagged as a non-political topic, so their lean was set to 0 without scoring.
The topic check matches substrings, so "ai" inside words like "said" counts as tech: see Known issues in the README.

Scores are keyword/lexicon heuristics, not validated measurements: see the Evaluation section of the README.

OK: full output matches demo/expected_output.json
```

The demo skips the parts that need keys: article retrieval (Valyu) and the LLM-written summaries. Every article's lean shows 0 here because of a topic-detection bug, described under [Known issues](#known-issues).

### Full pipeline (needs API keys)

```bash
pip install -r backend/requirements.txt
```

The API needs these keys. Create `.env` in the project root (`config/.env` is also read):

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

On a clean install (Python 3.12) the full requirements install, `python -m backend.api_server` starts, and `GET /health` responds without keys. The analysis endpoints and the CLI need valid Valyu and HolisticAI keys. They were not re-tested in this cleanup.

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

The React/Vite front end used at the hackathon (`frontend/factflow-ui`) was never committed to this repository. Use the API, CLI, Streamlit app or radar dashboard above.

### Cache warming

With the API running, pre-compute the demo prompts:

```bash
./scripts/warm_demo_cache.sh          # all demo prompts
python backend/warm_cache_smart.py    # only prompts missing from the cache
```

---

## Evaluation

ClearFrame's political-lean score (`detect_political_lean_enhanced` in `src/analysis/bias_metrics.py`) was compared against human labels. **It does not beat a trivial baseline.** Treat lean scores as illustrative, not as measurements.

**Data.** The media-split test set of [Article-Bias-Prediction](https://github.com/ramybaly/Article-Bias-Prediction) (Baly et al., EMNLP 2020): 1,300 news articles labelled left / center / right by AllSides (402 left, 299 center, 599 right), from outlets that are not in that dataset's training split. No article text is committed here. The script downloads it on first run.

**Method.** Each article is scored as ClearFrame scores a search result, on title plus description. "Snippet" uses the title and the first 500 characters of the body, close to what search returns. "Full text" uses the whole body. Scores below -5 count as left, above 5 as right, and everything else as center, the same thresholds ClearFrame uses for its left/neutral/right counts.

**Baselines.** *Majority class* always predicts "right", the most common label. *Keyword baseline* is the nine-keyword fallback heuristic from `calculate_bias_score` in `backend/basic_cli.py`.

```bash
pip install -r requirements-demo.txt
python evaluation/evaluate_bias.py    # writes evaluation/results.json
```

| System | Input | Accuracy | Macro-F1 | Recall L / C / R |
|---|---|---|---|---|
| ClearFrame lean score | snippet | 0.268 | 0.218 | 0.04 / 0.82 / 0.15 |
| ClearFrame lean score | full text | 0.317 | 0.284 | 0.09 / 0.53 / 0.37 |
| Keyword baseline | snippet | 0.270 | 0.206 | 0.07 / 0.96 / 0.07 |
| Keyword baseline | full text | 0.307 | 0.293 | 0.20 / 0.73 / 0.17 |
| Majority class ("right") | – | 0.461 | 0.210 | 0 / 0 / 1 |
| Always "center" | – | 0.230 | 0.125 | 0 / 1 / 0 |

Per-article predictions and confusion matrices are in [`evaluation/results.json`](evaluation/results.json).

**Examples it gets wrong** (snippet input; IDs refer to the dataset):

| ID | Outlet | Label | Score | Why |
|---|---|---|---|---|
| `SqLNY3j1qxchW0v7` | Salon | left | +30.7 (right) | One "liberal" keyword adds +5 toward right (sign bug below), and framing patterns add +18 |
| `oRgUtBo9oi2WziJw` | Reason | right | −30.2 (left) | Matches on right-side intensity keywords are pushed left by the same sign bug |
| `Ga5fn4vIxGAbfTfX` | Reuters | center | +21.1 (right) | No lean keywords at all. Framing patterns (+18) and sentiment (+3) alone cross the threshold |

In addition, 460 of 1,300 articles (35%) get no score: they are tagged as a non-political topic and forced to 0. See below.

**Limits.**
- AllSides labels largely follow the outlet's overall rating, so they measure "which side published this" more than the slant of the text. A text-only lexicon cannot recover much of that signal.
- ClearFrame only ever sees title plus description, which is short. Scoring the full text does better, but is still below the majority baseline on accuracy.
- This set has 1,300 articles from 2010s US outlets. It says nothing about non-US coverage, conflict reporting or non-English sources, which ClearFrame targets.
- Only the lean dimension is evaluated. Emotional-manipulation, sensationalism, propaganda and coverage-radar scores have no labelled evaluation.

## Known issues

Found by the evaluation above, and **not fixed** in this repository:

1. **Keyword term has the wrong sign.** `analyze_keywords_with_context` returns `keyword_balance = left − right`, and `detect_political_lean_enhanced` adds it to a score where positive means right. Left keywords push articles right, and right keywords push them left. The existing test `tests/test_consistency.py::test_political_lean_calculation` fails for this reason (it expects a negative score and gets +11.0).
2. **Topic check matches substrings.** `detect_topic_category` tests `kw in text`, so "ai" matches "said" or "against", and "app" matches "happen". Articles tagged as tech, sports, entertainment or science are forced to a lean of 0. This hits 35% of the evaluation set and all five demo articles.
3. `"extreme"` is listed as an intensity keyword for both sides.

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
demo/                    # Offline demo: sample articles, recorded output, run_demo.py
evaluation/              # Lean-score evaluation script and results.json
src/
  analysis/              # Bias metrics & advanced bias detection
  observability/         # Instrumentation, traces, dashboards, failure analysis
  utils/                 # Config loader, retry handler, frugal-AI helpers
config/config.yaml       # Default settings
docs/                    # Setup/deployment/track docs, radar HTML dashboard, assets
tests/                   # Consistency, bias-metric and load tests
tutorials/               # Hackathon notebooks + holistic_ai_bedrock.py (LLM client)
scripts/                 # warm_demo_cache.sh
docker-compose.yml
```

---

## Testing

```bash
pip install -r backend/requirements.txt
pytest tests/test_consistency.py tests/test_bias_metrics_dashboard.py -v

# Load testing (requires: pip install locust)
locust -f tests/test_load.py --host=http://localhost:5001
```

On a clean Python 3.12 install without API keys, 16 of these 20 tests pass. Three dashboard tests fail because they call the LLM-backed grandma brief, which needs HolisticAI credentials. `test_political_lean_calculation` fails because of known issue 1.

---

## Deployment

`docker-compose.yml` defines one `api` service, built from `backend/Dockerfile` on port 5001, with `./data` mounted for the caches. The old `ui` service, which built the missing React front end, has been removed. The Docker setup has not been tested since this cleanup.

See `docs/PRODUCTION_DEPLOYMENT.md` and `docs/CACHE_WARMING.md` for more detail. `docs/FULLSTACK_SETUP.md` and `docs/INTEGRATION_SUMMARY.md` describe the React front end, which is not in this repository.

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
