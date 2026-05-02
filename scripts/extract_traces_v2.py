"""
Trace-derived task extraction from real Week 10 agent execution logs.

Sources:
  - outputs/policy_trace.jsonl     (123 real policy decisions)
  - outputs/hiring_signal_brief_*  (35 real enrichment outputs)

Strategy:
  Each non-abstain policy_trace entry is converted to one PASS task and one
  FAIL task (wrong-segment or overclaiming variant), yielding ~60 trace-derived
  tasks that use the real agent decisions as ground truth.

  The hiring_signal_brief is reconstructed from the trace's input signals.
  Candidate emails are generated from deterministic templates (no LLM cost).

Output: eval/tenacious_bench/pilot_50/trace_derived_pool.jsonl
"""

import json
import uuid
import random
from pathlib import Path
from datetime import datetime

random.seed(42)

SEGMENTS = {1: "Growth", 2: "Restructuring", 3: "Enterprise", 4: "AI"}
WRONG_SEGMENT_MAP = {1: 2, 2: 1, 3: 1, 4: 2}  # D06: wrong segment for each correct one

# Template companies (synthetic but realistic, drawn from Crunchbase domain)
SYNTHETIC_COMPANIES = [
    ("Mobitek Ltd", "mobitek.io", "Nairobi"),
    ("DataBridge Analytics", "databridge.co", "Lagos"),
    ("CloudPeak Solutions", "cloudpeak.io", "Accra"),
    ("Finova Systems", "finova.co", "Cairo"),
    ("Stackwise Technologies", "stackwise.io", "Johannesburg"),
    ("Nexgen Platforms", "nexgen.co", "Dar es Salaam"),
    ("Orbis Software", "orbis.io", "Kigali"),
    ("Phaero Technologies", "phaero.co", "Tunis"),
    ("Lumino Systems", "lumino.io", "Casablanca"),
    ("Redwood Analytics", "redwood.co", "Addis Ababa"),
    ("Syncpath Ltd", "syncpath.io", "Kampala"),
    ("Vertex Innovations", "vertexin.co", "Abidjan"),
    ("Tessera Cloud", "tessera.io", "Douala"),
    ("Harbinger Tech", "harbinger.co", "Lusaka"),
    ("Quanta Systems", "quanta.io", "Harare"),
    ("Ironbolt Software", "ironbolt.co", "Maputo"),
    ("Plyxa Ltd", "plyxa.io", "Dakar"),
    ("Crestwave Digital", "crestwave.co", "Bamako"),
    ("Axiom Platforms", "axiom.io", "Conakry"),
    ("Driftstone Analytics", "driftstone.co", "Freetown"),
]

# Pass email templates per segment and tone
PASS_TEMPLATES = {
    (1, "assertive"): (
        "Subject: Engineering capacity for {company}'s growth phase\n\n"
        "Hi {name},\n\n"
        "Noticed {company} recently closed a {funding_event} — congratulations. "
        "Growth-stage scaling typically surfaces a gap between hiring velocity and "
        "available senior engineering talent.\n\n"
        "Tenacious works with Series A-B companies to close that gap quickly — "
        "typically within two to three weeks for senior backend and platform roles. "
        "Our bench currently has availability.\n\n"
        "Would a 20-minute call to assess fit make sense this week?\n\n"
        "Best,\nTenacious Consulting"
    ),
    (1, "exploratory"): (
        "Subject: A thought on {company}'s engineering team\n\n"
        "Hi {name},\n\n"
        "Came across {company} — looks like you may be in a growth phase. "
        "If scaling your engineering team is on the roadmap, I'd be curious whether "
        "the current hiring pipeline is keeping up with product demand.\n\n"
        "Happy to share how Tenacious has helped similar teams — no commitment needed.\n\n"
        "Worth a brief conversation?\n\n"
        "Best,\nTenacious Consulting"
    ),
    (2, "assertive"): (
        "Subject: Engineering efficiency for {company}'s current phase\n\n"
        "Hi {name},\n\n"
        "{company} has reduced headcount recently. That often creates a short window "
        "where the remaining team carries disproportionate load while the org restructures.\n\n"
        "Tenacious provides targeted senior contractor support — cost-controlled, "
        "no long-term headcount commitment. We can typically onboard within two weeks.\n\n"
        "Would it be useful to explore whether that fits your current situation?\n\n"
        "Best,\nTenacious Consulting"
    ),
    (2, "exploratory"): (
        "Subject: Flexible engineering support for {company}\n\n"
        "Hi {name},\n\n"
        "Noticed some changes at {company}. If the engineering team is carrying "
        "extra load during a restructure, Tenacious offers flexible contractor support "
        "that doesn't add permanent headcount.\n\n"
        "Curious whether that kind of arrangement would be useful to explore.\n\n"
        "Best,\nTenacious Consulting"
    ),
    (4, "assertive"): (
        "Subject: AI engineering bench for {company}\n\n"
        "Hi {name},\n\n"
        "{company} appears to be moving AI projects toward production. "
        "The gap between R&D prototypes and production-ready ML systems is where "
        "teams most commonly hit capacity constraints.\n\n"
        "Tenacious has senior MLOps and platform engineers available for short "
        "engagements — typically two to six months to get a model pipeline to production.\n\n"
        "Worth a conversation?\n\n"
        "Best,\nTenacious Consulting"
    ),
    (4, "exploratory"): (
        "Subject: A question about {company}'s AI roadmap\n\n"
        "Hi {name},\n\n"
        "Based on public signals, {company} may be working on AI/ML initiatives. "
        "If there's a gap between your current engineering capacity and your AI "
        "production goals, Tenacious could be useful.\n\n"
        "Would it make sense to have a brief conversation?\n\n"
        "Best,\nTenacious Consulting"
    ),
}

