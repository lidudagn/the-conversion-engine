"""
Demo script — Segment 3 of the video walkthrough.
Traces the headline 74% Delta A claim from raw traces → ablation file → evidence graph.
Run from repo root:  python3 scripts/demo_ablation_trace.py
"""

import json
from pathlib import Path

SEP  = "─" * 68
SEP2 = "═" * 68

def load(path):
    return json.loads(Path(path).read_text())

# ── 1. Rule evaluator — read directly from held-out traces ────────────────────
traces = [json.loads(l) for l in Path("eval/held_out_traces.jsonl").read_text().splitlines() if l.strip()]
rule_correct = sum(1 for t in traces if t.get("rule_correct"))

print()
print(SEP2)
print("  STEP 1 — Rule evaluator baseline  (from eval/held_out_traces.jsonl)")
print(SEP2)
print(f"  Tasks in held-out partition : {len(traces)}")
print(f"  rule_correct = True         : {rule_correct}")
print(f"  Rule evaluator accuracy     : {rule_correct}/{len(traces)} = {rule_correct/len(traces):.1%}  ← Delta B baseline")
print(SEP)

# ── 2. Trained judge — from ablation_results.json ─────────────────────────────
ablation = load("eval/ablation_results.json")
da = ablation["delta_a_trained_judge"]

print()
print(SEP2)
print("  STEP 2 — Trained DPO judge result  (from eval/ablation_results.json)")
print(SEP2)
print(f"  Method                      : {da['method']}  (β·(log π_DPO − log π_ref), sign→verdict)")
print(f"  Trained judge accuracy      : {da['n_correct']}/{da['n_total']} = {da['accuracy']:.1%}  ← Delta A")
print(f"  95% CI                      : {da['ci_95']}")
print(f"  p-value vs rule evaluator   : {da['p_value_vs_rule']}  (paired bootstrap n={ablation['_meta']['bootstrap_n']:,})")
print(f"  Significant at p < 0.05     : {da['significant_p05_vs_rule']}")
print(f"  Lift over rule evaluator    : +{da['lift_over_rule']:.0%}")
print(f"  Lift over prompt judge      : +{da['lift_over_prompt']:.0%}")
print(SEP)

# ── 3. Evidence graph — trace claim C25 back to its source ────────────────────
eg = load("eval/evidence_graph.json")
c25 = next(c for c in eg["claims"] if c["claim_id"] == "C25")

print()
print(SEP2)
print("  STEP 3 — Evidence graph trace  (eval/evidence_graph.json → C25)")
print(SEP2)
print(f"  Claim ID    : {c25['claim_id']}")
print(f"  Claim       : {c25['claim']}")
v = c25['value']
print(f"  Value       : {v['n_correct']}/{v['n_total']} = {v['accuracy']:.1%}  ← same number, traced to source")
print(f"  Source file : {c25['source_file']}")
print(f"  Source path : {c25['source_path']}")
print(f"  Provenance  : {c25['provenance'][:110]}...")
print(SEP)

print()
print("  TRACE CHAIN:")
print("  memo.pdf  →  evidence_graph.json[C25]")
print("            →  eval/ablation_results.json[delta_a_trained_judge.accuracy]")
print("            →  eval/held_out_traces.jsonl  (50 raw task verdicts)")
print()
