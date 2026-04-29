import os
import json
import torch
import gc
import re
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from eval.tenacious_bench.scoring_evaluator_v2_frozen import ScoringEvaluator

try:
    from unsloth import FastLanguageModel
    from transformers import AutoTokenizer
except ImportError:
    print("ERROR: Unsloth not installed. This script MUST run in Colab with GPU.")
    sys.exit(1)

HF_TOKEN = os.environ.get("HUGGING_FACE_HUB_TOKEN")
if not HF_TOKEN:
    raise ValueError("CRITICAL: HUGGING_FACE_HUB_TOKEN is not set.")

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
OUTPUT_DIR = "eval/tenacious_bench/judge_lora_v1"
evaluator_frozen = ScoringEvaluator()

def normalize_expected_verdict(task):
    verdict_str = task.get("verdict", task.get("ground_truth", {}).get("verdict", "PASS")).upper()
    if any(k in verdict_str for k in ["PASS", "POSITIVE", "APPROVE", "SUCCESS"]): return "PASS"
    return "FAIL"

def build_evaluator_payload(source, task):
    email_type = "warm" if source == "expert" and "reply" in task.get("signal_type", "") else "cold"
    td = {
        "candidate_output": task.get("candidate_output", task.get("body", "")),
        "ground_truth": {
            "inferred_segment": task.get("segment") if "segment" in task else task.get("input", {}).get("policy_decision", {}).get("pitch_segment")
        },
        "email_type": email_type
    }
    
    if "input" in task:
        bri = task["input"].get("hiring_signal_brief", {})
        td["ground_truth"]["stated_funding_stage"] = bri.get("funding") if isinstance(bri.get("funding"), str) else None
        
    if source == "expert" and "Series A" in td["candidate_output"]:
        td["ground_truth"]["stated_funding_stage"] = "Series A"
        
    return td

def build_inference_prompt(task_data, tokenizer):
    with open("eval/tenacious_bench/baseline_prompt_judge_v1.txt", "r") as f:
        template = f.read()
    
    if "input" in task_data:
        hiring_signal = json.dumps(task_data["input"].get("hiring_signal_brief", {}))
        policy = json.dumps(task_data["input"].get("policy_decision", {}))
        email = task_data.get("candidate_output", "")
    else:
        hiring_signal = json.dumps({"segment": task_data.get("segment"), "signal_type": task_data.get("signal_type")})
        policy = json.dumps({"pitch_segment": task_data.get("segment")})
        email = task_data.get("body", "")
    
    prompt = template.replace("{signal}", hiring_signal).replace("{policy}", policy).replace("{email}", email)
    prompt += "\n\nYou MUST respond in exactly this format:\nVERDICT: PASS or FAIL\nFAILURE_TYPE: NONE or <TYPE>"

    messages = [{"role": "user", "content": prompt}]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

def generate_and_parse(model, tokenizer, prompt_formatted):
    inputs = tokenizer([prompt_formatted], return_tensors="pt").to("cuda")
    with torch.inference_mode():
        outputs = model.generate(
            **inputs, 
            max_new_tokens=64, 
            temperature=0.0, 
            use_cache=True,
            pad_token_id=tokenizer.eos_token_id
        )
    raw_response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    
    verdict_match = re.search(r"VERDICT:\s*(PASS|FAIL)", raw_response, re.IGNORECASE)
    type_match = re.search(r"FAILURE_TYPE:\s*([A-Za-z_]+)", raw_response, re.IGNORECASE)
    
    v = verdict_match.group(1).upper() if verdict_match else "ERROR"
    ft = type_match.group(1).upper() if type_match else "UNKNOWN"
    
    return v, ft, raw_response

def verify_lora_active(model):
    print("\n[DEBUG] Verifying LoRA Adapter Layers...")
    lora_found = any('lora' in n.lower() for n, m in model.named_modules())
    if lora_found:
        print("[SUCCESS] Found 'lora' within model named_modules. Adapter is attached.")
    else:
        print("[CRITICAL ERROR] No 'lora' linear layers found! Adapter did NOT attach.")
        
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[DEBUG] Trainable Parameters: {trainable} (Must be 0)")
    if trainable != 0: print("[CRITICAL ERROR] Model is not locked for inference!")

