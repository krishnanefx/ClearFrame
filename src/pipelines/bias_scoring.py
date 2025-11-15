from typing import List
from textblob import TextBlob
from src.utils.data_models import ArticleRecord, BiasScore
from src.pipelines.embedding_cluster import extract_entities

def score_bias(articles: List[ArticleRecord]) -> BiasScore:
    """
    Calculates quantitative bias metrics for a given list of articles.
    """
    state_aligned_articles = [a for a in articles if a.metadata.get('state_aligned')]
    independent_articles = [a for a in articles if not a.metadata.get('state_aligned')]

    # 1. Coverage Delta (difference in share of coverage across article counts)
    total_articles = len(articles)
    if total_articles == 0:
        coverage_delta = 0.0
    else:
        coverage_delta = (len(state_aligned_articles) - len(independent_articles)) / total_articles

    # 2. Sentiment Delta
    state_sentiments = [TextBlob(a.text).sentiment.polarity for a in state_aligned_articles]
    independent_sentiments = [TextBlob(a.text).sentiment.polarity for a in independent_articles]

    if not state_sentiments or not independent_sentiments:
        sentiment_delta = 0.0
    else:
        avg_state_sentiment = sum(state_sentiments) / len(state_sentiments)
        avg_independent_sentiment = sum(independent_sentiments) / len(independent_sentiments)
        sentiment_delta = avg_state_sentiment - avg_independent_sentiment

    # 3. Omission Ratio
    state_entities = set()
    for article in state_aligned_articles:
        state_entities.update(extract_entities(article.text))
        
    independent_entities = set()
    for article in independent_articles:
        independent_entities.update(extract_entities(article.text))
        
    if not independent_entities:
        omission_ratio = 1.0 if state_entities else 0.0
    else:
        entities_only_in_independent = independent_entities - state_entities
        omission_ratio = len(entities_only_in_independent) / len(independent_entities)

    return BiasScore(
        coverage_delta=coverage_delta,
        sentiment_delta=sentiment_delta,
        omission_ratio=omission_ratio
    )
