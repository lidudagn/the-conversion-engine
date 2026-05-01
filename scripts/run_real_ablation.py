#!/usr/bin/env python3
"""
Real ablation evaluation for Tenacious-Bench v0.1.

This script runs two judges against the held-out partition and style guide examples:
  1. Rule-based deterministic evaluator (our built judge, no GPU needed)
  2. Prompt-only LLM judge via OpenRouter (Delta B baseline)

Both judges are compared against ground truth labels in the dataset.
Statistical tests (paired bootstrap, p-value) are computed on real predictions.

Delta A (LoRA-trained model vs baseline) requires GPU training in Google Colab.
See: scripts/train_judge_lora.py  and  scripts/run_ablation.py
"""

import json
import os
import sys
import time
import random
import statistics
import re
from pathlib import Path
from datetime import datetime, timezone

import urllib.request
import urllib.error

sys.path.insert(0, str(Path(__file__).parent.parent))
from eval.tenacious_bench.scoring_evaluator_v2_frozen import ScoringEvaluator

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
JUDGE_MODEL = "qwen/qwen3-8b"   # dev-tier, cheap, not same family as gpt-4o-mini generator
SEED = 3407
BOOTSTRAP_N = 10_000
HELD_OUT_PATH = "eval/tenacious_bench/pilot_50/splits/held_out.jsonl"
STYLE_GUIDE_PATH = "eval/tenacious_bench/style_guide_examples.jsonl"
JUDGE_PROMPT_PATH = "eval/tenacious_bench/baseline_prompt_judge_v1.txt"
OUTPUT_RAW = "eval/tenacious_bench/ablation_raw_results.json"
OUTPUT_TRACES = "eval/held_out_traces.jsonl"
OUTPUT_RESULTS = "eval/ablation_results.json"
COST_LOG_PATH = "cost_log.json"

random.seed(SEED)


def load_jsonl(path: str) -> list:
    items = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def normalize_verdict(v: str) -> str:
    """Normalize any verdict string to 'PASS' or 'FAIL'."""
    v = str(v).strip().upper()
    if any(k in v for k in ["PASS", "POSITIVE", "APPROVE", "ALIGNED", "GOOD", "SUCCESS"]):
        return "PASS"
    return "FAIL"


def extract_ground_truth(task: dict, source: str) -> str:
    if source == "style_guide":
        return normalize_verdict(task.get("verdict", "FAIL"))
    gt = task.get("ground_truth", {})
    return normalize_verdict(gt.get("verdict", "FAIL"))


def build_rule_evaluator_payload(task: dict, source: str) -> dict:
    """Build the dict the scoring evaluator expects."""
    if source == "style_guide":
        # Style guide tasks have 'body' and 'segment' at top level
        return {
            "candidate_output": task.get("body", ""),
            "ground_truth": {
                "inferred_segment": int(task.get("segment", 1)),
                "required_signals": [],
                "forbidden_signals": [],
            },
            "email_type": "cold",
        }
    # Held-out tasks
    gt = task.get("ground_truth", {})
    inp = task.get("input", {})
    bri = inp.get("hiring_signal_brief", {})
    return {
        "candidate_output": task.get("candidate_output", ""),
        "ground_truth": {
            "inferred_segment": gt.get("inferred_segment"),
            "required_signals": gt.get("required_signals", []),
            "forbidden_signals": gt.get("forbidden_signals", []),
        },
        "email_type": "cold",
    }


