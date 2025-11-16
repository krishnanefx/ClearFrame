"""FastAPI Radar Server

Serves censorship radar dashboard JSON directly to frontend.
Run:
  uvicorn radar_server:app --host 127.0.0.1 --port 8000 --reload
Then open clearframe_frontend.html (which will query /radar?query=...).
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Reuse existing search + dashboard logic
from .basic_cli import run_valyu_search, fetch_with_category_coverage
from src.analysis.bias_metrics import build_dashboard_payload, generate_grandma_brief

app = FastAPI(title="Censorship Radar API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/radar")
async def radar(
    query: str = Query(..., description="News/topic query"),
    max_results: int = Query(5, ge=1, le=20),
    response_length: str = Query("medium", regex="^(small|medium|large)$"),
    fast_mode: bool = Query(False),
):
    # Use coverage-aware ingestion to guarantee class presence
    per_class_min = max(1, min(3, max_results // 2))
    covered_articles, ingestion_meta = fetch_with_category_coverage(query, total_max=max_results, per_class_min=per_class_min, response_length=response_length)
    dashboard = build_dashboard_payload(covered_articles)
    dashboard["ingestion_summary"] = ingestion_meta
    return {
        "query": query,
        "results": len(covered_articles),
        "cost_usd": ingestion_meta.get("total_cost_usd"),
        "dashboard": dashboard,
    }

@app.get("/brief")
async def brief(
    query: str = Query(..., description="News/topic query"),
    max_results: int = Query(5, ge=1, le=20),
    response_length: str = Query("medium", regex="^(small|medium|large)$"),
):
    covered_articles, ingestion_meta = fetch_with_category_coverage(query, total_max=max_results, per_class_min=max(1, min(3, max_results // 2)), response_length=response_length)
    text_brief = generate_grandma_brief(covered_articles, query)
    return {
        "query": query,
        "results": len(covered_articles),
        "brief": text_brief,
        "cost_usd": ingestion_meta.get("total_cost_usd"),
        "ingestion_summary": ingestion_meta,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("radar_server:app", host="127.0.0.1", port=8000, reload=True)
