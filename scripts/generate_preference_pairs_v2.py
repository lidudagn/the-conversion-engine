#!/usr/bin/env python3
"""
generate_preference_pairs_v2.py — Expanded preference-pair generation for Path B (ORPO Judge Training).

Generates 300+ (prompt, chosen, rejected) preference pairs from the 102-task training partition.
Each training task produces up to 3 rejected variants (blatant, subtle, hard negative).

Model rotation policy (Li et al., 2025 preference leakage prevention):
  - Generation: openai/gpt-4o-mini (proprietary, instruction-tuned)
  - Judge/validation: meta-llama/llama-3.1-70b-instruct (open-weights, different architecture)

Output: eval/tenacious_bench/training_data/pairs_v2.jsonl
"""

import json
import asyncio
import os
import hashlib
import time
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import AsyncOpenAI
except ImportError:
    print("ERROR: openai not installed. Run: pip install openai")
    exit(1)

# --- Config ---
GENERATION_MODEL = "openai/gpt-4o-mini"
JUDGE_MODEL = "meta-llama/llama-3.1-70b-instruct"
TRAINING_DATA_PATH = "eval/tenacious_bench/pilot_50/splits/train.jsonl"
OUTPUT_PATH = "eval/tenacious_bench/training_data/pairs_v2.jsonl"
COST_LOG_PATH = "cost_log.json"
BATCH_SIZE = 5
BATCH_DELAY = 2.0  # seconds between batches

SEGMENT_DEFINITIONS = {
    1: "Growth / Scaling — Fast, agile, expansion, Series A/B funding, headcount growth, market capture",
    2: "Restructuring / Efficiency — Cost cutting, layoffs, consolidation, flat growth, doing more with less",
    3: "Enterprise / Legacy — Stable, migration-focused, risk-averse, security, compliance, outsourcing",
    4: "AI Maturity — LLM/ML focus, AI infrastructure, R&D to production, data pipelines, model deployment",
}

GENERATION_PROMPT = """You are an expert B2B sales enablement AI generating training data for a semantic alignment judge.

TASK: Given a prospect's hiring signal brief and policy decision, generate 4 email variants with rationales.

SEGMENT DEFINITIONS:
{segment_defs}

RULES:
- Each email MUST be 60-120 words (cold email format)
- Each email MUST end with a single clear CTA (question or calendar link)
- DO NOT use any banned phrases: "world-class", "rockstar", "ninja", "supercharge", "10x", "synergy", "leverage", "game-changer", "gold standard", "I hope this email finds you well"
- Each email MUST reference at least 1 specific signal from the input brief

VARIANTS TO GENERATE:
1. `chosen`: Perfect alignment with target segment {target_segment} ({segment_desc}). Uses correct framing, correct intent, correct tone for this segment.
2. `rejected_blatant`: WRONG segment entirely. If target is Seg{target_segment}, pitch as if Seg{wrong_seg_blatant}. Use that segment's value props and framing.
3. `rejected_subtle`: Mostly correct for Seg{target_segment} BUT with 1-2 sentences that leak adjacent-segment framing (Seg{wrong_seg_subtle}). The error should be in the intent framing, not in keywords.
4. `rejected_hard`: HARD NEGATIVE — Uses ≥2 correct signals from the brief AND correct Seg{target_segment} keywords, BUT frames the intent incorrectly. Example: using "efficiency" keywords for Seg2 but framing them as "scale your efficiency gains to capture more market" (Seg1 intent wrapped in Seg2 words).

PROSPECT CONTEXT:
- Company: {company_name}
- Target Segment: {target_segment} — {segment_desc}
- Hiring Signal Brief: {hiring_signal}
- Policy Decision: {policy_decision}

Return STRICTLY as JSON:
{{
    "chosen": {{"email": "<text>", "rationale": "<why this aligns perfectly>"}},
    "rejected_blatant": {{"email": "<text>", "rationale": "<why this is obviously misaligned>"}},
    "rejected_subtle": {{"email": "<text>", "rationale": "<why this is subtly misaligned>"}},
    "rejected_hard": {{"email": "<text>", "rationale": "<why this is a hard negative — right keywords, wrong intent>"}}
}}"""

