import json
import asyncio
import os
from pathlib import Path
from openai import AsyncOpenAI
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = "openai/gpt-4o-mini"

PROMPT = """You are an expert sales enablement AI. You are generating training pairs for a binary classifier: "Aligned vs Misaligned" solely focused on the D06 metric (Semantic Segment Alignment).
DO NOT include standalone tone errors or overclaiming errors. EVERY rejected email MUST fail specifically on Segment Alignment (D06).

Given the prospect's hiring signal brief and the policy decision, generate 4 email variants AND a rationale for why they succeed or fail at semantic alignment:
1. `chosen`: A perfect email that aligns exactly with the target `pitch_segment`.
2. `rejected_blatant`: Blatant D06 error. Pitches a completely contrasting segment (e.g., using Growth tropes for a Restructuring policy).
3. `rejected_subtle`: Subtle D06 error. Mixes the correct segment with an adjacent segment incorrectly, or uses the correct segment's tools but the wrong segment's ultimate goal.
4. `rejected_hard`: MUST follow the HARD NEGATIVE CONTRACT:
   - Must use >=2 correct signals from the input brief.
   - Must physically use correct buzzwords/keywords typical for the target segment (to bypass lazy keyword evaluators).
   - MUST violate the intent framing (e.g., framing 'efficiency and cost control' as a 'massive high-velocity scaling opportunity', or framing 'enterprise security' as 'move-fast hacking').

Return the result STRICTLY as a JSON object matching this schema:
{{
    "chosen": {{"email": "text", "rationale": "Why this aligns perfectly"}},
    "rejected_blatant": {{"email": "text", "rationale": "Why this is obviously misaligned"}},
    "rejected_subtle": {{"email": "text", "rationale": "Why this is subtly misaligned"}},
    "rejected_hard": {{"email": "text", "rationale": "Why this is a hard negative (right keywords, wrong intent)"}}
}}

Segment Definitions:
- Seg1: Growth / Scaling (Fast, agile, expansion, series A/B)
- Seg2: Restructuring / Efficiency (Cost cutting, layoffs, consolidation, flat growth)
- Seg3: Enterprise / Legacy (Stable, migration, risk-averse, security)
- Seg4: AI Maturity (Focus on tech stack, advanced tools, data pipelines)

Context:
- Target Segment: {target_segment}
- Hiring Signal: {hiring_signal}
- Policy Decision: {policy_decision}
"""

async def generate_variants(task):
    signal = task.get('input', {}).get('hiring_signal_brief', {})
    policy = task.get('input', {}).get('policy_decision', {})
    
    if not signal and 'hiring_signal_brief' in task:
        signal = task['hiring_signal_brief']
    if not policy and 'policy_decision' in task:
        policy = task['policy_decision']
        
    if not signal or not policy:
        return []
        
    target_segment = policy.get('pitch_segment', 'Unknown')

    prompt = PROMPT.format(
        target_segment=target_segment,
        hiring_signal=json.dumps(signal),
        policy_decision=json.dumps(policy)
    )
    
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        data = json.loads(response.choices[0].message.content)
        
        # Standardized Prompt Contract
        standard_prompt = f"[System]\nYou are a strict judge of B2B outreach alignment.\n\n[Input]\n{json.dumps(signal)}\n{json.dumps(policy)}\n\n[Task]\nEvaluate the email for semantic segment alignment."
        
        pairs = []
        if 'chosen' in data and isinstance(data['chosen'], dict):
            chosen_email = data['chosen'].get('email', '')
            
            for key in ['rejected_blatant', 'rejected_subtle', 'rejected_hard']:
                if key in data and isinstance(data[key], dict):
                    pair_type = key.split('_')[1]
                    pairs.append({
                        "prompt": standard_prompt,
                        "chosen": chosen_email,
                        "rejected": data[key].get('email', ''),
                        "pair_type": pair_type,
                        "rationale": data[key].get('rationale', ''),
                        "task_id": task.get('task_id', 'unknown'),
                        "target_segment": target_segment
                    })
        return pairs
    except Exception as e:
        print(f"Error generating for {task.get('task_id')}: {e}")
        return []

async def main():
    with open("eval/tenacious_bench/pilot_50/splits/train.jsonl", "r") as f:
        tasks = [json.loads(line) for line in f]
        
    print(f"Loaded {len(tasks)} training tasks.")
    
    all_pairs = []
    
    batch_size = 5
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(tasks)+batch_size-1)//batch_size}...")
        results = await asyncio.gather(*[generate_variants(t) for t in batch])
        for res in results:
            all_pairs.extend(res)
        await asyncio.sleep(2)
        
    out_dir = Path("eval/tenacious_bench/training_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / "pairs.jsonl", "w") as f:
        for p in all_pairs:
            f.write(json.dumps(p) + "\n")
            
    print(f"\nSUCCESS: Generated {len(all_pairs)} strict semantic pairs.")
    
    # Analyze Dataset Balance
    types = Counter([p['pair_type'] for p in all_pairs])
    segments = Counter([p['target_segment'] for p in all_pairs])
    print("\nDataset Composition:")
    print(f"Pair Types: {dict(types)}")
    print(f"Segments: {dict(segments)}")

if __name__ == "__main__":
    asyncio.run(main())

