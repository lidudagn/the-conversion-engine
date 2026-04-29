import json
import os
from pathlib import Path

class TraceExtractor:
    def __init__(self, trace_path: str):
        self.trace_path = trace_path
        self.tasks = []

    def extract(self):
        # Prefer the rich traces in held_out_traces.jsonl
        alt_path = Path("eval/held_out_traces.jsonl")
        target = alt_path if alt_path.exists() else Path(self.trace_path)
        
        if not target.exists():
            print(f"Warning: {target} not found.")
            return

        with open(target, "r") as f:
            for line in f:
                try:
                    raw = json.loads(line)
                except: continue
                
                # Derive B2B category from retail reward breakdown
                r_info = raw.get("reward_info", {})
                breakdown = r_info.get("reward_breakdown", {})
                
                failure_cats = []
                # Map DB failure to signal_grounding/integration
                if breakdown.get("DB", 1.0) < 0.5:
                    failure_cats.append("integration_failure")
                # Map NL failure to tone_guard
                if breakdown.get("NL_ASSERTION", 1.0) < 0.5:
                    failure_cats.append("tone_drift")
                
                score = r_info.get("reward")
                if score is None:
                    score = raw.get("reward", 0.0)
                if score is None:
                    score = 0.0
                
                # Synthesize a shadow B2B input
                task = {
                    "task_id": f"TB-TR-{raw.get('task_id', '000')}",
                    "category": "tone_guard" if "tone_drift" in failure_cats else "integration",
                    "difficulty": "medium",
                    "authoring_mode": "trace_derived",
                    "input": {
                        "hiring_signal_brief": {"prospect_name": f"RetailShadow_{raw.get('task_id')}"},
                        "policy_decision": {"pitch_segment": 1, "tone_mode": "suggestive"}
                    },
                    "candidate_output": "Shadow output for trace compliance analysis.",
                    "ground_truth": {
                        "verdict": "pass" if score > 0.8 else "fail",
                        "inferred_segment": 1,
                        "failure_categories": failure_cats,
                        "rationale": f"Transposed from τ²-Bench retail trace (score={score})."
                    },
                    "metadata": {
                        "source_trace_id": str(raw.get("task_id")),
                        "retail_reward": score,
                        "author": "TraceExtractor"
                    }
                }
                self.tasks.append(task)

    def save_tasks(self, output_dir: str):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        with open(Path(output_dir) / "mode_a_pool.jsonl", "w") as f:
            for task in self.tasks:
                f.write(json.dumps(task) + "\n")

if __name__ == "__main__":
    extractor = TraceExtractor("eval/trace_log.jsonl")
    extractor.extract()
    extractor.save_tasks("eval/tenacious_bench/pilot_50")
    print(f"Extracted {len(extractor.tasks)} trace-derived tasks.")
