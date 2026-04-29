import os
import re
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

import random

# Reproducibility seed
random.seed(42)

# Load Prompts from standalone markdown files
PROMPTS_DIR = Path("eval/prompts")

try:
    JUDGE_PROMPT_TEMPLATE = (PROMPTS_DIR / "judge_filter_prompt.md").read_text()
except FileNotFoundError:
    print("Warning: eval/prompts/judge_filter_prompt.md not found.")
    JUDGE_PROMPT_TEMPLATE = "{task_json}"

try:
    GEN_PROMPT = (PROMPTS_DIR / "generator_prompt.md").read_text()
except FileNotFoundError:
    print("Warning: eval/prompts/generator_prompt.md not found.")
    GEN_PROMPT = ""

# ============================================================
# MULTI-LLM ROUTING POLICY
# ============================================================
# To prevent preference leakage, the generation model and the judge model
# MUST belong to disjoint architectural families.
ROUTING_POLICY = {
    "generators": ["openai/gpt-4o-mini", "anthropic/claude-3-haiku"],
    "judges": ["meta-llama/llama-3.1-70b-instruct", "mistralai/mixtral-8x7b-instruct"]
}

def validate_model_separation(gen_model: str, judge_model: str):
    def get_family(m):
        return m.split("/")[0]
    
    if get_family(gen_model) == get_family(judge_model):
        raise ValueError(f"Model Separation Violation: Generator ({gen_model}) and Judge ({judge_model}) must not share the same lineage!")
    
    # Enforce declared roles
    if not any(g in gen_model for g in ROUTING_POLICY["generators"]) and gen_model not in ROUTING_POLICY["generators"]:
        print(f"Warning: Generator model {gen_model} is not in standard ROUTING_POLICY")
    if not any(j in judge_model for j in ROUTING_POLICY["judges"]) and judge_model not in ROUTING_POLICY["judges"]:
        print(f"Warning: Judge model {judge_model} is not in standard ROUTING_POLICY")

# ============================================================
# JUDGE FILTER THRESHOLDS
# Applied by meta-llama/llama-3.1-70b-instruct after generation.
# Each dimension is scored 0.0–1.0 by the judge; tasks that fail
# any threshold are dropped before writing to the pool.
# ============================================================
JUDGE_FILTER_THRESHOLDS: Dict[str, float] = {
    "coherence": 0.70,
    "grounding": 0.60,
    "rubric_clarity": 0.80,
    "schema_validity": 1.00,
}

REQUIRED_SCHEMA_FIELDS = [
    ("input", "hiring_signal_brief"),
    ("input", "policy_decision"),
    ("candidate_output",),
    ("ground_truth", "verdict"),
    ("ground_truth", "inferred_segment"),
]


def _check_schema_validity(task: dict) -> float:
    for path in REQUIRED_SCHEMA_FIELDS:
        node = task
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return 0.0
            node = node[key]
    return 1.0


def _get_ngrams(text: str, n: int = 8) -> set:
    words = re.findall(r'\w+', text.lower())
    return {tuple(words[i:i+n]) for i in range(len(words) - n + 1)}


def dedup_pool(tasks: List[dict], n: int = 8) -> Tuple[List[dict], List[dict]]:
    """
    Pairwise n-gram deduplication within a generated pool.
    Two tasks are near-duplicates if they share any n-gram in candidate_output.
    The first occurrence is kept; subsequent matches are dropped.
    Returns (kept, dropped).
    """
    kept: List[dict] = []
    dropped: List[dict] = []
    seen_ngrams: set = set()

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