# Fail email templates — deliberately violate policy (D06 wrong-segment)
FAIL_D06_TEMPLATES = {
    1: (  # Wrong: Seg1 pitch to a Seg2/Seg4 company
        "Subject: Scale your team fast with Tenacious\n\n"
        "Hi {name},\n\n"
        "{company} is clearly in hypergrowth mode. We help world-class companies "
        "like yours supercharge their engineering hiring and 10x their output.\n\n"
        "Our A-players are ready to accelerate your growth journey today. "
        "Don't miss out on this opportunity — let's synergize.\n\n"
        "Best,\nTenacious Consulting"
    ),
    2: (  # Wrong: Seg2 pitch to a Seg1/Seg4 company
        "Subject: Cost control for {company}\n\n"
        "Hi {name},\n\n"
        "Given the recent headcount changes at {company}, we can help you do more "
        "with less. Our gold standard efficiency model will help you freeze hiring "
        "and reduce engineering costs by leveraging our outsourced talent.\n\n"
        "This is a quick question: are you open to cutting your engineering budget?\n\n"
        "Best,\nTenacious Consulting"
    ),
}


def build_brief_from_trace(trace: dict, company: str, domain: str) -> dict:
    """Construct a hiring_signal_brief from policy trace inputs."""
    inp = trace["inputs"]
    out = trace["output"]

    funding_event = None
    funding_confidence = "low"
    if "SIGNAL_FUNDING_HIGH" in " ".join(trace.get("rules_triggered", [])):
        funding_event = "Series A"
        funding_confidence = "high"
    elif "SIGNAL_FUNDING_MEDIUM" in " ".join(trace.get("rules_triggered", [])):
        funding_event = "Seed"
        funding_confidence = "medium"

    layoffs_event = False
    layoffs_confidence = "low"
    if "SIGNAL_LAYOFFS_HIGH" in " ".join(trace.get("rules_triggered", [])):
        layoffs_event = True
        layoffs_confidence = "high"
    elif "SIGNAL_LAYOFFS_MEDIUM" in " ".join(trace.get("rules_triggered", [])):
        layoffs_event = True
        layoffs_confidence = "medium"

    ai_score = inp.get("ai_maturity_score", 0)

    return {
        "prospect_name": company,
        "prospect_domain": domain,
        "funding": {
            "event": funding_event,
            "confidence": funding_confidence,
            "source": "crunchbase"
        },
        "layoffs": {
            "event": layoffs_event,
            "headcount": 30 if layoffs_event else 0,
            "confidence": layoffs_confidence
        },
        "ai_maturity": {
            "score": ai_score,
            "confidence": inp.get("ai_maturity_confidence", "low"),
        },
        "icp_segment": {
            "primary": out.get("pitch_segment"),
            "confidence": inp.get("icp_confidence", 0.0),
        },
        "bench_match": {
            "available": 12 if out.get("bench_match") else 0,
            "matched_stacks": ["Python", "Go"] if out.get("bench_match") else []
        },
        "_source": "policy_trace",
        "_trace_decision_id": trace["decision_id"],
    }


def render_email(template: str, company: str, funding_event: str = "Series A") -> str:
    return template.format(
        company=company,
        name="Engineering Lead",
        funding_event=funding_event or "recent round",
    )


