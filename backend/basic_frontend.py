"""
Valyu + HolisticAI Frontend — refined, quiet UI.
Run with: streamlit run basic_frontend.py
Design goals: calm, crisp, minimal chrome while keeping advanced controls close.
"""

from __future__ import annotations

import json
import os
from typing import List, Optional, Tuple

import streamlit as st

from .basic_cli import (
    analyze_agent,
    analyze_debate,
    analyze_pipeline,
    analyze_structured,
    run_valyu_search,
    Config,
    mask,
)


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
_APPLE_CSS = """
<style>
/* Reset */
.block-container {padding: 1.4rem 1.6rem 2.6rem;}
header, footer {visibility: hidden;}
html, body, [class*="css"]  {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif;
    color: #0f1115;
    background: #f7f8fb;
}

/* Cards */
.panel {
    background: #ffffffeb;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    box-shadow: 0 8px 24px rgba(15,17,26,0.06);
}

.pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 999px;
    background: #0f172a;
    color: #f8fafc;
    font-weight: 600;
    font-size: 0.85rem;
}

.article-card {
    padding: 14px 16px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
    background: linear-gradient(180deg, #fff, #f9fafb);
}

.article-title {font-weight: 700; font-size: 1rem; margin-bottom: 4px;}
.article-meta {color: #6b7280; font-size: 0.9rem;}
.spacer {height: 6px;}
</style>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_sources(raw: str) -> Optional[List[str]]:
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


def _env_status() -> List[str]:
    valyu = os.getenv("VALYU_API_KEY")
    team = os.getenv("HOLISTIC_AI_TEAM_ID")
    token = os.getenv("HOLISTIC_AI_API_TOKEN")
    return [
        f"VALYU_API_KEY · {'set' if valyu else 'missing'} · {mask(valyu)}",
        f"HOLISTIC_AI_TEAM_ID · {'set' if team else 'missing'} · {mask(team)}",
        f"HOLISTIC_AI_API_TOKEN · {'set' if token else 'missing'} · {mask(token)}",
    ]


def _render_metrics(search: dict, articles: List[dict]) -> None:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Results Returned", f"{len(articles)}/{search.get('total_results', len(articles))}")
    with col2:
        st.metric("Search Type", search.get("search_type", "all").title())
    with col3:
        st.metric("Response Length", search.get("response_length", "large").title())


def _render_articles(articles: List[dict]) -> None:
    st.markdown("### Curated Results")
    for a in articles[:12]:
        with st.container():
            st.markdown(
                f"""<div class="article-card">
                    <div class="article-title">{a.get('title','Untitled')}</div>
                    <div class="article-meta">{a.get('source','unknown')} · {a.get('url','')}</div>
                    <div class="spacer"></div>
                    <div>{a.get('description','')}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            st.markdown("")


# ---------------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="Valyu Deepsearch · Glass",
        page_icon="📰",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_APPLE_CSS, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="panel" style="padding:16px 20px; margin-bottom:16px;">
            <div class="pill">Valyu Deepsearch · HolisticAI</div>
            <h1 style="margin:8px 0 4px;">Quiet control. Strong signals.</h1>
            <p style="color:#475569; font-size:0.95rem;">Search, analyze, and contrast narratives with a restrained, focused surface.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Environment status", expanded=False):
        for line in _env_status():
            st.markdown(f"- {line}")

    # Search + filters
    with st.container():
        st.markdown("### Search & Filters")
        form = st.form("search_form")
        q_col, mode_col, fast_col = form.columns([3, 1, 1])
        query = q_col.text_input("Topic / Query", value="", placeholder="e.g. AI regulation, climate summit outcomes", label_visibility="collapsed")
        search_type = mode_col.selectbox("Search type", ["all", "web", "proprietary"], index=0)
        fast_mode = fast_col.toggle("Fast mode", value=False)

        row2 = form.columns(4)
        sources_input = row2[0].text_input("Preferred sources (comma-separated)", value="")
        response_length = row2[1].selectbox("Response length", ["small", "medium", "large"], index=2)
        relevance_threshold = row2[2].slider("Relevance threshold", 0.0, 1.0, 0.0, 0.05)
        max_results = row2[3].slider("Max results", 3, 20, 8)

        row3 = form.columns(4)
        start_date = row3[0].text_input("Start date (ISO or -7d)", value="")
        end_date = row3[1].text_input("End date (ISO or today)", value="")
        include_sources = row3[2].text_input("Include sources (comma-separated)", value="")
        exclude_sources = row3[3].text_input("Exclude sources (comma-separated)", value="")

        row4 = form.columns(2)
        category = row4[0].text_input("Category hint", value="")
        country_code = row4[1].text_input("Country code (US, GB, FR...)", value="")

        submitted = form.form_submit_button("Run Valyu search", use_container_width=True)

    if submitted and not query:
        st.error("Please provide a topic/query.")
        return

    if submitted:
        config = Config()
        sources = _parse_sources(sources_input)
        included_sources = _parse_sources(include_sources)
        excluded_sources = _parse_sources(exclude_sources)
        date_from = config.parse_date(start_date) if start_date else None
        date_to = config.parse_date(end_date) if end_date else None

        with st.spinner("Searching Valyu..."):
            search = run_valyu_search(
                query=query,
                sources=sources,
                search_type=search_type,
                max_results=max_results,
                relevance_threshold=relevance_threshold,
                max_price=None,
                language=None,
                region=None,
                date_from=date_from,
                date_to=date_to,
                response_length=response_length,
                fast_mode=fast_mode,
                included_sources=included_sources,
                excluded_sources=excluded_sources,
                category=category or None,
                country_code=country_code or None,
                is_tool_call=True,
            )

        articles = search.get("results", [])
        if not articles:
            st.warning("No articles returned. Adjust your query or filters.")
            st.json(search)
            return

        st.success(f"Returned {len(articles)} articles")
        _render_metrics(search, articles)
        _render_articles(articles)

        # Analysis tabs
        st.markdown("### Analysis Modes")
        tab_pipeline, tab_agent, tab_structured, tab_debate = st.tabs(
            ["Pipeline", "Agent (tools)", "Structured JSON", "Debate"]
        )

        with tab_pipeline:
            with st.spinner("Running pipeline analysis..."):
                analysis = analyze_pipeline(query, articles)
            st.write(analysis)

        with tab_agent:
            st.caption("Select custom tools (empty = auto-detect).")
            tool_choices = st.multiselect(
                "Agent tools",
                ["bias", "credibility", "conflict", "corruption", "fact_check", "citations", "language", "nlp_bias"],
            )
            trigger = st.button("Run agent", key="agent_run")
            if trigger:
                with st.spinner("Running agent..."):
                    analysis, trace_msgs = analyze_agent(
                        query=query,
                        sources=sources,
                        trace=False,
                        custom_tools=tool_choices or None,
                        config=config,
                    )
                st.write(analysis)
                if trace_msgs:
                    with st.expander("Agent trace (messages)"):
                        for idx, msg in enumerate(trace_msgs, 1):
                            st.markdown(f"{idx}. `{type(msg).__name__}`: {getattr(msg, 'content', msg)}")

        with tab_structured:
            with st.spinner("Running structured analysis..."):
                report = analyze_structured(query, articles)
            st.json(report.model_dump())

        with tab_debate:
            with st.spinner("Running debate synthesis..."):
                result = analyze_debate(query, sources, trace=False)
            try:
                st.json(json.loads(result))
            except Exception:
                st.write(result)


if __name__ == "__main__":
    main()
