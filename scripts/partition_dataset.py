import json
import random
from pathlib import Path

def main():
    input_path = "eval/tenacious_bench/pilot_50/pilot_ready.jsonl"
    tasks = []
    with open(input_path, "r") as f:
        for line in f:
            tasks.append(json.loads(line))
            
    # Priority weighting for Held-out: Hand-authored and Synthetic
    # Randomly shuffle first
    random.seed(42)
    random.shuffle(tasks)
    
    # Sort by authoring mode priority: hand_authored > llm_synthesis > programmatic > trace_derived
    priority = {
        "hand_authored": 0,
        "llm_synthesis": 1,
        "programmatic": 2,
        "trace_derived": 3
    }
    tasks.sort(key=lambda x: priority.get(x.get("authoring_mode", "trace_derived"), 3))
    
    total = len(tasks)
    held_out_count = int(total * 0.20)
    dev_count = int(total * 0.30)
    train_count = total - held_out_count - dev_count
    
    held_out = tasks[:held_out_count]
    dev = tasks[held_out_count:held_out_count + dev_count]
    train = tasks[held_out_count + dev_count:]
    
    output_dir = Path("eval/tenacious_bench/pilot_50/splits")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for name, split in [("train", train), ("dev", dev), ("held_out", held_out)]:
        with open(output_dir / f"{name}.jsonl", "w") as f:
            for t in split:
                f.write(json.dumps(t) + "\n")
        print(f"Saved {len(split)} tasks to {name}.jsonl")

if __name__ == "__main__":
    main()
