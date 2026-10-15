#!/usr/bin/env python3
"""
Offline demo: run ClearFrame's deterministic bias analysis on committed sample
articles. No API keys, no network.

  python demo/run_demo.py           # analyse, print a summary, compare with the recorded output
  python demo/run_demo.py --record  # overwrite demo/expected_output.json

This skips retrieval (Valyu) and the LLM-written parts of the full pipeline
(grandma brief, agent synthesis). It runs the same functions the CLI's default
unified-deterministic mode and the API use for per-article scoring, plus the
censorship-radar coverage comparison.
"""

import argparse
import json
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DEMO_DIR.parent))

import logging
logging.disable(logging.WARNING)

from src.analysis.bias_metrics import (  # noqa: E402
    TEXTBLOB_AVAILABLE,
    analyze_articles_bias,
    compute_censorship_radar,
)

SAMPLE = DEMO_DIR / "sample_articles.json"
EXPECTED = DEMO_DIR / "expected_output.json"


def run() -> dict:
    sample = json.loads(SAMPLE.read_text())
    articles = sample["articles"]
    return {
        "query": sample["query"],
        "bias_analysis": analyze_articles_bias(articles),
        "censorship_radar": compute_censorship_radar(articles),
    }


def print_summary(result: dict) -> None:
    analysis = result["bias_analysis"]
    print(f'Query: {result["query"]}  ({analysis["article_count"]} sample articles)\n')
    print(f'{"source":32} {"lean":>6} {"category":>12} {"emotion":>7} {"sensat.":>7} {"propag.":>7} {"overall":>7} {"topic":>9}')
    for a in analysis["articles"]:
        s = a["bias_scores"]
        print(f'{a["source"]:32} {s["political_lean"]:6.1f} {a["classification"]["bias_category"]:>12} '
              f'{s["emotional_manipulation"]:7.1f} {s["sensationalism"]:7.1f} {s["propaganda"]:7.1f} {s["overall_bias"]:7.1f} {a["enhanced_analysis"]["topic_category"]:>9}')
    cov = analysis["aggregate_stats"]["coverage_assessment"]
    print(f'\nLean counts: {cov["left_leaning_articles"]} left, {cov["neutral_articles"]} neutral, '
          f'{cov["right_leaning_articles"]} right')
    radar = result["censorship_radar"]
    print(f'Coverage radar: omission score {radar["scale_of_censorship"]} ({radar["severity"]}), '
          f'topics seen: {", ".join(radar["union_topics"])}')
    for cls, vec in radar["bias_vectors"].items():
        print(f'  {cls:14} {vec["article_count"]} article(s), misses: {", ".join(vec["omissions"]) or "none"}')
    gated = [a for a in analysis["articles"] if a["enhanced_analysis"]["topic_category"] in ("entertainment", "sports", "tech", "science")]
    if gated:
        print(f"\nNote: {len(gated)} article(s) were tagged as a non-political topic, so their lean was set to 0 without scoring.")
    print("\nScores are keyword/lexicon heuristics, not validated measurements: see the Evaluation section of the README.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true", help="overwrite the recorded output")
    args = ap.parse_args()

    if not TEXTBLOB_AVAILABLE:
        print("textblob is not installed: pip install -r requirements-demo.txt", file=sys.stderr)
        return 1

    result = run()
    print_summary(result)

    if args.record:
        EXPECTED.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(f"\nRecorded output to {EXPECTED.relative_to(DEMO_DIR.parent)}")
        return 0

    expected = json.loads(EXPECTED.read_text())
    if json.loads(json.dumps(result)) == expected:
        print(f"\nOK: full output matches {EXPECTED.relative_to(DEMO_DIR.parent)}")
        return 0
    print(f"\nMISMATCH: output differs from {EXPECTED.relative_to(DEMO_DIR.parent)}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
