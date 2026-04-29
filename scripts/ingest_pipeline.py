import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional
from pathlib import Path

JUDGE_PROMPT = """
You are a Senior Machine Learning Evaluation Specialist at Tenacious Consulting.
Your task is to audit a B2B Sales Evaluation Task for our benchmark "Tenacious-Bench".

TASK DATA:
{task_json}

EVALUATION CRITERIA (Score 1-5):
1. COHERENCE: Does the business scenario make sense? (e.g. no conflicting dates, logical hiring needs).
2. VERIFIABILITY: Is the Ground Truth Verdict (PASS/FAIL) objectively derivable from the input signals and the agent's style guide?
3. CLARITY: Is the rationale provided in the ground truth unambiguous and based on evidence?

TONE CHECK:
- Seg1: Early-stage growth / Scaling / Product delivery focus.
- Seg2: Restructuring / Cost-control / Efficiency focus.
- Seg3: Enterprise / Specialized expertise / Migration.
- Seg4: AI Maturity / Infra / R&D to Prod.

RESPONSE FORMAT (JSON ONLY):
{{
  "coherence": float,
  "verifiability": float,
  "clarity": float,
  "judge_rationale": "string"
}}
"""

class OpenRouterJudge:
    def __init__(self, model: str = "meta-llama/llama-3.1-70b-instruct"):
        self.model = model
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    async def judge_task(self, task_data: dict) -> dict:
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set. Production ingest requires a live judge.")

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": JUDGE_PROMPT.format(task_json=json.dumps(task_data, indent=2))}],
            "response_format": {"type": "json_object"}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers={"Authorization": f"Bearer {self.api_key}"}, json=payload) as resp:
                result = await resp.json()
                content = result['choices'][0]['message']['content']
                scores = json.loads(content)
                
        quality_score = (scores["coherence"] + scores["verifiability"] + scores["clarity"]) / 3
        return {
            "judge_scores": scores,
            "quality_score": round(quality_score, 2),
            "judge_model": self.model
        }

from eval.tenacious_bench.scoring_evaluator import ScoringEvaluator

class IngestPipeline:
    def __init__(self, evaluator, judge, max_concurrency: int = 5):
        self.evaluator = evaluator
        self.judge = judge
        self.results = []
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def process_file(self, input_path: str):
        tasks = []
        with open(input_path, "r") as f:
            for line in f:
                tasks.append(json.loads(line))
        
        # Batch process with semaphore
        await asyncio.gather(*(self.process_task_semaphore(task) for task in tasks))

    async def process_task_semaphore(self, task_data: dict):
        async with self.semaphore:
            await self.process_task(task_data)

    async def process_task(self, task_data: dict):
        task_id = task_data.get("task_id", "unknown")
        print(f"  [START] {task_id}")
        
        try:
            # 1. Run Heuristic Evaluator (Cheap Filter)
            heuristic_result = self.evaluator.evaluate_task(task_data)
            
            # 2. Run LLM Judge (Rigorous Filter)
            judge_result = await self.judge.judge_task(task_data)
            
            # 3. Enrich Task Data
            task_data["scoring"] = {**task_data.get("scoring", {}), **heuristic_result.dimensions}
            task_data["metadata"].update(judge_result)
            
            # 4. Final Quality Filter
            if judge_result["quality_score"] >= 4.0:
                print(f"  [PASS]  {task_id} - Score: {judge_result['quality_score']}")
                self.results.append(task_data)
                return True
            else:
                print(f"  [REJECT] {task_id} - Score: {judge_result['quality_score']}")
                return False
        except Exception as e:
            print(f"  [ERROR] {task_id}: {str(e)}")
            return False

    def save_pool(self, output_path: str):
        with open(output_path, "w") as f:
            for task in self.results:
                f.write(json.dumps(task) + "\n")

async def main():
    evaluator = ScoringEvaluator()
    judge = OpenRouterJudge()
    pipeline = IngestPipeline(evaluator, judge)
    
    pilot_dir = Path("eval/tenacious_bench/pilot_50")
    for pool_file in pilot_dir.glob("*_pool.jsonl"):
        print(f"Processing {pool_file}...")
        await pipeline.process_file(str(pool_file))
    
    pipeline.save_pool("eval/tenacious_bench/pilot_50/filtered_pool.jsonl")
    print(f"Ingest complete. Saved {len(pipeline.results)} high-quality tasks.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
