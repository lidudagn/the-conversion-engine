import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional
from pathlib import Path

import random
import re

# Reproducibility seed
random.seed(42)

# Load external judge prompt
try:
    JUDGE_PROMPT = (Path("eval/prompts/ingest_judge_prompt.md")).read_text()
except FileNotFoundError:
    print("Warning: eval/prompts/ingest_judge_prompt.md not found.")
    JUDGE_PROMPT = "{task_json}"

# ============================================================
# JUDGE FILTER THRESHOLDS (Ingest Pipeline)
# Documentation of concrete score thresholds per dimension.
# ============================================================
INGEST_THRESHOLDS = {
    "coherence": 4.0,     # Must solidly make sense without major logical leaps
    "verifiability": 4.0, # Ground truth must be clearly derivable
    "clarity": 4.0        # Rationale must be explicitly unambiguous
}

def _get_ngrams(text: str, n: int = 8) -> set:
    words = re.findall(r'\w+', text.lower())
    return {tuple(words[i:i+n]) for i in range(len(words) - n + 1)}

def dedup_pool(tasks: List[dict], n: int = 8) -> Tuple[List[dict], List[dict]]:
    """Pairwise n-gram deduplication to remove near-duplicate generations."""
    kept, dropped = [], []
    seen_ngrams = set()
    for task in tasks:
        output = task.get("candidate_output", "")
        ngrams = _get_ngrams(output, n)
        if ngrams and ngrams.isdisjoint(seen_ngrams):
            kept.append(task)
            seen_ngrams.update(ngrams)
        elif not ngrams:
            kept.append(task)
        else:
            dropped.append(task)
    return kept, dropped

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
        
        # Enforce dimension-specific explicit thresholds
        passes_thresholds = all(scores.get(dim, 0) >= threshold for dim, threshold in INGEST_THRESHOLDS.items())
        
        return {
            "judge_scores": scores,
            "quality_score": round(quality_score, 2),
            "passes_thresholds": passes_thresholds,
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
            
            # Explicit Multi-model Rotation Guard (Forbid Self-Judging)
            gen_model = task_data.get("metadata", {}).get("generation_model", "unknown").split("/")[0]
            if gen_model != "unknown" and gen_model == self.judge.model.split("/")[0]:
                print(f"  [REJECT] {task_id} - Model separation violation (self-judging): {gen_model}")
                return False
                
            # 4. Final Quality Filter (Must pass concrete per-dimension thresholds AND quality score)
            if judge_result["passes_thresholds"] and judge_result["quality_score"] >= 4.0:
                print(f"  [PASS]  {task_id} - Score: {judge_result['quality_score']}")
                self.results.append(task_data)
                return True
            else:
                print(f"  [REJECT] {task_id} - Score: {judge_result['quality_score']} (Failed per-dim thresholds: {not judge_result['passes_thresholds']})")
                return False
        except Exception as e:
            print(f"  [ERROR] {task_id}: {str(e)}")
            return False

    def save_pool(self, output_path: str):
        # Implement explicit pairwise dedup logic before final save
        kept, dropped = dedup_pool(self.results)
        print(f"\nDedup: Kept {len(kept)} tasks. Dropped {len(dropped)} near-duplicates.")
        
        with open(output_path, "w") as f:
            for task in kept:
                f.write(json.dumps(task) + "\n")
        self.results = kept

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
