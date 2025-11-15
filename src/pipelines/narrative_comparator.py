from typing import Iterable, Sequence, Union

from src.utils.data_models import ClusterResult, NarrativeComparison
from src.pipelines.bias_scoring import score_bias


def compare_cluster(
    cluster_or_id: Union[ClusterResult, object],
    entities: Sequence[str] = (),
    articles: Sequence = (),
) -> NarrativeComparison:
    """
    Compare narratives between state aligned and independent sources in a cluster.
    Accepts either a ClusterResult instance or explicit identifiers plus articles.
    """
    if isinstance(cluster_or_id, ClusterResult):
        cluster_id = cluster_or_id.cluster_id
        entities = getattr(cluster_or_id, "entities", entities)
        articles = cluster_or_id.articles
    else:
        cluster_id = cluster_or_id

    articles = list(articles)
    state_aligned_articles = [
        article for article in articles if article.metadata.get("state_aligned")
    ]
    independent_articles = [
        article for article in articles if not article.metadata.get("state_aligned")
    ]

    state_aligned_summary = _generate_summary(state_aligned_articles)
    independent_summary = _generate_summary(independent_articles)

    bias_score = score_bias(articles)
    metrics = {
        "entities": list(entities),
        "article_count": len(articles),
        "state_aligned_count": len(state_aligned_articles),
        "independent_count": len(independent_articles),
        "bias_score": {
            "coverage_delta": bias_score.coverage_delta,
            "sentiment_delta": bias_score.sentiment_delta,
            "omission_ratio": bias_score.omission_ratio,
        },
    }

    return NarrativeComparison(
        cluster_id=cluster_id,
        state_aligned_summary=state_aligned_summary,
        independent_summary=independent_summary,
        bias_score=bias_score,
        metrics=metrics,
    )


def _generate_summary(articles: Iterable) -> str:
    """
    Generates a simple deterministic summary string for the provided articles.
    """
    articles = list(articles)
    if not articles:
        return "No articles from this group."

    sources = ", ".join(sorted({article.source_id for article in articles}))
    snippet = " ".join(article.text for article in articles)
    preview = snippet[:200] + ("..." if len(snippet) > 200 else "")
    return f"Sources: {sources}. Highlights: {preview}"