def build_pass_task(trace: dict, company: str, domain: str, seq: int) -> dict | None:
    out = trace["output"]
    pitch_segment = out.get("pitch_segment")
    tone_mode = out.get("tone_mode", "exploratory")

    if pitch_segment is None:
        return None  # abstain trace — skip for PASS tasks

    template_key = (pitch_segment, tone_mode)
    if template_key not in PASS_TEMPLATES:
        template_key = (pitch_segment, "exploratory")
    if template_key not in PASS_TEMPLATES:
        return None

    brief = build_brief_from_trace(trace, company, domain)
    email = render_email(PASS_TEMPLATES[template_key], company,
                         brief["funding"].get("event") or "recent round")

    return {
        "task_id": f"TB-TD-{seq:04d}",
        "category": "tone_guard",
        "difficulty": "medium",
        "authoring_mode": "trace_derived",
        "input": {
            "hiring_signal_brief": brief,
            "policy_decision": out,
        },
        "candidate_output": email,
        "ground_truth": {
            "verdict": "pass",
            "inferred_segment": pitch_segment,
            "failure_categories": [],
            "rationale": (
                f"Email correctly uses {tone_mode} tone for Seg{pitch_segment} "
                f"and references only assertable signals."
            ),
        },
        "metadata": {
            "source_trace_id": trace["decision_id"],
            "source_file": "outputs/policy_trace.jsonl",
            "generation_model": "deterministic_template",
            "judge_model": "scoring_evaluator_v2_frozen",
            "created_at": datetime.utcnow().isoformat(),
        },
    }


def build_fail_task(trace: dict, company: str, domain: str, seq: int) -> dict | None:
    out = trace["output"]
    pitch_segment = out.get("pitch_segment")

    if pitch_segment is None:
        pitch_segment = 1  # use Seg1 pitch for abstain traces (always wrong)
        wrong_seg = 1
    else:
        wrong_seg = WRONG_SEGMENT_MAP.get(pitch_segment, 1)

    if wrong_seg not in FAIL_D06_TEMPLATES:
        return None

    brief = build_brief_from_trace(trace, company, domain)
    email = render_email(FAIL_D06_TEMPLATES[wrong_seg], company)

    return {
        "task_id": f"TB-TD-{seq:04d}",
        "category": "tone_guard",
        "difficulty": "medium",
        "authoring_mode": "trace_derived",
        "input": {
            "hiring_signal_brief": brief,
            "policy_decision": out,
        },
        "candidate_output": email,
        "ground_truth": {
            "verdict": "fail",
            "inferred_segment": pitch_segment,
            "failure_categories": ["tone_guard", "icp_misclassification"],
            "rationale": (
                f"Email uses Seg{wrong_seg} framing for a Seg{pitch_segment} company "
                f"(D06 wrong-segment pitch). Also contains banned phrases."
            ),
        },
        "metadata": {
            "source_trace_id": trace["decision_id"],
            "source_file": "outputs/policy_trace.jsonl",
            "generation_model": "deterministic_template",
            "judge_model": "scoring_evaluator_v2_frozen",
            "created_at": datetime.utcnow().isoformat(),
        },
    }


def main():
    traces = []
    with open("outputs/policy_trace.jsonl") as f:
        for line in f:
            if line.strip():
                traces.append(json.loads(line))

    print(f"Loaded {len(traces)} policy_trace entries")

    # Shuffle companies for assignment
    companies = SYNTHETIC_COMPANIES.copy()
    random.shuffle(companies)

    tasks = []
    seq = 300  # start after existing TB-MG-0xxx range
    company_idx = 0

    for trace in traces:
        if company_idx >= len(companies):
            company_idx = 0  # cycle if needed

        company, domain, _ = companies[company_idx % len(companies)]
        company_idx += 1

        # PASS task
        pass_task = build_pass_task(trace, company, domain, seq)
        if pass_task:
            tasks.append(pass_task)
            seq += 1

        # FAIL task (D06)
        fail_task = build_fail_task(trace, company, domain, seq)
        if fail_task:
            tasks.append(fail_task)
            seq += 1

        if len(tasks) >= 64:  # target ~60, stop at 64
            break

    out_path = Path("eval/tenacious_bench/pilot_50/trace_derived_pool.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(json.dumps(t) for t in tasks))

    pass_count = sum(1 for t in tasks if t["ground_truth"]["verdict"] == "pass")
    fail_count = sum(1 for t in tasks if t["ground_truth"]["verdict"] == "fail")
    print(f"\nGenerated {len(tasks)} trace-derived tasks")
    print(f"  PASS: {pass_count}  FAIL: {fail_count}")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
