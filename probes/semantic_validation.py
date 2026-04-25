"""
Semantic Wrong-Segment Validation for ToneGuard
Runs 15 adversarial probes that require semantic understanding (not keyword matching)
through ToneGuard with LLM client enabled. Measures actual catch rate.

Uses free model: meta-llama/llama-3.3-70b-instruct:free
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from openai import AsyncOpenAI
from agent.tone_guard import ToneGuard, ToneResult
from agent.policy_engine import PolicyDecision

# ── Semantic probes: wrong-segment pitch content + correct policy context ──

SEMANTIC_PROBES = [
    # --- Seg1 language to Seg2 (restructuring) context ---
    {
        "id": "SEM-01",
        "category": "wrong_segment_pitch",
        "draft": (
            "Congratulations on the recent Series A! Teams fresh off a funding round often "
            "need to scale engineering fast to hit the product milestones investors are watching. "
            "We'd love to chat about how Tenacious can help you ship faster."
        ),
        "policy": {"pitch_segment": 2, "tone_mode": "exploratory"},
        "expected_fail": True,
        "why": "Seg1 growth pitch to a company that should get Seg2 restructuring pitch"
    },
    {
        "id": "SEM-02",
        "category": "wrong_segment_pitch",
        "draft": (
            "With your recent funding, now is the perfect time to double down on engineering "
            "velocity. Most founders in your position are hiring 3-5 engineers per month — "
            "Tenacious can help you hit that pace without the recruiting overhead."
        ),
        "policy": {"pitch_segment": 2, "tone_mode": "exploratory"},
        "expected_fail": True,
        "why": "Growth/hiring language to restructuring company"
    },
    {
        "id": "SEM-03",
        "category": "wrong_segment_pitch",
        "draft": (
            "I noticed your team has been growing rapidly — exciting times! When engineering "
            "teams scale from 20 to 50, outsourcing non-core functions becomes a multiplier. "
            "Would a 15-minute call make sense this week?"
        ),
        "policy": {"pitch_segment": 2, "tone_mode": "exploratory"},
        "expected_fail": True,
        "why": "Growth narrative sent to cost-cutting company"
    },
    # --- Seg2 language to Seg1 (recently funded) context ---
    {
        "id": "SEM-04",
        "category": "wrong_segment_pitch",
        "draft": (
            "In times of organizational change, maintaining engineering output while "
            "optimizing costs is critical. Tenacious specializes in helping teams right-size "
            "without losing delivery velocity."
        ),
        "policy": {"pitch_segment": 1, "tone_mode": "assertive"},
        "expected_fail": True,
        "why": "Restructuring/cost-cutting pitch to freshly funded startup"
    },
    {
        "id": "SEM-05",
        "category": "wrong_segment_pitch",
        "draft": (
            "After a restructuring event, smart leaders look for ways to rebuild capacity "
            "at a sustainable cost. We've helped over a dozen companies in similar situations "
            "replace higher-cost roles with offshore equivalents."
        ),
        "policy": {"pitch_segment": 1, "tone_mode": "assertive"},
        "expected_fail": True,
        "why": "Post-layoff language to a company that just raised Series A"
    },
    # --- Seg4 language to low AI maturity context ---
    {
        "id": "SEM-06",
        "category": "wrong_segment_pitch",
        "draft": (
            "Your ML pipeline migration from on-prem to cloud is a move we've guided "
            "several teams through. Our data platform engineers can accelerate the transition "
            "and help you avoid the common pitfalls of model serving at scale."
        ),
        "policy": {"pitch_segment": 1, "tone_mode": "exploratory",
                   "assertable_signals": [], "question_signals": []},
        "expected_fail": True,
        "why": "ML platform migration pitch to company with no AI function"
    },
    {
        "id": "SEM-07",
        "category": "wrong_segment_pitch",
        "draft": (
            "Building agentic systems requires a specific engineering DNA — prompt engineering, "
            "evaluation harnesses, and retrieval-augmented generation pipelines. Tenacious has a "
            "dedicated AI squad ready to integrate into your existing ML workflow."
        ),
        "policy": {"pitch_segment": 2, "tone_mode": "exploratory",
                   "assertable_signals": [], "question_signals": []},
        "expected_fail": True,
        "why": "Advanced AI pitch to company being restructured with no AI signals"
    },
    # --- Seg3 language to wrong context ---
    {
        "id": "SEM-08",
        "category": "wrong_segment_pitch",
        "draft": (
            "New engineering leaders typically reassess vendor relationships in their first "
            "90 days. Since your new CTO joined last month, this could be a great time to "
            "explore how Tenacious fits into the new technical strategy."
        ),
        "policy": {"pitch_segment": 1, "tone_mode": "assertive"},
        "expected_fail": True,
        "why": "Leadership transition pitch to a freshly funded company (no leadership change signal)"
    },
    # --- Correct pitches (should PASS) ---
    {
        "id": "SEM-09",
        "category": "correct_pitch",
        "draft": (
            "I came across your company while researching teams that recently closed a "
            "funding round. Scaling engineering quickly after a raise is one of the toughest "
            "challenges — would it be worth a quick call to explore how Tenacious can help?"
        ),
        "policy": {"pitch_segment": 1, "tone_mode": "assertive"},
        "expected_fail": False,
        "why": "Correct Seg1 pitch to Seg1 context"
    },
    {
        "id": "SEM-10",
        "category": "correct_pitch",
        "draft": (
            "Teams going through organizational changes often find that maintaining delivery "
            "velocity is the hardest part. Tenacious specializes in helping companies keep "
            "shipping while restructuring — would a brief conversation be useful?"
        ),
        "policy": {"pitch_segment": 2, "tone_mode": "exploratory"},
        "expected_fail": False,
        "why": "Correct Seg2 pitch to Seg2 context"
    },
    {
        "id": "SEM-11",
        "category": "correct_pitch",
        "draft": (
            "I noticed a leadership change in your engineering organization — congratulations "
            "to the new CTO. New leaders often want a fresh perspective on vendor partnerships. "
            "Would it be worth a 15-minute introduction?"
        ),
        "policy": {"pitch_segment": 3, "tone_mode": "exploratory"},
        "expected_fail": False,
        "why": "Correct Seg3 pitch to Seg3 context"
    },
    {
        "id": "SEM-12",
        "category": "correct_pitch",
        "draft": (
            "Your team's investment in ML infrastructure is impressive. If you're looking to "
            "accelerate a specific build — model serving, data contracts, or evaluation — "
            "Tenacious has a consulting squad that works on exactly that."
        ),
        "policy": {"pitch_segment": 4, "tone_mode": "assertive",
                   "assertable_signals": ["ai_maturity"], "question_signals": []},
        "expected_fail": False,
        "why": "Correct Seg4 pitch to high-AI-maturity Seg4 context"
    },
    # --- Subtle mismatches ---
    {
        "id": "SEM-13",
        "category": "wrong_segment_pitch",
        "draft": (
            "Exciting news about your growth! Scaling from 15 to 50 engineers in a year "
            "is ambitious — most teams find their recruiting pipeline can't keep up. "
            "That's exactly where Tenacious adds value."
        ),
        "policy": {"pitch_segment": 2, "tone_mode": "exploratory"},
        "expected_fail": True,
        "why": "Subtle: growth/hiring enthusiasm sent to restructuring company"
    },
    {
        "id": "SEM-14",
        "category": "wrong_segment_pitch",
        "draft": (
            "Cutting costs while maintaining quality is the hardest balancing act in tech. "
            "The companies that get it right are the ones that offshore strategically rather "
            "than cutting heads. Tenacious can help you do that cleanly."
        ),
        "policy": {"pitch_segment": 1, "tone_mode": "assertive"},
        "expected_fail": True,
        "why": "Cost-cutting/offshore language to a freshly funded startup"
    },
    {
        "id": "SEM-15",
        "category": "correct_pitch",
        "draft": (
            "Hi — I wanted to reach out because your company looks like a strong fit for "
            "what we do at Tenacious. We help teams scale engineering output through managed "
            "outsourcing. Would a quick call make sense?"
        ),
        "policy": {"pitch_segment": 1, "tone_mode": "exploratory"},
        "expected_fail": False,
        "why": "Generic exploratory email — should pass in any context"
    },
]


def run_validation():
    """Run all semantic probes through ToneGuard with LLM enabled."""
    return asyncio.run(_run_validation_async())


async def _run_validation_async():
    """Async implementation of validation."""
    # Use free model via OpenRouter
    llm = AsyncOpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
    )

    guard = ToneGuard(style_guide="Tenacious voice: professional, specific, never pushy.", llm_client=llm)

    results = []
    correct = 0
    total = len(SEMANTIC_PROBES)

    print(f"\n{'='*60}")
    print(f"Semantic ToneGuard Validation — {total} probes")
    print(f"Model: {os.environ.get('DEV_MODEL', 'meta-llama/llama-3.3-70b-instruct:free')}")
    print(f"{'='*60}\n")

    for probe in SEMANTIC_PROBES:
        policy = PolicyDecision()
        policy.pitch_segment = probe["policy"].get("pitch_segment")
        policy.tone_mode = probe["policy"].get("tone_mode", "exploratory")
        policy.assertable_signals = probe["policy"].get("assertable_signals", [])
        policy.question_signals = probe["policy"].get("question_signals", [])

        try:
            result = await guard.check(draft=probe["draft"], policy=policy)
            caught = result.hard_fail if probe["expected_fail"] else not result.hard_fail

            results.append({
                "id": probe["id"],
                "category": probe["category"],
                "expected_fail": probe["expected_fail"],
                "actual_hard_fail": result.hard_fail,
                "hard_fail_reason": result.hard_fail_reason,
                "score": result.overall_score,
                "issues": result.issues,
                "correct": caught,
                "why": probe["why"],
            })

            if caught:
                correct += 1
                marker = "✓"
            else:
                marker = "✗"

            print(f"  {marker} {probe['id']}: expect_fail={probe['expected_fail']}, "
                  f"got_fail={result.hard_fail} | {probe['why'][:60]}")

        except Exception as e:
            results.append({
                "id": probe["id"],
                "category": probe["category"],
                "error": str(e),
                "correct": False,
            })
            print(f"  ✗ {probe['id']}: ERROR — {e}")

    # Compute metrics
    wrong_segment_probes = [r for r in results if r.get("category") == "wrong_segment_pitch"]
    correct_probes = [r for r in results if r.get("category") == "correct_pitch"]

    tp = sum(1 for r in wrong_segment_probes if r.get("actual_hard_fail", False))
    fn = sum(1 for r in wrong_segment_probes if not r.get("actual_hard_fail", False))
    tn = sum(1 for r in correct_probes if not r.get("actual_hard_fail", False))
    fp = sum(1 for r in correct_probes if r.get("actual_hard_fail", False))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = correct / total if total > 0 else 0

    summary = {
        "timestamp": datetime.now().isoformat(),
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "total_probes": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "wrong_segment_probes": len(wrong_segment_probes),
        "true_positives": tp,
        "false_negatives": fn,
        "correct_pitch_probes": len(correct_probes),
        "true_negatives": tn,
        "false_positives": fp,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "catch_rate_semantic": f"{tp}/{tp+fn} ({round(recall*100, 1)}%)",
        "false_positive_rate": f"{fp}/{fp+tn} ({round(fp/(fp+tn)*100 if (fp+tn) > 0 else 0, 1)}%)",
        "per_probe": results,
    }

    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"  Overall accuracy: {correct}/{total} ({accuracy:.1%})")
    print(f"  Semantic catch rate (recall): {tp}/{tp+fn} ({recall:.1%})")
    print(f"  Precision: {precision:.1%}")
    print(f"  False positive rate: {fp}/{fp+tn}")
    print(f"  F1: {f1:.3f}")
    print(f"{'='*60}")

    # Save results
    output_file = Path(__file__).parent / "semantic_validation_results.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved to {output_file}")

    return summary


if __name__ == "__main__":
    run_validation()
