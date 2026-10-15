#!/usr/bin/env python3
"""
Evaluate ClearFrame's deterministic political-lean score against human labels.

Labels: the media-split test set of the Article-Bias-Prediction dataset
(Baly et al., EMNLP 2020, https://github.com/ramybaly/Article-Bias-Prediction).
Each article carries an AllSides left / center / right label. The test split
uses news outlets that do not appear in the dataset's training split.

Article text is not committed to this repo. The script downloads the test-split
IDs and the per-article JSON files into evaluation/.cache/ on first run.

Usage:
  python evaluation/evaluate_bias.py            # writes evaluation/results.json
  python evaluation/evaluate_bias.py --limit 50 # quick smoke run
"""

import argparse
import json
import sys
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import logging
logging.disable(logging.WARNING)

from src.analysis.bias_metrics import TEXTBLOB_AVAILABLE, detect_political_lean_enhanced  # noqa: E402

DATASET = "https://raw.githubusercontent.com/ramybaly/Article-Bias-Prediction/main/data"
CACHE = Path(__file__).resolve().parent / ".cache"
LABELS = ["left", "center", "right"]
SNIPPET_CHARS = 500


def fetch(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=30) as r:
            dest.write_bytes(r.read())
    return dest


def load_test_split(limit=None):
    tsv = fetch(f"{DATASET}/splits/media/test.tsv", CACHE / "test.tsv")
    ids = [line.split("\t")[0] for line in tsv.read_text().splitlines()[1:] if line.strip()]
    if limit:
        ids = ids[:limit]
    with ThreadPoolExecutor(max_workers=16) as pool:
        paths = list(pool.map(lambda i: fetch(f"{DATASET}/jsons/{i}.json", CACHE / "jsons" / f"{i}.json"), ids))
    return [json.loads(p.read_text()) for p in paths]


def to_label(score: float) -> str:
    # Same thresholds ClearFrame uses for its left/neutral/right article counts
    # (coverage_assessment in src/analysis/bias_metrics.py).
    if score < -5:
        return "left"
    if score > 5:
        return "right"
    return "center"


def keyword_baseline(text: str) -> float:
    # Copied from the fallback branch of calculate_bias_score in backend/basic_cli.py.
    left_keywords = ['progressive', 'liberal', 'reform', 'diversity', 'climate action']
    right_keywords = ['conservative', 'traditional', 'free market', 'deregulation']
    text_lower = text.lower()
    left_count = sum(1 for kw in left_keywords if kw in text_lower)
    right_count = sum(1 for kw in right_keywords if kw in text_lower)
    total = left_count + right_count
    if total == 0:
        return 0.0
    return ((right_count - left_count) / total) * 50


def metrics(gold, pred):
    n = len(gold)
    acc = sum(g == p for g, p in zip(gold, pred)) / n
    per_class, f1s = {}, []
    for c in LABELS:
        tp = sum(g == c and p == c for g, p in zip(gold, pred))
        fp = sum(g != c and p == c for g, p in zip(gold, pred))
        fn = sum(g == c and p != c for g, p in zip(gold, pred))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[c] = {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3)}
        f1s.append(f1)
    confusion = {g: {p: sum(1 for x, y in zip(gold, pred) if x == g and y == p) for p in LABELS} for g in LABELS}
    return {
        "accuracy": round(acc, 3),
        "macro_f1": round(sum(f1s) / len(f1s), 3),
        "per_class": per_class,
        "predicted_counts": dict(Counter(pred)),
        "confusion_gold_rows_pred_cols": confusion,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--output", default=str(Path(__file__).resolve().parent / "results.json"))
    args = ap.parse_args()

    if not TEXTBLOB_AVAILABLE:
        sys.exit("textblob is required (pip install -r requirements-demo.txt): the scorer's sentiment term depends on it")

    articles = load_test_split(args.limit)
    gold = [a["bias_text"] for a in articles]

    systems = {}
    rows = []
    for setting, make_text in {
        "snippet": lambda a: (a["title"], a["content_original"][:SNIPPET_CHARS]),
        "full_text": lambda a: (a["title"], a["content_original"]),
    }.items():
        preds, kw_preds = [], []
        for a in articles:
            title, body = make_text(a)
            text = f"{title} {body}"  # what ArticleBiasProfile scores: title + description
            r = detect_political_lean_enhanced(text, a.get("source_url", ""), title, a.get("url", ""))
            preds.append(to_label(r["lean_score"]))
            kw_preds.append(to_label(keyword_baseline(text)))
            if setting == "snippet":
                rows.append({
                    "id": a["ID"], "source": a["source"], "gold": a["bias_text"],
                    "lean_score": r["lean_score"], "pred": preds[-1],
                    "topic_category": r["topic_category"], "gated_neutral": "reason" in r,
                })
        systems[f"clearframe_{setting}"] = metrics(gold, preds)
        systems[f"keyword_baseline_{setting}"] = metrics(gold, kw_preds)

    majority = Counter(gold).most_common(1)[0][0]
    systems["majority_class"] = metrics(gold, [majority] * len(gold))
    systems["always_center"] = metrics(gold, ["center"] * len(gold))

    out = {
        "dataset": "Article-Bias-Prediction, media split, test set (Baly et al. 2020)",
        "n_articles": len(articles),
        "gold_counts": dict(Counter(gold)),
        "snippet_chars": SNIPPET_CHARS,
        "label_thresholds": "lean_score < -5 -> left, > 5 -> right, else center",
        "gated_neutral_snippet": sum(r["gated_neutral"] for r in rows),
        "systems": systems,
        "per_article_snippet": rows,
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + "\n")

    print(f"{len(articles)} articles, gold counts {dict(Counter(gold))}")
    print(f"{'system':32} {'accuracy':>8} {'macro-F1':>8}")
    for name, m in systems.items():
        print(f"{name:32} {m['accuracy']:8.3f} {m['macro_f1']:8.3f}")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
