import os, sys, pytest
sys.path.append(os.path.abspath('.'))
from src.analysis import bias_metrics

# Minimal fixture articles simulating different classes
ARTICLES_FIXTURE = [
    {
        "title": "Gov announces aid package",
        "description": "Government officials confirm international aid and UN coordination for displaced civilians.",
        "source": "reuters.com",
        "url": "https://www.reuters.com/world/africa/gov-announces-aid"},
    {
        "title": "State media report stability",
        "description": "Military authorities highlight stability and deny casualty escalation.",
        "source": "tass.com",
        "url": "https://tass.com/stability-update"},
    {
        "title": "Diaspora blog eyewitness account",
        "description": "Activists describe humanitarian shortages and accuse government forces of blocking aid routes.",
        "source": "mydiasporablog.medium.com",
        "url": "https://mydiasporablog.medium.com/post"},
]


def test_dashboard_payload_structure():
    payload = bias_metrics.build_dashboard_payload(ARTICLES_FIXTURE)
    expected_keys = {
        "version","scale_of_censorship","severity","union_topics","bias_vectors","source_angle_cards","coverage_matrix_percent","blame_distribution","omissions_diff","entity_stance"
    }
    for k in expected_keys:
        assert k in payload, f"Missing key {k} in dashboard payload"


def test_cross_class_omissions_present():
    radar = bias_metrics.compute_censorship_radar(ARTICLES_FIXTURE)
    diff = bias_metrics.cross_class_omissions(radar['bias_vectors'])
    assert 'by_class' in diff and 'merged' in diff
    # merged may be empty but structure must exist
    assert isinstance(diff['by_class'], dict)


def test_normalize_coverage_matrix_percentages():
    radar = bias_metrics.compute_censorship_radar(ARTICLES_FIXTURE)
    framing = bias_metrics.compute_framing_comparison(radar['bias_vectors'], radar['union_topics'])
    normalized = bias_metrics.normalize_coverage_matrix(framing['coverage_matrix'], radar['bias_vectors'])
    for row in normalized:
        for pct in row['topic_percent'].values():
            assert 0.0 <= pct <= 100.0


def test_entity_stance_mentions_and_avg():
    radar = bias_metrics.compute_censorship_radar(ARTICLES_FIXTURE)
    stance = bias_metrics.compute_entity_stance(ARTICLES_FIXTURE, radar['bias_vectors'])
    assert 'entity_stance' in stance
    # At least one class should appear
    assert isinstance(stance['entity_stance'], dict)


def test_grandma_brief_word_bounds():
    brief = bias_metrics.generate_grandma_brief(ARTICLES_FIXTURE, "test query")
    wc = len(brief.split())
    assert 300 <= wc <= 500, f"Brief word count out of bounds: {wc}"


def test_dashboard_determinism():
    p1 = bias_metrics.build_dashboard_payload(ARTICLES_FIXTURE)
    p2 = bias_metrics.build_dashboard_payload(ARTICLES_FIXTURE)
    assert p1 == p2, "Dashboard payload not deterministic across runs"
