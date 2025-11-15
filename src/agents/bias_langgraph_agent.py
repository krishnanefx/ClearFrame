"""LangGraph agent skeleton that uses cached sources, clustering, bias scoring, and Valyu cross-checks."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent

from ingestion import (
    CachedEntry,
    CachedSourceRepository,
    ValyuSearchGateway,
)
from pipelines.bias_scoring import score_bias
from pipelines.embedding_cluster import ArticleRecord, ClusterResult, cluster_articles
from utils.model_helper import get_chat_model
from observability.tracing import init_langsmith, otel_span


class BiasLangGraphAgent:
    """LangGraph ReAct agent with tools for fetch -> cluster -> bias scoring -> explain."""

    def __init__(
        self,
        default_limit: int = 4,
        max_preview_chars: int = 1200,
        model_name: str = "claude-3-5-sonnet",
    ):
        init_langsmith()
        self.logger = logging.getLogger(__name__)
        self.repo = CachedSourceRepository()
        self.default_limit = default_limit
        self.max_preview_chars = max_preview_chars
        self.llm = get_chat_model(model_name=model_name)
        self.valyu_gateway = ValyuSearchGateway()
        self.tools = [
            Tool(
                name="FetchSourcesTool",
                description=(
                    "Fetch the most recent cached articles as JSON. "
                    "Input: optional integer for how many items to fetch."
                ),
                func=self._fetch_sources,
            ),
            Tool(
                name="ClusterTool",
                description=(
                    "Cluster the provided articles JSON. "
                    "Input must be JSON from FetchSourcesTool. "
                    "Returns clusters with member metadata."
                ),
                func=self._cluster_articles,
            ),
            Tool(
                name="BiasScoreTool",
                description=(
                    "Compute bias/censorship metrics for clustered articles. "
                    "Input must be JSON returned by ClusterTool."
                ),
                func=self._bias_score,
            ),
            Tool(
                name="ValyuCrossCheckTool",
                description=(
                    "Call Valyu search to find supporting or contrasting articles. "
                    "Input must be JSON returned by FetchSourcesTool."
                ),
                func=self._valyu_cross_check,
            ),
            Tool(
                name="ExplainTool",
                description=(
                    "Produce a neutral explanation referencing the bias scores. "
                    "Input must be JSON returned by BiasScoreTool along with optional user context."
                ),
                func=self._explain_bias,
            ),
        ]
        self.system_prompt = (
            "You are a neutral censorship analyst. Your goal is to detect and report on potential state-aligned narrative control. "
            "Always call the tools in this order: "
            "1. FetchSourcesTool: Gather recent articles from the cache. "
            "2. ValyuCrossCheckTool: Use external search to find related articles and identify coverage gaps. "
            "3. ClusterTool: Group articles into narrative clusters. "
            "4. BiasScoreTool: Quantify bias metrics for each cluster. "
            "5. ExplainTool: Synthesize all findings into a neutral, evidence-based report. "
            "Do not speculate; cite quantitative metrics and tool outputs in your final explanation."
        )
        self.agent = create_react_agent(self.llm, tools=self.tools)

    # Tool implementations -------------------------------------------------
    def _fetch_sources(self, limit_text: str = "") -> str:
        with otel_span("FetchSourcesTool"):
            limit = self.default_limit
            if limit_text:
                try:
                    limit = max(1, int(limit_text))
                except ValueError:
                    pass

            entries = self.repo.get_recent_entries(limit=limit)
            if not entries:
                entries = self._fallback_entries(limit)

            payload: List[Dict[str, Any]] = []
            for entry in entries:
                text = entry.read_full_text() or " ".join(entry.text_preview)
                text = text[: self.max_preview_chars]
                state_flag = bool(entry.metadata.get("state_aligned"))
                payload.append(
                    {
                        "source_id": entry.source_id,
                        "language": entry.language or "unknown",
                        "state_aligned": state_flag,
                        "text": text,
                        "metadata": entry.metadata,
                    }
                )
            return json.dumps({"articles": payload}, ensure_ascii=False)

    def _cluster_articles(self, articles_json: str) -> str:
        with otel_span("ClusterTool"):
            try:
                parsed = json.loads(articles_json)
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON payload for ClusterTool"})

            articles = parsed.get("articles", [])
            records = [
                ArticleRecord(
                    source_id=item.get("source_id", "unknown"),
                    text=item.get("text", ""),
                    metadata={
                        "state_aligned": item.get("state_aligned", False),
                        "language": item.get("language"),
                    },
                )
                for item in articles
            ]

            if not records:
                return json.dumps({"clusters": []})

            clusters = cluster_articles(records)
            payload = {
                "clusters": [self._cluster_to_dict(cluster) for cluster in clusters],
            }
            return json.dumps(payload, ensure_ascii=False)

    def _bias_score(self, clusters_json: str) -> str:
        with otel_span("BiasScoreTool"):
            try:
                parsed = json.loads(clusters_json)
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON payload for BiasScoreTool"})

            results = []
            for cluster in parsed.get("clusters", []):
                members = [
                    ArticleRecord(
                        source_id=member.get("source_id", "unknown"),
                        text=member.get("text", ""),
                        metadata={
                            "state_aligned": member.get("state_aligned", False),
                            "language": member.get("language"),
                        },
                    )
                    for member in cluster.get("members", [])
                ]
                if not members:
                    continue
                bias = score_bias(members)
                results.append(
                    {
                        "cluster_id": cluster.get("cluster_id"),
                        "entities": cluster.get("entities", []),
                        "metrics": bias.as_dict(),
                    }
                )
            return json.dumps({"bias_scores": results}, ensure_ascii=False)

    def _valyu_cross_check(self, articles_json: str) -> str:
        with otel_span("ValyuCrossCheckTool"):
            try:
                parsed = json.loads(articles_json)
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON payload for ValyuCrossCheckTool"})

            articles = parsed.get("articles", [])
            if not articles:
                return json.dumps({"error": "No articles provided"})

            region_tags: Set[str] = set()
            query_fragments: List[str] = []
            for article in articles:
                metadata = article.get("metadata") or {}
                region_tags.update(metadata.get("region_tags", []))
                query_fragments.append(article.get("text", "")[:200])

            query = " ".join(query_fragments)[:600]
            result = self.valyu_gateway.search(query, region_tags=sorted(region_tags))
            ingestion_count = len(articles)
            valyu_hits = len(result.get("results", []))
            recall_gain = 0.0
            if ingestion_count:
                recall_gain = max(0, valyu_hits - ingestion_count) / ingestion_count
            elif valyu_hits:
                recall_gain = 1.0

            self.logger.info(
                "Valyu cross-check: ingestion=%d, valyu_hits=%d, recall_gain=%.2f, status=%s",
                ingestion_count,
                valyu_hits,
                recall_gain,
                result.get("status"),
            )

            payload = {
                "ingestion_count": ingestion_count,
                "valyu_hits": valyu_hits,
                "recall_gain": recall_gain,
                "region_tags": sorted(region_tags),
                "search_status": result.get("status"),
                "results": result.get("results", []),
            }
            return json.dumps(payload, ensure_ascii=False)

    def _explain_bias(self, payload_json: str) -> str:
        with otel_span("ExplainTool"):
            try:
                parsed = json.loads(payload_json)
            except json.JSONDecodeError:
                return "Invalid JSON payload for ExplainTool."

            scores = parsed.get("bias_scores", [])
            cross_check = parsed.get("cross_check_results", {})
            if not scores:
                return "No bias scores available to explain."

            lines = ["Neutral bias assessment based on available data:"]

            # Summarize cross-check findings first
            if cross_check:
                lines.append("\n**External Cross-Check (Valyu Search):**")
                lines.append(
                    f"- Ingested {cross_check.get('ingestion_count', 0)} articles, "
                    f"found {cross_check.get('valyu_hits', 0)} related articles externally."
                )
                recall_gain = cross_check.get("recall_gain", 0.0) * 100
                lines.append(
                    f"- External search recall gain: {recall_gain:.1f}% compared to cached sources."
                )
                if not cross_check.get("results"):
                    lines.append(
                        "- No external articles found, suggesting the topic may have low public visibility."
                    )
                lines.append("")  # Spacer

            lines.append("**Per-Cluster Bias Analysis:**")
            for item in scores:
                metrics = item.get("metrics", {})
                coverage = metrics.get("coverage_delta", 0)
                sentiment = metrics.get("sentiment_delta", 0)
                omission = metrics.get("omission_ratio", 0)
                entities = ", ".join(item.get("entities", [])) or "no named entities"

                lines.append(f"\n- **Cluster {item.get('cluster_id')} (Entities: {entities})**")
                lines.append(
                    f"  - **Coverage Delta:** {coverage:.2f}. "
                    f"{'State-aligned sources dominate coverage.' if coverage > 0.1 else 'Coverage is relatively balanced.'}"
                )
                lines.append(
                    f"  - **Sentiment Delta:** {sentiment:.2f}. "
                    f"{'State-aligned sources are markedly more positive.' if sentiment > 0.1 else 'Sentiment is similar across sources.'}"
                )
                lines.append(
                    f"  - **Omission Ratio:** {omission:.2f}. "
                    f"{'State-aligned sources omit key entities mentioned by others.' if omission > 0.1 else 'No significant omissions detected.'}"
                )
            return "\n".join(lines)

    # Public interface -----------------------------------------------------
    def explain(self, query: str) -> str:
        with otel_span("ExplainRequest"):
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=query),
            ]
            result = self.agent.invoke({"messages": messages})
            conversation = result.get("messages", [])
            return conversation[-1].content if conversation else ""

    # Helpers --------------------------------------------------------------
    def _fallback_entries(self, limit: int) -> List[CachedEntry]:
        """Produce stub entries when cache is empty."""
        fallback_payloads = [
            {
                "source_id": "liberty_watch",
                "language": "en",
                "text": (
                    "Liberty Watch reports grassroots protests in Aurora calling for "
                    "transparency over regional AI deployments."
                ),
                "metadata": {"state_aligned": False},
            },
            {
                "source_id": "aurora_daily",
                "language": "es",
                "text": (
                    "Aurora Daily destaca los avances del gobierno en estabilizar la economía "
                    "con nuevas inversiones tecnológicas."
                ),
                "metadata": {"state_aligned": True},
            },
        ]
        stubs = []
        for idx in range(min(limit, len(fallback_payloads))):
            payload = fallback_payloads[idx]
            stubs.append(
                CachedEntry(
                    source_id=payload["source_id"],
                    language=payload["language"],
                    clean_path=Path(""),
                    raw_path=Path(""),
                    fetched_at="stub",
                    text_preview=[payload["text"]],
                    metadata=payload["metadata"],
                    metadata_path=Path(""),
                )
            )
        return stubs

    def _cluster_to_dict(self, cluster: ClusterResult) -> Dict[str, Any]:
        return {
            "cluster_id": cluster.id,
            "entities": sorted(cluster.entities),
            "members": [
                {
                    "source_id": member.source_id,
                    "language": member.metadata.get("language"),
                    "state_aligned": bool(member.metadata.get("state_aligned")),
                    "text": member.text,
                }
                for member in cluster.members
            ],
        }


def demo():
    agent = BiasLangGraphAgent()
    question = "Provide a neutral summary of cached censorship signals."
    response = agent.explain(question)
    print("🤖 Bias Explainer Agent Response:\n")
    print(response)


if __name__ == "__main__":
    demo()
