"""
Reply simulation: LLM-judge measures simulated reply likelihood for
signal_grounded vs exploratory email variants.

Methodology:
  - Sample up to 15 records of each variant from policy_trace.jsonl
  - Construct a brief email scenario from each record's signals
  - Prompt an LLM judge to act as a busy CTO and decide: REPLY or IGNORE
  - Report reply rates by variant and their delta

Output: outputs/reply_simulation_results.json
"""

import json
import os
import random
import sys
import time
from pathlib import Path

import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
# Free/very cheap model for reply simulation
MODEL = "google/gemma-3-4b-it:free"

random.seed(42)


def load_variants(trace_path: str):
    signal_grounded, exploratory = [], []
    with open(trace_path) as f:
        for line in f:
            r = json.loads(line.strip())
            if r["output"]["abstain"]:
                continue
            tone = r["output"]["tone_mode"]
            if tone in ("assertive", "suggestive", "hedged"):
                signal_grounded.append(r)
            elif tone == "exploratory":
                exploratory.append(r)
    return signal_grounded, exploratory


def build_email_scenario(record: dict) -> str:
    """Construct a brief email scenario from policy trace signals."""
    inp = record["inputs"]
    out = record["output"]

    ai_score = inp.get("ai_maturity_score", 0)
    icp_conf = inp.get("icp_confidence", 0.0)
    seg = out.get("pitch_segment", 1)
    tone = out.get("tone_mode", "exploratory")
    assertable = out.get("assertable_signals", [])
    gap = out.get("use_competitor_gap", False)
    contradictions = out.get("contradictions_used", 0)

    seg_labels = {
        1: "operational efficiency via outsourcing",
        2: "cost reduction through managed staffing",
        3: "dedicated offshore engineering teams",
        4: "AI/ML capability uplift with dedicated engineers",
    }
    pitch = seg_labels.get(seg, "technology consulting services")

    signals = []
    if "funding" in assertable:
        signals.append("recent funding activity")
    if "leadership" in assertable:
        signals.append("a recent CTO/VP Engineering change")
    if "layoffs" in assertable:
        signals.append("a recent headcount reduction")
    if "job_velocity" in assertable:
        signals.append("a spike in job postings")
    if ai_score >= 2:
        signals.append(f"AI maturity score {ai_score}/3")
    if gap:
        signals.append("a competitor capability gap analysis")
    if contradictions > 0:
        signals.append("cross-signal research finding")

    signal_str = (
        f"The email references {', '.join(signals)}."
        if signals else "The email uses a generic pitch with no specific signals."
    )

    tone_desc = {
        "assertive": "direct, confident, data-backed",
        "suggestive": "evidence-based with a soft recommendation",
        "hedged": "cautious, framed as a question",
        "exploratory": "generic, curiosity-driven, no specific signals",
    }.get(tone, "neutral")

    return (
        f"You are a {_role(seg)} at a mid-sized tech company.\n"
        f"You receive an unsolicited sales email pitching: {pitch}.\n"
        f"Tone: {tone_desc}. {signal_str}\n"
        f"ICP fit score (internal): {icp_conf:.2f}/1.00.\n"
        f"Would you reply to explore further? Answer with exactly one word: REPLY or IGNORE."
    )


def _role(seg):
    return {1: "VP Operations", 2: "CFO", 3: "VP Engineering", 4: "CTO"}.get(seg, "CTO")


def judge_reply(scenario: str, retries: int = 3) -> str | None:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/tenacious/conversion-engine",
        "X-Title": "Conversion Engine Reply Simulation",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": scenario}],
        "max_tokens": 10,
        "temperature": 0.3,
    }
    for attempt in range(retries):
        try:
            resp = requests.post(OPENROUTER_BASE_URL, headers=headers,
                                 json=payload, timeout=30)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip().upper()
            if "REPLY" in content:
                return "REPLY"
            elif "IGNORE" in content:
                return "IGNORE"
            else:
                return "IGNORE"  # ambiguous → conservative
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(2)
    return None


def run_simulation(sample_size: int = 15):
    trace_path = Path(__file__).parent.parent / "outputs" / "policy_trace.jsonl"
    out_path = Path(__file__).parent.parent / "outputs" / "reply_simulation_results.json"

    sg_all, ex_all = load_variants(str(trace_path))
    sg_sample = random.sample(sg_all, min(sample_size, len(sg_all)))
    ex_sample = random.sample(ex_all, min(sample_size, len(ex_all)))

    print(f"Simulating replies: {len(sg_sample)} signal_grounded + {len(ex_sample)} exploratory")
    print(f"Model: {MODEL}\n")

    results = {"signal_grounded": [], "exploratory": []}

    for variant_name, sample in [("signal_grounded", sg_sample), ("exploratory", ex_sample)]:
        replies = 0
        for i, record in enumerate(sample):
            scenario = build_email_scenario(record)
            decision = judge_reply(scenario)
            replied = decision == "REPLY"
            if replied:
                replies += 1
            results[variant_name].append({
                "decision_id": record["decision_id"],
                "tone_mode": record["output"]["tone_mode"],
                "icp_confidence": record["inputs"]["icp_confidence"],
                "ai_maturity_score": record["inputs"]["ai_maturity_score"],
                "decision": decision,
            })
            status = "REPLY" if replied else "IGNORE"
            print(f"  [{variant_name[:2].upper()}] {i+1}/{len(sample)} "
                  f"(icp={record['inputs']['icp_confidence']:.2f}) → {status}")
            time.sleep(0.5)  # gentle rate limiting

        n = len(sample)
        rate = replies / n if n > 0 else 0.0
        results[f"{variant_name}_summary"] = {
            "n": n, "replies": replies, "reply_rate": round(rate, 4),
            "reply_rate_pct": round(rate * 100, 1),
        }
        print(f"  → {variant_name}: {replies}/{n} replied ({rate*100:.1f}%)\n")

    sg_rate = results["signal_grounded_summary"]["reply_rate"]
    ex_rate = results["exploratory_summary"]["reply_rate"]
    delta = round(sg_rate - ex_rate, 4)
    results["delta"] = {
        "signal_grounded_minus_exploratory": delta,
        "delta_pct_points": round(delta * 100, 1),
    }
    results["methodology"] = (
        f"LLM judge ({MODEL}) roleplays as a tech executive receiving each email. "
        "Scenario constructed from policy_trace signals. "
        "Answer constrained to REPLY/IGNORE. Seed=42. "
        "Caveat: simulated prospects, not live interactions."
    )
    results["model"] = MODEL

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n=== RESULTS ===")
    print(f"Signal-grounded reply rate: {sg_rate*100:.1f}% (n={results['signal_grounded_summary']['n']})")
    print(f"Exploratory reply rate:     {ex_rate*100:.1f}% (n={results['exploratory_summary']['n']})")
    print(f"Delta (SG − EX):            {delta*100:+.1f} percentage points")
    print(f"\nSaved: {out_path}")
    return results


if __name__ == "__main__":
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    run_simulation(sample_size=15)
