"""
AI Maturity Scorer Validation
Compares scorer output against hand-labeled ground truth.
Outputs: confusion matrix, precision/recall per score level, overall accuracy.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.enrichment.pipeline import EnrichmentPipeline


def validate():
    labels_file = Path(__file__).parent / "ai_maturity_labels.json"
    labels_data = json.loads(labels_file.read_text())
    labels = labels_data["labels"]

    pipeline = EnrichmentPipeline()
    pipeline.load_data()

    results = []
    confusion = defaultdict(lambda: defaultdict(int))

    print(f"\n{'='*60}")
    print(f"AI Maturity Scorer Validation — {len(labels)} companies")
    print(f"{'='*60}\n")

    for entry in labels:
        company = entry["company"]
        expected = entry["label"]

        try:
            brief, gap_brief, contradictions = pipeline.enrich_prospect(company)
            predicted = brief.ai_maturity.get("score", 0) if isinstance(brief.ai_maturity, dict) else 0
        except Exception as e:
            predicted = 0
            print(f"  Warning: {company} enrichment error: {e}")

        match = predicted == expected
        results.append({
            "company": company,
            "expected": expected,
            "predicted": predicted,
            "match": match,
        })
        confusion[expected][predicted] += 1
        marker = "✓" if match else "✗"
        print(f"  {marker} {company:35s} expected={expected} predicted={predicted}")

    # Metrics
    correct = sum(1 for r in results if r["match"])
    total = len(results)
    accuracy = correct / total if total > 0 else 0

    # Within-1 accuracy (predicted is within ±1 of expected)
    within_1 = sum(1 for r in results if abs(r["expected"] - r["predicted"]) <= 1)
    within_1_rate = within_1 / total if total > 0 else 0

    # Per-score precision/recall
    per_score = {}
    for score in range(4):
        tp = confusion[score][score]
        fp = sum(confusion[other][score] for other in range(4) if other != score)
        fn = sum(confusion[score][other] for other in range(4) if other != score)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        per_score[str(score)] = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(prec, 3),
            "recall": round(rec, 3),
            "support": sum(confusion[score].values()),
        }

    summary = {
        "total_companies": total,
        "exact_match": correct,
        "exact_accuracy": round(accuracy, 4),
        "within_1_match": within_1,
        "within_1_accuracy": round(within_1_rate, 4),
        "confusion_matrix": {str(k): dict(v) for k, v in confusion.items()},
        "per_score_metrics": per_score,
        "per_company": results,
    }

    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"  Exact accuracy: {correct}/{total} ({accuracy:.1%})")
    print(f"  Within-1 accuracy: {within_1}/{total} ({within_1_rate:.1%})")
    print(f"\nConfusion matrix (rows=expected, cols=predicted):")
    print(f"  {'':>8s}  pred=0  pred=1  pred=2  pred=3")
    for exp in range(4):
        row = [confusion[exp].get(p, 0) for p in range(4)]
        print(f"  exp={exp}:  {'  '.join(f'{v:>6d}' for v in row)}")
    print(f"\nPer-score metrics:")
    for score, m in per_score.items():
        print(f"  Score {score}: P={m['precision']:.2f} R={m['recall']:.2f} support={m['support']}")
    print(f"{'='*60}")

    output_file = Path(__file__).parent / "ai_maturity_validation_results.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved to {output_file}")

    return summary


if __name__ == "__main__":
    validate()
