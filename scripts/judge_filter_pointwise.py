"""
Pointwise judge filter for Tenacious-Bench task quality control.

MODEL ROLES (explicit separation per rubric requirement)
--------------------------------------------------------
DEV_TIER_MODEL  — high-volume filtering of every generated task.
                  Family: open-weights (Llama). Cross-family from generator
                  (GPT-4o-mini) per Li et al. 2025 preference leakage prevention.
EVAL_TIER_MODEL — calibration spot-check only. Never used on full pool.
                  Used to verify that dev-tier thresholds are correctly set.
                  Sample size: CALIBRATION_N = 50 tasks.

PIPELINE STAGES
---------------
1. Pointwise scoring  — score every task on 3 dimensions (1-5 each).
2. Threshold filter   — drop any task where any dimension < 3.
3. Pairwise dedup     — cluster near-duplicate tasks; within each cluster
                        keep only the highest ground_truth_verifiability scorer.
4. Calibration check  — optional eval-tier spot-check on CALIBRATION_N tasks
                        to verify dev-tier threshold alignment.

Three 1-5 dimensions:
  input_coherence            >= 3 to pass
  ground_truth_verifiability >= 3 to pass  (also used as pairwise tiebreaker)
  rubric_application_clarity >= 3 to pass

Usage:
  # Full filter pipeline (score + dedup):
  python scripts/judge_filter_pointwise.py --input pool.jsonl --output filtered.jsonl

  # Calibration: compare dev-tier vs eval-tier on 50 random tasks:
  python scripts/judge_filter_pointwise.py --calibrate
"""

import json
import os
import random
import argparse
import time
from pathlib import Path

# --- Model roles (explicit) ---------------------------------------------------
# DEV_TIER: high-volume filtering. Different family from generator (GPT-4o-mini).
DEV_TIER_MODEL = "meta-llama/llama-3.1-70b-instruct"
# EVAL_TIER: calibration spot-check only. Never run on full pool.
EVAL_TIER_MODEL = "openai/gpt-4o"

# Calibration sample size (rubric requirement: spot-check 50 tasks with eval-tier)
CALIBRATION_N = 50

PROMPT_PATH = Path("eval/prompts/judge_filter_prompt.md")

# Per-dimension inclusion thresholds (1–5 scale)
THRESHOLDS = {
    "input_coherence": 3,
    "ground_truth_verifiability": 3,
    "rubric_application_clarity": 3,
}

# Pairwise dedup: two tasks are near-duplicates if they share the same
# (category, inferred_segment, verdict) AND their candidate_output first-150-char
# prefix overlaps > 60%. Within a cluster, keep the highest ground_truth_verifiability.
DEDUP_OVERLAP_THRESHOLD = 0.60

random.seed(42)


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text()


def call_judge(task: dict, template: str, api_key: str, model: str) -> dict | None:
    task_json = json.dumps(task, indent=2)[:3000]
    prompt = template.replace("{task_json}", task_json)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/lidya7/tenacious-bench",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 64,
    }

    try:
        import requests
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return json.loads(content)
    except Exception as e:
        print(f"  [WARN] Judge call failed for {task.get('task_id', '?')}: {e}")
        return None


def passes_thresholds(scores: dict) -> bool:
    return all(scores.get(dim, 0) >= thr for dim, thr in THRESHOLDS.items())


# --- Pairwise dedup -----------------------------------------------------------

def _dedup_key(task: dict) -> tuple:
    """Coarse grouping key for near-duplicate detection."""
    gt = task.get("ground_truth", {})
    return (
        task.get("metadata", {}).get("category", ""),
        str(gt.get("inferred_segment", "")),
        str(gt.get("verdict", "")),
    )


def _text_overlap(a: str, b: str) -> float:
    """Character-level overlap ratio on first 150 chars of candidate_output."""
    a, b = a[:150].lower(), b[:150].lower()
    if not a or not b:
        return 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    matches = sum(c in longer for c in shorter)
    return matches / len(shorter)


