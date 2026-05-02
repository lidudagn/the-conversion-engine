"""
Pointwise judge filter for Tenacious-Bench task quality control.

Scores each task on three 1-5 dimensions per the spec requirement:
  - input_coherence         >= 3 to pass
  - ground_truth_verifiability >= 3 to pass
  - rubric_application_clarity >= 3 to pass

Model rotation policy (Li et al. 2025 preference leakage prevention):
  - Generation model (GPT family) is NEVER used as the judge.
  - Judge model: meta-llama/llama-3.1-70b-instruct (different family).

Usage:
  python scripts/judge_filter_pointwise.py --input <pool.jsonl> --output <filtered.jsonl>
  python scripts/judge_filter_pointwise.py --spot-check 50  # calibration run on random 50
"""

import json
import os
import random
import argparse
import time
from pathlib import Path

import requests

JUDGE_MODEL = "meta-llama/llama-3.1-70b-instruct"
PROMPT_PATH = Path("eval/prompts/judge_filter_prompt.md")

# Per-dimension inclusion thresholds (1-5 scale)
THRESHOLDS = {
    "input_coherence": 3,
    "ground_truth_verifiability": 3,
    "rubric_application_clarity": 3,
}

random.seed(42)


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text()


def score_task(task: dict, template: str, api_key: str) -> dict | None:
    task_json = json.dumps(task, indent=2)[:3000]  # truncate to stay within context
    prompt = template.replace("{task_json}", task_json)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/lidya7/tenacious-bench",
    }
    payload = {
        "model": JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 64,
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        scores = json.loads(content)
        return scores
    except Exception as e:
        print(f"  [WARN] Judge call failed for {task.get('task_id', '?')}: {e}")
        return None


def passes_thresholds(scores: dict) -> bool:
    return all(
        scores.get(dim, 0) >= threshold
        for dim, threshold in THRESHOLDS.items()
    )


def run_filter(input_path: Path, output_path: Path, api_key: str):
    template = load_prompt_template()
    tasks = [json.loads(l) for l in input_path.read_text().splitlines() if l.strip()]
    print(f"Loaded {len(tasks)} tasks from {input_path}")

    passed, failed, errored = [], [], []
    for i, task in enumerate(tasks):
        print(f"  [{i+1}/{len(tasks)}] {task.get('task_id', '?')} ", end="", flush=True)
        scores = score_task(task, template, api_key)
        if scores is None:
            errored.append(task)
            print("ERROR")
            continue

        ok = passes_thresholds(scores)
        task.setdefault("metadata", {})["quality_filter_scores"] = scores
        task["metadata"]["quality_filter_pass"] = ok

        if ok:
            passed.append(task)
            print(f"PASS {scores}")
        else:
            failed.append(task)
            print(f"FAIL {scores}")

        time.sleep(0.3)  # rate limit

    output_path.write_text("\n".join(json.dumps(t) for t in passed))
    print(f"\nFilter complete: {len(passed)} passed / {len(failed)} failed / {len(errored)} errors")
    print(f"Saved {len(passed)} tasks to {output_path}")

    # Log summary
    log = {
        "input": str(input_path),
        "output": str(output_path),
        "judge_model": JUDGE_MODEL,
        "thresholds": THRESHOLDS,
        "n_input": len(tasks),
        "n_passed": len(passed),
        "n_failed": len(failed),
        "n_errored": len(errored),
    }
    log_path = output_path.with_suffix(".filter_log.json")
    log_path.write_text(json.dumps(log, indent=2))
    print(f"Log saved to {log_path}")


def run_spot_check(n: int, api_key: str):
    """Score n random tasks from the existing dataset for calibration."""
    pool_path = Path("eval/tenacious_bench/pilot_50/splits/train.jsonl")
    tasks = [json.loads(l) for l in pool_path.read_text().splitlines() if l.strip()]
    sample = random.sample(tasks, min(n, len(tasks)))
    template = load_prompt_template()

    results = []
    for i, task in enumerate(sample):
        print(f"  [{i+1}/{len(sample)}] {task.get('task_id', '?')} ", end="", flush=True)
        scores = score_task(task, template, api_key)
        if scores:
            ok = passes_thresholds(scores)
            results.append({"task_id": task.get("task_id"), "scores": scores, "pass": ok})
            print(f"{'PASS' if ok else 'FAIL'} {scores}")
        time.sleep(0.3)

    pass_rate = sum(1 for r in results if r["pass"]) / len(results) if results else 0
    print(f"\nSpot-check ({len(results)} tasks): {pass_rate:.1%} pass rate")

    out = Path("eval/tenacious_bench/spot_check_calibration.json")
    out.write_text(json.dumps({"thresholds": THRESHOLDS, "judge_model": JUDGE_MODEL, "results": results}, indent=2))
    print(f"Saved to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Input .jsonl pool to filter")
    parser.add_argument("--output", type=Path, help="Output filtered .jsonl")
    parser.add_argument("--spot-check", type=int, metavar="N",
                        help="Run calibration spot-check on N random existing tasks")
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")

    if args.spot_check:
        run_spot_check(args.spot_check, api_key)
    elif args.input and args.output:
        run_filter(args.input, args.output, api_key)
    else:
        parser.print_help()
