import os
import re
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

# ============================================================
# JUDGE FILTER THRESHOLDS
# Applied by meta-llama/llama-3.1-70b-instruct after generation.
# Each dimension is scored 0.0–1.0 by the judge; tasks that fail
# any threshold are dropped before writing to the pool.
# ============================================================
JUDGE_FILTER_THRESHOLDS: Dict[str, float] = {
    # The scenario is internally consistent: signals match the
    # declared segment, and the output logically follows from the input.
    "coherence": 0.70,

    # Claims in candidate_output are anchored in hiring_signal_brief
    # fields (funding amount, layoff count, role titles, etc.).
    # Fabricated or unsupported claims score below this threshold.
    "grounding": 0.60,

    # The ground_truth failure category is unambiguous: a human
    # reading only the task should reach the same verdict with high
    # confidence. Borderline or dual-failure cases score below this.
    "rubric_clarity": 0.80,

    # Task has all required schema fields:
    # input.hiring_signal_brief, input.policy_decision,
    # candidate_output, ground_truth.verdict, ground_truth.inferred_segment.
    # This is a binary check: 1.0 = all present, 0.0 = any missing.
    "schema_validity": 1.00,
}

JUDGE_PROMPT_TEMPLATE = """
You are a strict quality-control judge for a B2B sales evaluation dataset.

Score the following task on four dimensions, each 0.0–1.0:

1. coherence       — signals match declared segment; output logically follows input
2. grounding       — output claims are anchored in provided hiring_signal_brief fields
3. rubric_clarity  — failure category is unambiguous; no dual-failure ambiguity
4. schema_validity — all required fields present (1.0) or at least one missing (0.0)

Respond with JSON only:
{{"coherence": <float>, "grounding": <float>, "rubric_clarity": <float>, "schema_validity": <float>}}

TASK:
{task_json}
"""

REQUIRED_SCHEMA_FIELDS = [
    ("input", "hiring_signal_brief"),
    ("input", "policy_decision"),
    ("candidate_output",),
    ("ground_truth", "verdict"),
    ("ground_truth", "inferred_segment"),
]

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
    gen = SyntheticGenerator()
    judge = JudgeFilter(api_key) if api_key else None
    all_tasks: List[dict] = []

    print("Starting Scale Synthesis (Batch Loop)...")
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