def dedup_pairwise(tasks: list[dict]) -> tuple[list[dict], int]:
    """
    Cluster near-duplicates and keep the best per cluster.

    Two tasks are near-duplicates when they share the same coarse key AND
    their candidate_output prefixes overlap > DEDUP_OVERLAP_THRESHOLD.
    Within each cluster the task with the highest ground_truth_verifiability
    score is kept (tiebreak: first encountered).

    Returns (deduplicated_tasks, n_removed).
    """
    from collections import defaultdict

    # Group by coarse key first to limit O(n²) comparisons
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for t in tasks:
        groups[_dedup_key(t)].append(t)

    kept: list[dict] = []
    n_removed = 0

    for group in groups.values():
        if len(group) == 1:
            kept.append(group[0])
            continue

        # Build clusters within the group
        clusters: list[list[dict]] = []
        assigned = [False] * len(group)

        for i, ti in enumerate(group):
            if assigned[i]:
                continue
            cluster = [ti]
            assigned[i] = True
            text_i = ti.get("candidate_output", "")
            for j, tj in enumerate(group):
                if assigned[j]:
                    continue
                if _text_overlap(text_i, tj.get("candidate_output", "")) > DEDUP_OVERLAP_THRESHOLD:
                    cluster.append(tj)
                    assigned[j] = True
            clusters.append(cluster)

        # Keep best per cluster (highest ground_truth_verifiability)
        for cluster in clusters:
            best = max(
                cluster,
                key=lambda t: t.get("metadata", {})
                              .get("quality_filter_scores", {})
                              .get("ground_truth_verifiability", 0),
            )
            kept.append(best)
            n_removed += len(cluster) - 1

    return kept, n_removed


# --- Main pipeline ------------------------------------------------------------

def run_filter(input_path: Path, output_path: Path, api_key: str):
    """Stage 1 (pointwise) + Stage 3 (pairwise dedup)."""
    template = load_prompt_template()
    tasks = [json.loads(l) for l in input_path.read_text().splitlines() if l.strip()]
    print(f"Loaded {len(tasks)} tasks from {input_path}")
    print(f"Judge model (dev-tier): {DEV_TIER_MODEL}")

    passed, failed, errored = [], [], []
    for i, task in enumerate(tasks):
        print(f"  [{i+1}/{len(tasks)}] {task.get('task_id', '?')} ", end="", flush=True)
        scores = call_judge(task, template, api_key, DEV_TIER_MODEL)
        if scores is None:
            errored.append(task)
            print("ERROR")
            continue

        ok = passes_thresholds(scores)
        task.setdefault("metadata", {})["quality_filter_scores"] = scores
        task["metadata"]["quality_filter_pass"] = ok
        task["metadata"]["judge_model"] = DEV_TIER_MODEL

        if ok:
            passed.append(task)
            print(f"PASS {scores}")
        else:
            failed.append(task)
            print(f"FAIL {scores}")

        time.sleep(0.3)

    print(f"\nStage 1 complete: {len(passed)} passed / {len(failed)} failed / {len(errored)} errors")

    # Stage 3: pairwise dedup
    deduped, n_removed = dedup_pairwise(passed)
    print(f"Stage 3 pairwise dedup: removed {n_removed} near-duplicates → {len(deduped)} tasks kept")

    output_path.write_text("\n".join(json.dumps(t) for t in deduped))
    print(f"Saved {len(deduped)} tasks to {output_path}")

    log = {
        "input": str(input_path),
        "output": str(output_path),
        "judge_model_dev_tier": DEV_TIER_MODEL,
        "judge_model_eval_tier": EVAL_TIER_MODEL,
        "thresholds": THRESHOLDS,
        "dedup_overlap_threshold": DEDUP_OVERLAP_THRESHOLD,
        "n_input": len(tasks),
        "n_passed_pointwise": len(passed),
        "n_failed_pointwise": len(failed),
        "n_errored": len(errored),
        "n_removed_dedup": n_removed,
        "n_final": len(deduped),
    }
    log_path = output_path.with_suffix(".filter_log.json")
    log_path.write_text(json.dumps(log, indent=2))
    print(f"Log saved to {log_path}")


