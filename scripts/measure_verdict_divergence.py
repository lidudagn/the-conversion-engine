import json
import os

def measure_verdict_divergence():
    file_path = "eval/tenacious_bench/ablation_raw_results.json"
    if not os.path.exists(file_path):
        print(f"ERROR: {file_path} not found. You must run run_ablation.py first.")
        return

    with open(file_path, "r") as f:
        results = json.load(f)

    if not results:
        print("ERROR: Empty results file.")
        return

    total = len(results)
    identical = 0
    flipped = 0
    
    # Confusion Matrix: Base -> Trained
    cm = {"PASS": {"PASS": 0, "FAIL": 0}, "FAIL": {"PASS": 0, "FAIL": 0}}
    
    for r in results:
        b_raw = r.get("base_verdict", "ERROR").upper()
        t_raw = r.get("trained_verdict", "ERROR").upper()
        
        # Clean weird outputs
        b = "PASS" if "PASS" in b_raw else ("FAIL" if "FAIL" in b_raw else "FAIL")
        t = "PASS" if "PASS" in t_raw else ("FAIL" if "FAIL" in t_raw else "FAIL")
        
        cm[b][t] += 1
        if b == t:
            identical += 1
        else:
            flipped += 1
            
    pct_identical = (identical / total) * 100 if total > 0 else 0
    pct_flipped = (flipped / total) * 100 if total > 0 else 0
    
    print("\n=======================================================")
    print("VERDICT DIVERGENCE ANALYSIS (Base vs LoRA)")
    print("=======================================================")
    print(f"Total Tasks        : {total}")
    print(f"Identical Verdicts : {identical} ({pct_identical:.1f}%)")
    print(f"Flipped Verdicts   : {flipped} ({pct_flipped:.1f}%)\n")
    
    print("--- Confusion Matrix (Base -> Trained) ---")
    d1, d2 = cm['PASS']['PASS'], cm['PASS']['FAIL']
    d3, d4 = cm['FAIL']['PASS'], cm['FAIL']['FAIL']
    print("                    | Trained: PASS | Trained: FAIL |")
    print(f"Base: PASS ({d1+d2:>2})   | {d1:>13} | {d2:>13} |")
    print(f"Base: FAIL ({d3+d4:>2})   | {d3:>13} | {d4:>13} |")

    print("\n--- Diagnostic Conclusion ---")
    if pct_flipped >= 10.0:
        print(">>> PASS: LoRA actively shifted the decision boundary on >10% of tasks.")
        print(f"          (Flipped {pct_flipped:.1f}% of labels)")
    elif pct_flipped > 0.0:
        print(">>> WARNING: LoRA shifted boundaries, but below the 10% threshold.")
        print(f"             (Flipped only {pct_flipped:.1f}% of labels -> Possible underfitting)")
    else:
        print(">>> CRITICAL FAILURE: 0% divergence. LoRA outputs match Base perfectly.")
        print("                      The adapter is bypassed or completely collapsed.")
        
if __name__ == "__main__":
    measure_verdict_divergence()
