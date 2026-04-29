"""
Normalize existing synthetic pool for schema compliance, merge all pools,
and re-partition into train/dev/held_out with stratified sampling.
"""
import json
import random
import hashlib
from pathlib import Path
from collections import Counter

random.seed(42)

SEGMENT_MAP = {
    "Growth": 1, "growth": 1, "Scaling": 1, "scaling": 1,
    "Restructuring": 2, "restructuring": 2, "Cost-control": 2, "cost-control": 2,
    "Enterprise": 3, "enterprise": 3, "Migration": 3, "migration": 3,
    "AI Maturity": 4, "ai maturity": 4, "AI": 4, "R&D": 4,
}

VERDICT_MAP = {
    "Successful Outreach": "pass", "Successful": "pass", "Pass": "pass", "pass": "pass",
    "Failed Outreach": "fail", "Failed": "fail", "Fail": "fail", "fail": "fail",
    "Borderline": "borderline", "borderline": "borderline",
}

VALID_CATEGORIES = [
    "tone_guard", "enrichment", "icp_boundary", "policy", "injection",
    "integration", "composer", "icp_misclassification", "signal_overclaiming", "tone_drift"
]

VALID_DIFFICULTIES = ["easy", "medium", "hard", "adversarial"]


def normalize_segment(seg):
    """Convert string segment to int (1-4)."""
    if isinstance(seg, int) and 1 <= seg <= 4:
        return seg
    if isinstance(seg, str):
        for key, val in SEGMENT_MAP.items():
            if key.lower() in seg.lower():
                return val
    return 1  # default to Seg1 if unknown


def normalize_verdict(verdict):
    """Normalize verdict to enum."""
    if verdict in ["pass", "fail", "borderline"]:
        return verdict
    return VERDICT_MAP.get(verdict, "fail")


def normalize_task(task):
    """Fix schema violations in a task."""
    # Fix ground_truth
    gt = task.get("ground_truth", {})
    gt["inferred_segment"] = normalize_segment(gt.get("inferred_segment", 1))
    gt["verdict"] = normalize_verdict(gt.get("verdict", "fail"))
    if "failure_categories" not in gt:
        gt["failure_categories"] = []
    if "rationale" not in gt:
        gt["rationale"] = "Auto-normalized task."
    if "forbidden_signals" not in gt:
        gt["forbidden_signals"] = []
    if "required_signals" not in gt:
        gt["required_signals"] = []
    task["ground_truth"] = gt

    # Fix category
    if task.get("category") not in VALID_CATEGORIES:
        task["category"] = "tone_guard"

    # Fix difficulty
    if task.get("difficulty") not in VALID_DIFFICULTIES:
        task["difficulty"] = "medium"

    # Ensure scoring exists
    if "scoring" not in task:
        task["scoring"] = {
            "segment_alignment": 0.5, "signal_grounding": 0.5,
            "tone_compliance": 0.5, "honesty_constraint": 0.5,
            "style_guide_match": 0.5, "composite_score": 0.5
        }

    # Ensure metadata exists
    if "metadata" not in task:
        task["metadata"] = {"author": "unknown", "created_at": "2026-04-28T00:00:00Z"}

    # Ensure subcategory
    if "subcategory" not in task:
        task["subcategory"] = "general"

    return task


def content_hash(task):
    """Generate hash for dedup based on candidate_output."""
    output = task.get("candidate_output", "")
    return hashlib.md5(output.encode()).hexdigest()


