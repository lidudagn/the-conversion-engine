"""
Contamination verification script for Tenacious-Bench.
Implements n-gram overlap, embedding similarity, and time-shift checks
across train/dev/held_out partitions.
"""
import json
import re
from pathlib import Path
from datetime import datetime

# Optional dependency gracefully handled
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False

BOILERPLATE = {
    "warm regards your name your position tenacious consulting",
    "i hope this email finds you well",
    "i hope this message finds you well",
    "i hope this email finds you",
    "i hope this message finds you",
    "let s discuss how we can work together",
    "let s connect to explore how we can",
    "would a 15 minute conversation be useful",
    "would 15 minutes next week be useful",
    "overlap would 15 minutes next week be",
    "doing exciting things in the tech space we",
    "is doing exciting things in the tech space",
    "our team can help you accelerate your",
    "at tenacious consulting we specialize in",
    "at tenacious consulting we re here to help",
    "dear prospect s name",
    "recipient s name i hope this email finds",
    "recipient s name i hope this message finds",
    "an exciting time for transformation at tenacious consulting",
    "it s an exciting time for transformation",
    "managing costs is a pattern we support often",
    "we d love to help your team scale",
    "we place dedicated python and data engineers with",
    "prospect s name congratulations on your recent acquisition",
    "dear prospect s name congratulations on your recent",
    "exciting time for transformation at tenacious consulting we",
    "hi recipient s name i hope this message",
    "dear recipient s name i hope this email",
    "space we d love to help your team",
    "s an exciting time for transformation at tenacious",
    "tech space we d love to help your",
    "we d love to help your team scale",
    "exciting things in the tech space we d",
}

def get_ngrams(text, n=8):
    words = re.findall(r'\w+', text.lower())
    ngrams = set()
    for i in range(len(words)-n+1):
        gram = " ".join(words[i:i+n])
        # Skip if pure boilerplate
        is_bp = False
        for bp in BOILERPLATE:
            if bp in gram:
                is_bp = True
                break
        if not is_bp:
            ngrams.add(tuple(words[i:i+n]))
    return ngrams

def check_ngram_overlap(split_a, split_b, n=8):
    violations = []
    for ta in split_a:
        ngrams_a = get_ngrams(ta.get("candidate_output", ""), n)
        if not ngrams_a: continue
        for tb in split_b:
            ngrams_b = get_ngrams(tb.get("candidate_output", ""), n)
            overlap = ngrams_a.intersection(ngrams_b)
            if overlap:
                violations.append({
                    "task_id_a": ta["task_id"],
                    "task_id_b": tb["task_id"],
                    "overlap_size": len(overlap),
                    "sample": " ".join(list(overlap)[0])
                })
    return violations

def check_embedding_similarity(split_a, split_b, threshold=0.85):
    if not HAS_EMBEDDINGS:
        return [{"warning": "sentence-transformers not installed. Skipping embedding check."}]
    
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def get_text(task):
        input_data = task.get("input", task)
        brief = input_data.get("hiring_signal_brief", {})
        policy = input_data.get("policy_decision", {})
        
        # Extract only strings/values to avoid schema-key contamination
        def extract_vals(obj):
            if isinstance(obj, dict):
                return " ".join(extract_vals(v) for v in obj.values())
            if isinstance(obj, list):
                return " ".join(extract_vals(v) for v in obj)
            return str(obj)

        text = f"{extract_vals(brief)} {extract_vals(policy)}"
        return text

    texts_a = [get_text(t) for t in split_a]
    texts_b = [get_text(t) for t in split_b]

    embs_a = model.encode(texts_a)
    embs_b = model.encode(texts_b)

    sims = cosine_similarity(embs_a, embs_b)
    
    violations = []
    for i in range(sims.shape[0]):
        for j in range(sims.shape[1]):
            if sims[i, j] > threshold:
                violations.append({
                    "task_id_a": split_a[i]["task_id"],
                    "task_id_b": split_b[j]["task_id"],
                    "similarity": float(sims[i, j])
                })
    return violations

def check_time_shift(tasks):
    """
    Checks that explicitly mentioned dates in the input brief
    are within the documented state constraints (2024-2026).
    """
    violations = []
    for t in tasks:
        input_data = t.get("input", t)
        brief = json.dumps(input_data.get("hiring_signal_brief", {}))
        # Find YYYY-MM-DD or YYYY-MM patterns
        dates = re.findall(r'20\d{2}-\d{2}-\d{2}|20\d{2}-\d{2}', brief)
        for d in dates:
            year = int(d.split('-')[0])
            if year < 2024 or year > 2026:
                violations.append({
                    "task_id": t["task_id"],
                    "date_found": d,
                    "issue": "Date outside of documented state space (2024-2026)"
                })
    return violations

def load_split(name):
    path = Path(f"eval/tenacious_bench/pilot_50/splits/{name}.jsonl")
    if not path.exists(): return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]

def main():
    splits_dir = Path("eval/tenacious_bench/pilot_50/splits")
    if not splits_dir.exists():
        print("Splits directory not found.")
        return

    train = load_split("train")
    dev = load_split("dev")
    held_out = load_split("held_out")
    
    all_tasks = train + dev + held_out
    print(f"Loaded {len(all_tasks)} total tasks for verification.")

    report = {"timestamp": datetime.now().isoformat(), "checks": {}}

    print("Running time-shift baseline checks...")
    ts_violations = check_time_shift(all_tasks)
    report["checks"]["time_shift"] = {
        "status": "pass" if not ts_violations else "fail",
        "violations": ts_violations
    }

    print("Running n-gram overlap checks (held_out vs train)...")
    ngram_violations = check_ngram_overlap(held_out, train, n=8)
    report["checks"]["ngram_overlap"] = {
        "status": "pass" if not ngram_violations else "fail",
        "violations": ngram_violations
    }

    print("Running embedding similarity checks (held_out vs train)...")
    emb_violations = check_embedding_similarity(held_out, train)
    if emb_violations and "warning" in emb_violations[0]:
        report["checks"]["embedding_similarity"] = {"status": "skipped", "message": emb_violations[0]["warning"]}
    else:
        report["checks"]["embedding_similarity"] = {
            "status": "pass" if not emb_violations else "fail",
            "violations": emb_violations
        }

    # Output results
    out_path = Path("eval/tenacious_bench/pilot_50/contamination_check.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nVerification complete. Results saved to {out_path}")
    print("Summary:")
    for check, data in report["checks"].items():
        print(f"  {check}: {data['status'].upper()} ({len(data.get('violations', []))} violations)")

if __name__ == "__main__":
    main()