def run_calibration(api_key: str, n: int = CALIBRATION_N):
    """
    Stage 4: eval-tier calibration spot-check.

    Scores CALIBRATION_N random tasks with BOTH dev-tier and eval-tier models
    and reports agreement. This verifies that dev-tier thresholds are aligned
    with eval-tier judgments before the thresholds are used on the full pool.

    Per spec: "eval-tier model used only to spot-check 50 sampled tasks."
    """
    pool_path = Path("eval/tenacious_bench/pilot_50/splits/train.jsonl")
    tasks = [json.loads(l) for l in pool_path.read_text().splitlines() if l.strip()]
    sample = random.sample(tasks, min(n, len(tasks)))
    template = load_prompt_template()

    print(f"Calibration: scoring {len(sample)} tasks with both models")
    print(f"  Dev-tier:  {DEV_TIER_MODEL}")
    print(f"  Eval-tier: {EVAL_TIER_MODEL}")

    results = []
    for i, task in enumerate(sample):
        tid = task.get("task_id", f"task_{i}")
        print(f"  [{i+1}/{len(sample)}] {tid} ", end="", flush=True)

        dev_scores  = call_judge(task, template, api_key, DEV_TIER_MODEL)
        time.sleep(0.3)
        eval_scores = call_judge(task, template, api_key, EVAL_TIER_MODEL)
        time.sleep(0.3)

        if dev_scores and eval_scores:
            dev_pass  = passes_thresholds(dev_scores)
            eval_pass = passes_thresholds(eval_scores)
            agree = dev_pass == eval_pass
            results.append({
                "task_id": tid,
                "dev_scores": dev_scores,
                "eval_scores": eval_scores,
                "dev_pass": dev_pass,
                "eval_pass": eval_pass,
                "agree": agree,
            })
            print(f"{'✓' if agree else '✗'} dev={'PASS' if dev_pass else 'FAIL'} eval={'PASS' if eval_pass else 'FAIL'}")
        else:
            print("ERROR")

    if results:
        agreement = sum(1 for r in results if r["agree"]) / len(results)
        print(f"\nCalibration agreement: {agreement:.1%} ({len(results)} tasks)")
        if agreement < 0.80:
            print("  ⚠ Agreement < 80% — consider adjusting thresholds before full run.")

    out = Path("eval/tenacious_bench/calibration_spotcheck.json")
    out.write_text(json.dumps({
        "n_tasks": len(results),
        "dev_tier_model": DEV_TIER_MODEL,
        "eval_tier_model": EVAL_TIER_MODEL,
        "calibration_n": CALIBRATION_N,
        "thresholds": THRESHOLDS,
        "agreement_rate": sum(1 for r in results if r["agree"]) / len(results) if results else None,
        "results": results,
    }, indent=2))
    print(f"Saved to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tenacious-Bench judge filter pipeline")
    parser.add_argument("--input",     type=Path, help="Input .jsonl pool to filter (stages 1+3)")
    parser.add_argument("--output",    type=Path, help="Output filtered .jsonl")
    parser.add_argument("--calibrate", action="store_true",
                        help=f"Run eval-tier calibration spot-check on {CALIBRATION_N} tasks (stage 4)")
    parser.add_argument("--calibrate-n", type=int, default=CALIBRATION_N,
                        help="Override calibration sample size (default: %(default)s)")
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")

    if args.calibrate:
        run_calibration(api_key, n=args.calibrate_n)
    elif args.input and args.output:
        run_filter(args.input, args.output, api_key)
    else:
        parser.print_help()