def run_four_bad_harness(trained_model, trained_tokenizer, data, base_results, rule_results):
    print("\n=======================================================")
    print("MINIMAL VERIFICATION HARNESS (Primary Truth Check)")
    print("=======================================================")
    
    four_bad = ["SG-BAD-03", "SG-BAD-05", "SG-BAD-07", "SG-BAD-12"]
    tasks_to_test = [t for t in data if t[1].get("task_id") in four_bad]
    
    for source, task in tasks_to_test:
        tid = task.get("task_id")
        expected = normalize_expected_verdict(task)
        rule_v = rule_results[tid]
        base_v = base_results[tid]
        
        prompt = build_inference_prompt(task, trained_tokenizer)
        tv, tft, traw = generate_and_parse(trained_model, trained_tokenizer, prompt)
        
        print(f"\nTask ID     : {tid}")
        print(f"Expected    : {expected}")
        print(f"Rule verdict: {rule_v}")
        print(f"Base verdict: {base_v}")
        print(f"Trnd verdict: {tv} (Type: {tft})")
        print(f"Raw Output  :\n{traw}")
        print("-" * 55)

def run_ablation():
    data = []
    with open("eval/tenacious_bench/pilot_50/splits/held_out.jsonl", "r") as f:
        data.extend([("held_out", json.loads(l)) for l in f])
    with open("eval/tenacious_bench/style_guide_examples.jsonl", "r") as f:
        data.extend([("expert", json.loads(l)) for l in f])

    print("\n[1/3] Gathering BASE MODEL and RULE baseline predictions...")
    base_model, base_tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
        token=HF_TOKEN
    )
    FastLanguageModel.for_inference(base_model)
    
    base_results = {}
    rule_results = {}
    rule_types = {}
    
    for idx, (source, task) in enumerate(data):
        tid = task.get("task_id", f"TASK_{idx}")
        
        # Rule
        td = build_evaluator_payload(source, task)
        r_eval = evaluator_frozen.evaluate_task(td)
        rule_results[tid] = r_eval.verdict
        rule_types[tid] = r_eval.failure_type
        
        # Base
        prompt = build_inference_prompt(task, base_tokenizer)
        bv, _, _ = generate_and_parse(base_model, base_tokenizer, prompt)
        base_results[tid] = bv

    del base_model
    del base_tokenizer
    gc.collect()
    torch.cuda.empty_cache()

    print("\n[2/3] Loading TRAINED MODEL with adapter connection verification...")
    if not os.path.exists(OUTPUT_DIR):
        raise RuntimeError(f"LoRA adapter missing at {OUTPUT_DIR}. Cannot evaluate.")

    # Reload base model cleanly
    trained_model, trained_tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
        token=HF_TOKEN
    )
    # Reload matching tokenizer from adapter directory explicitly as requested
    trained_tokenizer = AutoTokenizer.from_pretrained(OUTPUT_DIR, token=HF_TOKEN)
    
    # EXPLICIT load_adapter
    trained_model.load_adapter(OUTPUT_DIR)
    FastLanguageModel.for_inference(trained_model)
    verify_lora_active(trained_model)
    
    # Run Harness Immediately
    run_four_bad_harness(trained_model, trained_tokenizer, data, base_results, rule_results)

    print("\n[3/3] Completing comprehensive TRAINED MODEL ablation run...")
    final_results = []
    
    for idx, (source, task) in enumerate(data):
        tid = task.get("task_id", f"TASK_{idx}")
        prompt = build_inference_prompt(task, trained_tokenizer)
        tv, tft, traw = generate_and_parse(trained_model, trained_tokenizer, prompt)
        
        final_results.append({
            "task_id": tid,
            "source": source,
            "expected_verdict": normalize_expected_verdict(task),
            "rule_verdict": rule_results[tid],
            "rule_failure_type": rule_types[tid],
            "base_verdict": base_results[tid],
            "trained_verdict": tv,
            "trained_failure_type": tft,
            "trained_rationale": traw
        })
        
    with open("eval/tenacious_bench/ablation_raw_results.json", "w") as f:
        json.dump(final_results, f, indent=2)
        
    print("\nComplete. Output saved to ablation_raw_results.json.")

if __name__ == "__main__":
    run_ablation()