JUDGE_PROMPT = """You are a strict B2B outreach quality judge. Evaluate whether this email correctly aligns with the target segment.

TARGET SEGMENT: {target_segment} — {segment_desc}
HIRING SIGNAL: {hiring_signal}

EMAIL TO EVALUATE:
{email}

Evaluate on these criteria:
1. Does the email frame the value proposition correctly for {segment_desc}?
2. Does the email reference at least 1 specific signal from the brief?
3. Is the email free of banned phrases and condescension?

Respond with ONLY:
VERDICT: PASS or FAIL
REASON: <one sentence>"""


client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


def get_wrong_segments(target: int) -> tuple:
    """Return (blatant_wrong, subtle_wrong) segments."""
    opposites = {1: (2, 3), 2: (1, 3), 3: (4, 1), 4: (2, 3)}
    return opposites.get(target, (2, 3))


async def generate_variants(task: dict) -> list:
    """Generate 3 preference pairs from a single training task."""
    inp = task.get("input", {})
    signal = inp.get("hiring_signal_brief", {})
    policy = inp.get("policy_decision", {})

    if not signal or not policy:
        return []

    target_segment = policy.get("pitch_segment")
    if target_segment is None or target_segment not in SEGMENT_DEFINITIONS:
        return []

    company_name = signal.get("company_name", signal.get("company", "ProspectCo"))
    wrong_blatant, wrong_subtle = get_wrong_segments(target_segment)
    segment_desc = SEGMENT_DEFINITIONS[target_segment]

    segment_defs_str = "\n".join(f"- Seg{k}: {v}" for k, v in SEGMENT_DEFINITIONS.items())

    prompt = GENERATION_PROMPT.format(
        segment_defs=segment_defs_str,
        target_segment=target_segment,
        segment_desc=segment_desc,
        wrong_seg_blatant=wrong_blatant,
        wrong_seg_subtle=wrong_subtle,
        company_name=company_name,
        hiring_signal=json.dumps(signal, indent=2),
        policy_decision=json.dumps(policy, indent=2),
    )

    try:
        response = await client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        data = json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"  [ERROR] Generation failed for {task.get('task_id')}: {e}")
        return []

    # Build the standardized judge prompt
    standard_prompt = (
        f"[System]\nYou are a strict Tenacious Consulting outreach alignment judge.\n"
        f"Evaluate the email below for semantic segment alignment with Segment {target_segment} ({segment_desc}).\n\n"
        f"[Prospect Context]\n"
        f"Company: {company_name}\n"
        f"Hiring Signal: {json.dumps(signal)}\n"
        f"Policy Decision: {json.dumps(policy)}\n\n"
        f"[Scoring Rubric]\n"
        f"1. segment_alignment: Does the email match Seg{target_segment} framing?\n"
        f"2. signal_grounding: Does the email reference ≥1 specific signal from the brief?\n"
        f"3. tone_compliance: Is the tone appropriate (no banned phrases, no condescension)?\n"
        f"4. honesty_constraint: Are all claims grounded (no fabricated signals)?\n"
        f"5. style_guide_match: Is the email 60-120 words with a single CTA?\n\n"
        f"[Email to Evaluate]\n"
    )

    pairs = []
    if "chosen" in data and isinstance(data["chosen"], dict):
        chosen_email = data["chosen"].get("email", "")
        if not chosen_email:
            return []

        for key in ["rejected_blatant", "rejected_subtle", "rejected_hard"]:
            if key not in data or not isinstance(data[key], dict):
                continue
            rejected_email = data[key].get("email", "")
            if not rejected_email:
                continue

            pair_type = key.replace("rejected_", "")
            pair = {
                "prompt": standard_prompt,
                "chosen": chosen_email,
                "rejected": rejected_email,
                "pair_type": pair_type,
                "rationale": data[key].get("rationale", ""),
                "chosen_rationale": data["chosen"].get("rationale", ""),
                "task_id": task.get("task_id", "unknown"),
                "target_segment": target_segment,
                "company_name": company_name,
                "generation_model": GENERATION_MODEL,
                "judge_model": JUDGE_MODEL,
                "content_hash": hashlib.md5(
                    (chosen_email + rejected_email).encode()
                ).hexdigest(),
            }
            pairs.append(pair)

    return pairs