class JudgeFilter:
    """
    Calls meta-llama/llama-3.1-70b-instruct to score each task on
    JUDGE_FILTER_THRESHOLDS dimensions. Tasks failing any threshold are dropped.
    Family separation: generator=gpt-4o-mini, judge=llama-3.1-70b (per Li et al. 2025).
    """
    JUDGE_MODEL = "meta-llama/llama-3.1-70b-instruct"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    async def score_task(self, session: aiohttp.ClientSession, task: dict) -> Dict[str, float]:
        # Schema validity is deterministic — skip the LLM call if it already fails.
        schema_score = _check_schema_validity(task)
        if schema_score < JUDGE_FILTER_THRESHOLDS["schema_validity"]:
            return {"coherence": 0.0, "grounding": 0.0, "rubric_clarity": 0.0, "schema_validity": 0.0}

        prompt = JUDGE_PROMPT_TEMPLATE.format(task_json=json.dumps(task, indent=2))
        payload = {
            "model": self.JUDGE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        try:
            async with session.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            ) as resp:
                result = await resp.json()
                content = result["choices"][0]["message"]["content"]
                scores = json.loads(content)
                scores["schema_validity"] = schema_score
                return scores
        except Exception as e:
            print(f"  Judge error for {task.get('task_id', '?')}: {e}")
            return {"coherence": 0.0, "grounding": 0.0, "rubric_clarity": 0.0, "schema_validity": schema_score}

    def passes(self, scores: Dict[str, float]) -> bool:
        for dim, threshold in JUDGE_FILTER_THRESHOLDS.items():
            if scores.get(dim, 0.0) < threshold:
                return False
        return True

    async def filter_batch(self, tasks: List[dict]) -> Tuple[List[dict], List[dict]]:
        """Returns (passed, failed) lists after applying JUDGE_FILTER_THRESHOLDS."""
        passed, failed = [], []
        async with aiohttp.ClientSession() as session:
            for task in tasks:
                scores = await self.score_task(session, task)
                task["metadata"]["judge_scores"] = scores
                task["metadata"]["judge_model"] = self.JUDGE_MODEL
                if self.passes(scores):
                    passed.append(task)
                else:
                    failed.append(task)
                    failed_dims = [d for d, t in JUDGE_FILTER_THRESHOLDS.items() if scores.get(d, 0.0) < t]
                    print(f"  DROP {task.get('task_id', '?')} — failed: {failed_dims} scores={scores}")
        return passed, failed


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
                try:
                    data = json.loads(content)
                    tasks = data.get("scenarios", data.get("tasks", []))
                except Exception:
                    tasks = []

        for i, t in enumerate(tasks):
            t["task_id"] = f"TB-SY-PG{i:03d}"
            t["category"] = "tone_guard"
            t["authoring_mode"] = "llm_synthesis"
            t["difficulty"] = t.get("difficulty", "medium")
            t["metadata"] = {
                "author": f"SyntheticGenerator({self.model})",
                "generation_model": self.model,
                "created_at": datetime.now().isoformat(),
            }

        return tasks


async def main():
    api_key = os.getenv("OPENROUTER_API_KEY")
    gen_model = "openai/gpt-4o-mini"
    judge_model = "meta-llama/llama-3.1-70b-instruct"
    
    # Enforce routing policy before taking action
    validate_model_separation(gen_model, judge_model)
    
    gen = SyntheticGenerator(model=gen_model)
    judge = JudgeFilter(api_key) if api_key else None
    if judge:
        judge.JUDGE_MODEL = judge_model
        
    all_tasks: List[dict] = []

    print(f"Starting Scale Synthesis (Batch Loop) with Generator: {gen_model}...")
    for i in range(10):  # 10 batches of 10 tasks = 100 tasks
        print(f"Batch {i+1}/10...")
        tasks = await gen.generate_batch()
        all_tasks.extend(tasks)
        await asyncio.sleep(1)

    print(f"\nGenerated {len(all_tasks)} raw tasks.")

    # Step 1: Judge filter — drop tasks below per-dimension thresholds.
    if judge and api_key:
        print(f"\nRunning judge filter ({JudgeFilter.JUDGE_MODEL})...")
        print(f"Thresholds: {JUDGE_FILTER_THRESHOLDS}")
        all_tasks, dropped_by_judge = await judge.filter_batch(all_tasks)
        print(f"Judge filter: {len(all_tasks)} passed, {len(dropped_by_judge)} dropped.")
    else:
        print("WARNING: OPENROUTER_API_KEY not set — judge filter skipped.")
        dropped_by_judge = []

    # Step 2: Pairwise n-gram deduplication within the generated pool.
    print("\nRunning pairwise n-gram deduplication (n=8)...")
    all_tasks, dropped_by_dedup = dedup_pool(all_tasks, n=8)
    print(f"Dedup: {len(all_tasks)} kept, {len(dropped_by_dedup)} near-duplicates removed.")

    output_dir = Path("eval/tenacious_bench/pilot_50")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "mode_c_pool.jsonl", "w") as f:
        for task in all_tasks:
            f.write(json.dumps(task) + "\n")

    print(f"\nFinal pool: {len(all_tasks)} tasks written to mode_c_pool.jsonl")
    print(f"Total dropped: {len(dropped_by_judge)} (judge) + {len(dropped_by_dedup)} (dedup)")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