def call_openrouter_judge(prompt_template: str, task: dict, source: str) -> dict:
    """Call OpenRouter with the prompt judge and return parsed result."""
    if source == "style_guide":
        signal = json.dumps({
            "segment": task.get("segment"),
            "signal_type": task.get("signal_type", ""),
        })
        policy = json.dumps({"pitch_segment": task.get("segment")})
        email = task.get("body", "")
    else:
        inp = task.get("input", {})
        signal = json.dumps(inp.get("hiring_signal_brief", {}))
        policy = json.dumps(inp.get("policy_decision", {}))
        email = task.get("candidate_output", "")

    prompt = (
        prompt_template
        .replace("{signal}", signal)
        .replace("{policy}", policy)
        .replace("{email}", email)
    )

    payload = json.dumps({
        "model": JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 120,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/lidudagn/the-conversion-engine",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"].strip()
        usage = body.get("usage", {})
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        return {"verdict": "ERROR", "rationale": f"HTTP {e.code}: {error_body[:200]}", "usage": {}}
    except Exception as ex:
        return {"verdict": "ERROR", "rationale": str(ex), "usage": {}}

    # Try JSON parse first (the template asks for strict JSON output)
    verdict = "ERROR"
    rationale = content
    try:
        parsed = json.loads(content)
        verdict = normalize_verdict(parsed.get("verdict", "FAIL"))
        rationale = parsed.get("rationale", "")
    except json.JSONDecodeError:
        # Fallback: search for "Aligned" or "Misaligned" in raw text
        if re.search(r'\bAligned\b', content, re.IGNORECASE):
            verdict = "PASS"
        elif re.search(r'\bMisaligned\b', content, re.IGNORECASE):
            verdict = "FAIL"
        else:
            verdict = "FAIL"

    return {"verdict": verdict, "rationale": rationale, "raw": content, "usage": usage}


def bootstrap_ci(labels: list, preds: list, n: int = BOOTSTRAP_N, alpha: float = 0.05):
    """Paired bootstrap for accuracy. Returns (accuracy, ci_low, ci_high)."""
    n_samples = len(labels)
    base_acc = sum(l == p for l, p in zip(labels, preds)) / n_samples
    boot_accs = []
    for _ in range(n):
        indices = [random.randint(0, n_samples - 1) for _ in range(n_samples)]
        acc = sum(labels[i] == preds[i] for i in indices) / n_samples
        boot_accs.append(acc)
    boot_accs.sort()
    lo = boot_accs[int(alpha / 2 * n)]
    hi = boot_accs[int((1 - alpha / 2) * n)]
    return round(base_acc, 4), round(lo, 4), round(hi, 4)


def paired_bootstrap_p(labels: list, preds_a: list, preds_b: list, n: int = BOOTSTRAP_N) -> float:
    """
    Two-tailed paired bootstrap p-value: is accuracy(A) != accuracy(B)?
    Returns p-value. Reject H0 (equal accuracy) at p < 0.05.
    """
    n_samples = len(labels)
    obs_delta = (
        sum(l == a for l, a in zip(labels, preds_a)) -
        sum(l == b for l, b in zip(labels, preds_b))
    ) / n_samples

    count_extreme = 0
    for _ in range(n):
        indices = [random.randint(0, n_samples - 1) for _ in range(n_samples)]
        delta = (
            sum(labels[i] == preds_a[i] for i in indices) -
            sum(labels[i] == preds_b[i] for i in indices)
        ) / n_samples
        if abs(delta) >= abs(obs_delta):
            count_extreme += 1
    return round(count_extreme / n, 4)


def main():
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set in environment.")
        sys.exit(1)

    with open(JUDGE_PROMPT_PATH) as f:
        prompt_template = f.read()

    evaluator = ScoringEvaluator()

    # Load evaluation data
    held_out_tasks = [("held_out", t) for t in load_jsonl(HELD_OUT_PATH)]
    sg_tasks = [("style_guide", t) for t in load_jsonl(STYLE_GUIDE_PATH)]
    all_tasks = held_out_tasks + sg_tasks

    print(f"Loaded {len(held_out_tasks)} held-out tasks + {len(sg_tasks)} style-guide examples = {len(all_tasks)} total")
    print(f"Rule evaluator: ScoringEvaluator (deterministic, no API)")
    print(f"Prompt judge: {JUDGE_MODEL} via OpenRouter")
    print()

    results = []
    total_tokens = 0
    errors = 0

    for idx, (source, task) in enumerate(all_tasks):
        tid = task.get("task_id", f"TASK_{idx}")
        gt = extract_ground_truth(task, source)

        # --- Rule evaluator ---
        rule_payload = build_rule_evaluator_payload(task, source)
        rule_result = evaluator.evaluate_task(rule_payload)
        rule_verdict = "PASS" if rule_result.verdict == "PASS" else "FAIL"

        # --- Prompt judge ---
        prompt_result = call_openrouter_judge(prompt_template, task, source)
        prompt_verdict = prompt_result["verdict"]
        usage = prompt_result.get("usage", {})
        total_tokens += usage.get("total_tokens", 0)

        if prompt_verdict == "ERROR":
            errors += 1
            prompt_verdict = "FAIL"  # conservative fallback

        rule_correct = (rule_verdict == gt)
        prompt_correct = (prompt_verdict == gt)

        results.append({
            "task_id": tid,
            "source": source,
            "ground_truth": gt,
            "rule_verdict": rule_verdict,
            "rule_score": rule_result.composite,
            "rule_failure_type": rule_result.failure_type,
            "rule_fatal_flags": rule_result.fatal_reasons,
            "rule_correct": rule_correct,
            "prompt_verdict": prompt_verdict,
            "prompt_rationale": prompt_result.get("rationale", ""),
            "prompt_correct": prompt_correct,
        })

        print(f"[{idx+1:03d}/{len(all_tasks)}] {tid:<20} GT={gt}  Rule={rule_verdict}({'✓' if rule_correct else '✗'})  Prompt={prompt_verdict}({'✓' if prompt_correct else '✗'})")

        time.sleep(0.3)  # polite rate limiting

    # --- Compute statistics ---
    gt_labels = [r["ground_truth"] for r in results]
    rule_preds = [r["rule_verdict"] for r in results]
    prompt_preds = [r["prompt_verdict"] for r in results]

    rule_acc, rule_ci_lo, rule_ci_hi = bootstrap_ci(gt_labels, rule_preds)
    prompt_acc, prompt_ci_lo, prompt_ci_hi = bootstrap_ci(gt_labels, prompt_preds)
    delta_b_pvalue = paired_bootstrap_p(gt_labels, rule_preds, prompt_preds)
    delta_b_lift = round(rule_acc - prompt_acc, 4)

    # Subset: only held-out (excludes style guide)
    ho_results = [r for r in results if r["source"] == "held_out"]
    ho_gt = [r["ground_truth"] for r in ho_results]
    ho_rule = [r["rule_verdict"] for r in ho_results]
    ho_prompt = [r["prompt_verdict"] for r in ho_results]
    ho_rule_acc, ho_rule_ci_lo, ho_rule_ci_hi = bootstrap_ci(ho_gt, ho_rule)
    ho_prompt_acc, ho_prompt_ci_lo, ho_prompt_ci_hi = bootstrap_ci(ho_gt, ho_prompt)

    # Cost estimate: ~$0.0001 per 1k tokens for qwen3-8b on OpenRouter
    estimated_cost_usd = round(total_tokens / 1_000_000 * 0.1, 4)  # $0.10/M tokens

    print(f"\n{'='*70}")
    print(f"RESULTS (all {len(results)} tasks)")
    print(f"  Rule evaluator accuracy: {rule_acc:.4f}  95% CI [{rule_ci_lo:.4f}, {rule_ci_hi:.4f}]")
    print(f"  Prompt judge accuracy:   {prompt_acc:.4f}  95% CI [{prompt_ci_lo:.4f}, {prompt_ci_hi:.4f}]")
    print(f"  Delta B lift (rule - prompt): {delta_b_lift:+.4f}")
    print(f"  Delta B p-value (paired bootstrap, n={BOOTSTRAP_N}): {delta_b_pvalue}")
    print(f"  Significant (p<0.05): {delta_b_pvalue < 0.05}")
    print(f"\nHeld-out only ({len(ho_results)} tasks)")
    print(f"  Rule evaluator accuracy: {ho_rule_acc:.4f}  95% CI [{ho_rule_ci_lo:.4f}, {ho_rule_ci_hi:.4f}]")
    print(f"  Prompt judge accuracy:   {ho_prompt_acc:.4f}  95% CI [{ho_prompt_ci_lo:.4f}, {ho_prompt_ci_hi:.4f}]")
    print(f"\nAPI errors: {errors} | Total tokens: {total_tokens} | Est. cost: ${estimated_cost_usd}")

    # --- Write outputs ---
    with open(OUTPUT_RAW, "w") as f:
        json.dump(results, f, indent=2)

    with open(OUTPUT_TRACES, "w") as f:
        for r in ho_results:
            f.write(json.dumps(r) + "\n")

    ablation_results = {
        "_meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seed": SEED,
            "bootstrap_n": BOOTSTRAP_N,
            "rule_model": "ScoringEvaluator (deterministic rule-based)",
            "prompt_model": JUDGE_MODEL,
            "held_out_n": len(ho_results),
            "total_n": len(results),
            "api_errors": errors,
            "total_tokens_used": total_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "note_delta_a": (
                "Delta A (LoRA-trained judge vs baseline) requires GPU training. "
                "Run scripts/train_judge_lora.py in Google Colab T4, then scripts/run_ablation.py. "
                "The training script and preference pairs (eval/tenacious_bench/training_data/pairs_v2.jsonl) "
                "are complete and ready."
            ),
        },
        "week10_tau2_baseline": {
            "variant": "V0",
            "agent_name": "llm_agent",
            "description": "Week 10 baseline — original LLMAgent on tau2-bench retail",
            "split": "tau2_retail",
            "mean_pass_at_1": 0.7267,
            "bootstrap_ci_95": [0.6504, 0.7917],
            "mean_cost_per_task": 0.0199,
            "note": "Reused from Week 10; not re-run this week per cost-discipline rules.",
        },
        "delta_b_rule_evaluator": {
            "variant": "V1_RULE_JUDGE",
            "agent_name": "scoring_evaluator_v2_frozen",
            "description": "Deterministic rule-based judge (our built artifact) — no LLM inference",
            "split": "held_out",
            "num_tasks": len(ho_results),
            "accuracy": ho_rule_acc,
            "bootstrap_ci_95": [ho_rule_ci_lo, ho_rule_ci_hi],
            "mean_cost_per_task": 0.0,
            "latency_note": "< 1ms per task (pure Python, no GPU)",
            "lift_over_prompt_judge": round(ho_rule_acc - ho_prompt_acc, 4),
            "significant": delta_b_pvalue < 0.05,
            "p_value": delta_b_pvalue,
        },
        "delta_b_prompt_judge_baseline": {
            "variant": "V0_PROMPT_JUDGE",
            "agent_name": f"prompt_judge_{JUDGE_MODEL.replace('/', '_')}",
            "description": f"Zero-shot prompt judge ({JUDGE_MODEL}) — no training, same rubric in prompt",
            "split": "held_out",
            "num_tasks": len(ho_results),
            "accuracy": ho_prompt_acc,
            "bootstrap_ci_95": [ho_prompt_ci_lo, ho_prompt_ci_hi],
            "mean_cost_per_task": round(estimated_cost_usd / max(len(results), 1), 6),
            "latency_note": "~1-2s per task via OpenRouter API",
        },
        "delta_a_pending": {
            "variant": "V2_DPO_LORA",
            "status": "PENDING_GPU_TRAINING",
            "description": (
                "DPO-trained Qwen2.5-0.5B-Instruct judge with Tenacious preference pairs. "
                "279 preference pairs ready in eval/tenacious_bench/training_data/pairs_v2.jsonl. "
                "Training script: scripts/train_judge_lora.py (requires Colab T4 GPU, ~45 min). "
                "Ablation script: scripts/run_ablation.py."
            ),
            "training_data": "eval/tenacious_bench/training_data/pairs_v2.jsonl",
            "pairs_count": 279,
            "training_script": "scripts/train_judge_lora.py",
            "ablation_script": "scripts/run_ablation.py",
            "backbone": "Qwen/Qwen2.5-0.5B-Instruct",
            "algorithm": "DPO (beta=0.1)",
            "hyperparameters": "r=16, alpha=32, lr=2e-5, epochs=3, batch_size=4",
            "colab_notebook": "See README.md for Colab setup instructions",
        },
    }

    with open(OUTPUT_RESULTS, "w") as f:
        json.dump(ablation_results, f, indent=2)

    # Update cost log
    try:
        with open(COST_LOG_PATH) as f:
            cost_log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cost_log = []

    cost_log.append({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bucket": "held_out_evaluation",
        "model": JUDGE_MODEL,
        "purpose": "delta_b_prompt_judge_ablation",
        "tasks_evaluated": len(results),
        "total_tokens": total_tokens,
        "cost_usd": estimated_cost_usd,
    })
    with open(COST_LOG_PATH, "w") as f:
        json.dump(cost_log, f, indent=4)

    print(f"\nWritten:")
    print(f"  {OUTPUT_RAW}")
    print(f"  {OUTPUT_TRACES}")
    print(f"  {OUTPUT_RESULTS}")
    print(f"  {COST_LOG_PATH} (appended)")


if __name__ == "__main__":
    main()
