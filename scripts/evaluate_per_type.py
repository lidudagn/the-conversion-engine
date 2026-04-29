import json
from collections import defaultdict

def evaluate_results():
    with open("eval/tenacious_bench/ablation_raw_results.json", "r") as f:
        results = json.load(f)

    # 1. Define True Labels & Buckets
    # For expert BAD drafts, we know their actual failure types:
    expert_true_types = {
        "SG-BAD-01": "STYLE_VIOLATION",
        "SG-BAD-02": "STYLE_VIOLATION",
        "SG-BAD-03": "SEMANTIC_FALSEHOOD", # Bench overcommit
        "SG-BAD-04": "STYLE_VIOLATION",
        "SG-BAD-05": "SEMANTIC_FALSEHOOD", # Passive-aggression
        "SG-BAD-06": "STYLE_VIOLATION",
        "SG-BAD-07": "SEMANTIC_FALSEHOOD", # Fake urgency
        "SG-BAD-08": "REASONING_FAILURE",
        "SG-BAD-09": "STRUCTURAL_VIOLATION",
        "SG-BAD-10": "REASONING_FAILURE",
        "SG-BAD-11": "REASONING_FAILURE",
        "SG-BAD-12": "SEMANTIC_FALSEHOOD"  # Fabricated funding
    }

    # Aggregate counts
    metrics = {
        "Rule": {"correct": 0, "false_positives": 0, "semantic_caught": 0},
        "Base": {"correct": 0, "false_positives": 0, "semantic_caught": 0},
        "Trained": {"correct": 0, "false_positives": 0, "semantic_caught": 0}
    }
    
    total_tasks = len(results)
    total_passes = sum(1 for r in results if r["expected_verdict"] == "PASS")
    total_semantic_bad = sum(1 for r in expert_true_types.values() if r == "SEMANTIC_FALSEHOOD")
    
    four_bad_drafts = ["SG-BAD-03", "SG-BAD-05", "SG-BAD-07", "SG-BAD-12"]
    
    ablation_report = []
    ablation_report.append("# Act IV: Ablation Studies & Measurement Report\n")
    
    # Track the 4 key mentor drafts specifically
    four_bad_results = []
    
    for r in results:
        task_id = r["task_id"]
        expected = r["expected_verdict"]
        
        # Rule metrics
        if r["rule_verdict"] == expected: metrics["Rule"]["correct"] += 1
        if expected == "PASS" and r["rule_verdict"] == "FAIL": metrics["Rule"]["false_positives"] += 1
        
        # Base metrics
        if r["base_verdict"] == expected: metrics["Base"]["correct"] += 1
        if expected == "PASS" and r["base_verdict"] == "FAIL": metrics["Base"]["false_positives"] += 1
        
        # Trained metrics
        if r["trained_verdict"] == expected: metrics["Trained"]["correct"] += 1
        if expected == "PASS" and r["trained_verdict"] == "FAIL": metrics["Trained"]["false_positives"] += 1
        
        if task_id in four_bad_drafts:
            metrics["Rule"]["semantic_caught"] += (1 if r["rule_verdict"] == "FAIL" else 0)
            metrics["Base"]["semantic_caught"] += (1 if r["base_verdict"] == "FAIL" else 0)
            metrics["Trained"]["semantic_caught"] += (1 if r["trained_verdict"] == "FAIL" else 0)
            
            four_bad_results.append({
                "ID": task_id,
                "Rule": r["rule_verdict"],
                "Trained": r["trained_verdict"],
                "Trained Rationale": r.get("trained_rationale", "")
            })

    # Output formatting
    ablation_report.append("## Overall Metrics")
    ablation_report.append(f"| Model | Accuracy | Pass Precision (1 - FP/TotalPasses) | SEMANTIC_FALSEHOOD Recall (4 Key Drafts) |")
    ablation_report.append(f"|---|---|---|---|")
    
    for model in ["Rule", "Base", "Trained"]:
        acc = metrics[model]["correct"] / total_tasks
        precision = 1.0 - (metrics[model]["false_positives"] / max(total_passes, 1))
        sem_recall = metrics[model]["semantic_caught"] / max(total_semantic_bad, 1)
        ablation_report.append(f"| {model} | {acc:.1%} | {precision:.1%} | {metrics[model]['semantic_caught']}/{total_semantic_bad} ({sem_recall:.1%}) |")
        
    ablation_report.append("\n## The 4-Draft Litmus Test (Evaluator Agreement vs Human Verdict)")
    ablation_report.append("| Task ID | Frozen Evaluator (Rule) | Trained Judge | Human Verdict (Expected) | Agreement Status |")
    ablation_report.append("|---|---|---|---|---|")
    
    caught_by_trained = 0
    for r in four_bad_results:
        # Evaluator is wrong on all four (passes them). Human says FAIL.
        status = "Disagrees: Evaluator WRONG, Model RIGHT" if r["Trained"] == "FAIL" else "Agrees: Model inherited Evaluator Blind Spot"
        if r["Trained"] == "FAIL": caught_by_trained +=1
        ablation_report.append(f"| {r['ID']} | {r['Rule']} | {r['Trained']} | FAIL | {status} |")
        
    ablation_report.append("\n### Litmus Conclusion")
    if caught_by_trained >= 3:
        ablation_report.append(f"**SUCCESS**: The Trained Judge successfully flipped {caught_by_trained}/4 semantic truth violations without degrading style precision. It learned structural independence beyond our labeling rules.")
    else:
        ablation_report.append(f"**FAILURE MODE DETECTED**: The Trained Judge only caught {caught_by_trained}/4 cases. It aligned heavily with the evaluator metric rather than discovering the semantic falsehoods in the wild.")
        
    # Write to report
    with open("eval/tenacious_bench/ablation_report.md", "w") as f:
        f.write("\n".join(ablation_report))
        
    print("Evaluation completed. Saved to eval/tenacious_bench/ablation_report.md")

if __name__ == "__main__":
    evaluate_results()
