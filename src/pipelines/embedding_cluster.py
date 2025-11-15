import math
import re
from typing import Iterable, List, Sequence, Tuple

from src.utils.data_models import ArticleRecord, ClusterResult

try:
    import spacy

    _NLP = spacy.load("en_core_web_sm")
except Exception:  # pragma: no cover - fallback path used in tests
    _NLP = None


class HashEmbeddingProvider:
    """
    Lightweight embedding provider that hashes tokens into a fixed-size vector.
    Deterministic so tests can rely on stable clustering behaviour.
    """

    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions

    def embed_text(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        for token in self._tokenize(text):
            index = hash(token) % self.dimensions
            vector[index] += 1.0
        return self._normalize(vector)

    def embed_articles(self, articles: Sequence[ArticleRecord]) -> List[List[float]]:
        return [self.embed_text(article.text) for article in articles]

    def _tokenize(self, text: str) -> Iterable[str]:
        return re.findall(r"\w+", text.lower())

    def _normalize(self, vector: List[float]) -> List[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def extract_entities(text: str) -> List[str]:
    """
    Extract named entities using spaCy when available, otherwise fall back to a
    simple capitalized-word heuristic so tests do not require external models.
    """
    if _NLP:
        doc = _NLP(text)
        return [ent.text for ent in doc.ents]
    return re.findall(r"\b[A-Z][a-zA-Z]+\b", text)


def cluster_articles(
    articles: Sequence[ArticleRecord],
    similarity_threshold: float = 0.45,
) -> List[ClusterResult]:
    """
    Group articles with similar vocabulary/embeddings/entities into clusters.
    A greedy single-pass approach keeps the implementation lightweight.
    """
    if not articles:
        return []

    provider = HashEmbeddingProvider()
    embeddings = provider.embed_articles(articles)
    token_sets = [_token_set(article.text) for article in articles]
    entity_sets = [set(extract_entities(article.text)) for article in articles]

    cluster_store: List[Tuple[List[int], List[ArticleRecord]]] = []

    for idx, article in enumerate(articles):
        assigned = False
        for cluster_indices, cluster_articles in cluster_store:
            similarity = max(
                _article_similarity(
                    idx,
                    other_idx,
                    embeddings,
                    token_sets,
                    entity_sets,
                )
                for other_idx in cluster_indices
            )
            if similarity >= similarity_threshold:
                cluster_indices.append(idx)
                cluster_articles.append(article)
                assigned = True
                break
        if not assigned:
            cluster_store.append(([idx], [article]))

    results = [
        ClusterResult(cluster_id=f"cluster_{i}", articles=cluster_articles)
        for i, (_, cluster_articles) in enumerate(cluster_store)
    ]
    return results


def _token_set(text: str) -> set:
    return set(re.findall(r"\w+", text.lower()))


def _article_similarity(
    idx_a: int,
    idx_b: int,
    embeddings: Sequence[Sequence[float]],
    token_sets: Sequence[set],
    entity_sets: Sequence[set],
) -> float:
    embedding_sim = _cosine_similarity(embeddings[idx_a], embeddings[idx_b])
    token_overlap = _jaccard(token_sets[idx_a], token_sets[idx_b])
    entity_overlap = _jaccard(entity_sets[idx_a], entity_sets[idx_b])
    # Weighted blend keeps similarity within [0, 1]
    return 0.5 * embedding_sim + 0.3 * token_overlap + 0.2 * entity_overlap


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)