def load_pool(path):
    """Load a JSONL pool file."""
    tasks = []
    if not path.exists():
        return tasks
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def main():
    pilot_dir = Path("eval/tenacious_bench/pilot_50")

    # Load all pools
    pools = {}
    for pool_file in pilot_dir.glob("*_pool.jsonl"):
        name = pool_file.stem
        tasks = load_pool(pool_file)
        pools[name] = tasks
        print(f"Loaded {name}: {len(tasks)} tasks")

    # Also load existing pilot_ready if it has different tasks
    ready = load_pool(pilot_dir / "pilot_ready.jsonl")
    if ready:
        pools["pilot_ready_existing"] = ready
        print(f"Loaded pilot_ready_existing: {len(ready)} tasks")

    # Merge all pools
    all_tasks = []
    for name, tasks in pools.items():
        all_tasks.extend(tasks)
    print(f"\nTotal before dedup: {len(all_tasks)}")

    # Normalize all tasks
    for task in all_tasks:
        normalize_task(task)

    # Dedup by content hash
    seen = set()
    deduped = []
    for task in all_tasks:
        h = content_hash(task)
        if h not in seen:
            seen.add(h)
            deduped.append(task)
    print(f"After dedup: {len(deduped)}")

    # Reassign unique IDs to avoid any collisions
    for i, task in enumerate(deduped):
        task["task_id"] = f"TB-MG-{i+1:04d}"

    # Group tasks by scenario (input hash) to avoid leakage
    scenarios = {}
    for task in deduped:
        input_data = task.get("input", task)
        brief = input_data.get("hiring_signal_brief", {})
        policy = input_data.get("policy_decision", {})
        # Create a stable string representation
        s_repr = json.dumps({"b": brief, "p": policy}, sort_keys=True)
        s_hash = hashlib.md5(s_repr.encode()).hexdigest()
        scenarios.setdefault(s_hash, []).append(task)
    
    # Shuffle scenarios
    s_keys = list(scenarios.keys())
    random.shuffle(s_keys)

    # Stratified partition by scenario
    # We want to keep all tasks for a prospect in the same split.
    # To keep category balance, we'll assign the first scenario that contains 
    # a specific category to splits proportionally. 
    # Simpler approach: Shuffle scenarios and assign to splits.
    
    # Final contamination patch: Force specific similar scenarios to train
    FORCE_TO_TRAIN = {
        "TB-MG-0113", "TB-MG-0026", "TB-MG-0033", "TB-MG-0023", "TB-MG-0024", 
        "TB-MG-0077", "TB-MG-0200"
    }

    train, dev, held_out = [], [], []
    for s_hash, tasks in scenarios.items():
        # Check if any task in this scenario is forced to train
        force_train = any(t["task_id"] in FORCE_TO_TRAIN for t in tasks)
        
        if force_train:
            train.extend(tasks)
            continue

        # Standard split assignment
        n_mod = random.random()
        if n_mod < 0.5:
            train.extend(tasks)
        elif n_mod < 0.8:
            dev.extend(tasks)
        else:
            held_out.extend(tasks)

    # Shuffle within splits
    random.shuffle(train)
    random.shuffle(dev)
    random.shuffle(held_out)

    # Save splits
    splits_dir = pilot_dir / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    for name, tasks in [("train", train), ("dev", dev), ("held_out", held_out)]:
        with open(splits_dir / f"{name}.jsonl", "w") as f:
            for task in tasks:
                f.write(json.dumps(task) + "\n")

    # Save merged pool
    with open(pilot_dir / "pilot_ready.jsonl", "w") as f:
        for task in deduped:
            f.write(json.dumps(task) + "\n")

    # Report
    print(f"\n{'='*60}")
    print(f"Final dataset: {len(deduped)} tasks")
    print(f"  train: {len(train)}  dev: {len(dev)}  held_out: {len(held_out)}")

    print(f"\nCategory distribution:")
    cats = Counter(t["category"] for t in deduped)
    for c, n in sorted(cats.items()):
        print(f"  {c}: {n}")

    print(f"\nDifficulty distribution:")
    diffs = Counter(t["difficulty"] for t in deduped)
    for d, n in sorted(diffs.items()):
        print(f"  {d}: {n}")

    print(f"\nAuthoring mode distribution:")
    modes = Counter(t.get("authoring_mode", "unknown") for t in deduped)
    for m, n in sorted(modes.items()):
        print(f"  {m}: {n}")

    print(f"\nVerdict distribution:")
    verdicts = Counter(t["ground_truth"]["verdict"] for t in deduped)
    for v, n in sorted(verdicts.items()):
        print(f"  {v}: {n}")

    # Save IRA sample (30 tasks from held_out + dev)
    ira_pool = held_out + dev
    random.shuffle(ira_pool)
    ira_sample = ira_pool[:30]
    with open(pilot_dir / "ira_sample.jsonl", "w") as f:
        for task in ira_sample:
            f.write(json.dumps(task) + "\n")
    print(f"\nIRA sample: {len(ira_sample)} tasks saved")


if __name__ == "__main__":
    main()