async def judge_filter_pair(pair: dict) -> bool:
    """Use a DIFFERENT model family to validate the chosen output passes."""
    segment_desc = SEGMENT_DEFINITIONS.get(pair["target_segment"], "Unknown")
    prompt = JUDGE_PROMPT.format(
        target_segment=pair["target_segment"],
        segment_desc=segment_desc,
        hiring_signal=json.dumps({"task_id": pair["task_id"]}),
        email=pair["chosen"],
    )
    try:
        response = await client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=100,
        )
        result = response.choices[0].message.content.strip().upper()
        return "PASS" in result
    except Exception as e:
        print(f"  [WARN] Judge filter error for {pair['task_id']}: {e}")
        return True  # Keep on judge error to avoid data loss


async def main():
    """Main pipeline: load data → generate → filter → write."""
    start_time = time.time()

    # Load training tasks
    with open(TRAINING_DATA_PATH, "r") as f:
        tasks = [json.loads(line) for line in f]
    print(f"Loaded {len(tasks)} training tasks from {TRAINING_DATA_PATH}")

    # Generate preference pairs
    all_pairs = []
    for i in range(0, len(tasks), BATCH_SIZE):
        batch = tasks[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(tasks) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"Batch {batch_num}/{total_batches}...")

        results = await asyncio.gather(*[generate_variants(t) for t in batch])
        for res in results:
            all_pairs.extend(res)

        if i + BATCH_SIZE < len(tasks):
            await asyncio.sleep(BATCH_DELAY)

    print(f"\nGenerated {len(all_pairs)} raw pairs.")

    # Deduplicate by content hash
    seen_hashes = set()
    deduped_pairs = []
    for p in all_pairs:
        h = p["content_hash"]
        if h not in seen_hashes:
            seen_hashes.add(h)
            deduped_pairs.append(p)
    print(f"After dedup: {len(deduped_pairs)} pairs.")

    # Judge filter (cross-family validation)
    print("Running judge filter (cross-family validation)...")
    filtered_pairs = []
    for i in range(0, len(deduped_pairs), BATCH_SIZE):
        batch = deduped_pairs[i : i + BATCH_SIZE]
        results = await asyncio.gather(*[judge_filter_pair(p) for p in batch])
        for p, passed in zip(batch, results):
            if passed:
                filtered_pairs.append(p)
            else:
                print(f"  [FILTERED] {p['task_id']} pair_type={p['pair_type']} — chosen failed judge")
        if i + BATCH_SIZE < len(deduped_pairs):
            await asyncio.sleep(1.0)

    print(f"After judge filter: {len(filtered_pairs)} pairs.")

    # Write output
    out_path = Path(OUTPUT_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for p in filtered_pairs:
            f.write(json.dumps(p) + "\n")

    # Statistics
    elapsed = time.time() - start_time
    types = Counter(p["pair_type"] for p in filtered_pairs)
    segments = Counter(p["target_segment"] for p in filtered_pairs)

    print(f"\n{'=' * 60}")
    print(f"PREFERENCE PAIR GENERATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total pairs:         {len(filtered_pairs)}")
    print(f"Pair types:          {dict(types)}")
    print(f"Segment distribution:{dict(segments)}")
    print(f"Output:              {out_path}")
    print(f"Elapsed:             {elapsed:.1f}s")
    print(f"Generation model:    {GENERATION_MODEL}")
    print(f"Judge model:         {JUDGE_MODEL}")

    # Append to cost log
    cost_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "bucket": "dataset_authoring",
        "model": f"{GENERATION_MODEL} + {JUDGE_MODEL}",
        "purpose": "preference_pair_generation_v2",
        "pairs_generated": len(filtered_pairs),
        "cost_usd": round(len(filtered_pairs) * 0.002, 2),  # Estimated
    }
    try:
        with open(COST_LOG_PATH, "r") as f:
            cost_log = json.load(f)
        cost_log.append(cost_entry)
        with open(COST_LOG_PATH, "w") as f:
            json.dump(cost_log, f, indent=4)
        print(f"Cost logged: ~${cost_entry['cost_usd']:.2f}")
    except Exception:
        print(f"Warning: Could not update cost log.")


if __name__ == "__main__":
    asyncio.run(main())
