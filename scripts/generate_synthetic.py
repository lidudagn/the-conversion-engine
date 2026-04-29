import os
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Prompt for Seed Generation
GEN_PROMPT = """
You are a Senior B2B Sales Dataset Engineer. Generate 10 diverse B2B outreach scenarios for Tenacious Consulting.

EACH SCENARIO MUST INCLUDE:
1. A hiring_signal_brief (prospect_name, funding, layoffs, ai_maturity).
2. A policy_decision (pitch_segment 1-4, tone_mode).
3. A candidate_output (the email draft).
4. A ground_truth (verdict, inferred_segment, rationale).

The scenarios must target the 4 Tenacious segments:
- Seg1: Growth
- Seg2: Restructuring
- Seg3: Enterprise
- Seg4: AI Maturity

Make at least 3 of these scenarios "Adversarial" or "Hard" where the tone subtly mismatches the business condition (e.g., calling a layoff 'exciting transformation').

JSON OUTPUT ONLY (Array of objects):
"""

class SyntheticGenerator:
    def __init__(self, model: str = "openai/gpt-4o-mini"):
        self.model = model
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    async def generate_batch(self) -> List[dict]:
        if not self.api_key:
            return []

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": GEN_PROMPT}],
            "response_format": {"type": "json_object"}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers={"Authorization": f"Bearer {self.api_key}"}, json=payload) as resp:
                result = await resp.json()
                if 'choices' not in result:
                    print(f"ERROR: API Response Error for {self.model}: {result}")
                    return []
                content = result['choices'][0]['message']['content']
                # The response is a JSON object with an array, needs parsing
                try:
                    data = json.loads(content)
                    tasks = data.get("scenarios", data.get("tasks", []))
                except:
                    tasks = []
                
        # Post-process to fit schema
        for i, t in enumerate(tasks):
            t["task_id"] = f"TB-SY-PG{i:03d}"
            t["category"] = "tone_guard"
            t["authoring_mode"] = "llm_synthesis"
            t["difficulty"] = t.get("difficulty", "medium")
            t["metadata"] = {"author": f"SyntheticGenerator({self.model})", "created_at": datetime.now().isoformat()}
            
        return tasks

async def main():
    gen = SyntheticGenerator()
    all_tasks = []
    
    print("Starting Scale Synthesis (Batch Loop)...")
    for i in range(10):  # 10 batches of 10 tasks = 100 tasks
        print(f"Batch {i+1}/10...")
        tasks = await gen.generate_batch()
        all_tasks.extend(tasks)
        await asyncio.sleep(1) # Rate limit safety
    
    output_dir = Path("eval/tenacious_bench/pilot_50")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "mode_c_pool.jsonl", "w") as f:
        for task in all_tasks:
            f.write(json.dumps(task) + "\n")
    
    print(f"Total Generated {len(all_tasks)} synthetic tasks for Pilot 50.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
