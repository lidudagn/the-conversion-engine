import os
import torch
from unsloth import FastLanguageModel
import sys

HF_TOKEN = os.environ.get("HUGGING_FACE_HUB_TOKEN")
BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
OUTPUT_DIR = "eval/tenacious_bench/judge_lora_v1"

def test_lora_divergence():
    print("Testing LoRA Active Divergence...")
    prompt = """<|im_start|>system
You are a sales enablement evaluator.
<|im_end|>
<|im_start|>user
[EMAIL]
We are a leading AI company.
[/EMAIL]
VERDICT:
<|im_end|>
<|im_start|>assistant
"""
    
    # 1. Base Model Pass
    print("\n[1] Loading BASE MODEL...")
    base_model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=2048,
        load_in_4bit=True,
        token=HF_TOKEN
    )
    FastLanguageModel.for_inference(base_model)
    
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        base_logits = base_model(**inputs).logits

    # Free memory
    del base_model
    torch.cuda.empty_cache()

    # 2. Trained Model Pass
    print("\n[2] Loading TRAINED MODEL...")
    trained_model, _ = FastLanguageModel.from_pretrained(
        model_name=OUTPUT_DIR,
        max_seq_length=2048,
        load_in_4bit=True,
        token=HF_TOKEN
    )
    FastLanguageModel.for_inference(trained_model)
    
    with torch.no_grad():
        trained_logits = trained_model(**inputs).logits
        
    # Free
    del trained_model
    torch.cuda.empty_cache()

    # 3. Calculate Divergence (MSE of next-token logits)
    # We take the logits of the last token in the prompt (predicting the next token)
    base_last_token = base_logits[0, -1, :]
    trained_last_token = trained_logits[0, -1, :]
    
    mse_diff = torch.nn.functional.mse_loss(base_last_token, trained_last_token).item()
    max_diff = torch.max(torch.abs(base_last_token - trained_last_token)).item()
    
    print("\n[3] DIAGNOSTIC RESULTS")
    print(f"Mean Squared Error (MSE)        : {mse_diff:.6f}")
    print(f"Max Absolute Logit Diff         : {max_diff:.6f}")
    
    if mse_diff == 0.0:
        print(">>> CONCLUSION: ZERO DIVERGENCE. Adapter failed to load or weights are identical.")
    elif mse_diff < 0.01:
        print(">>> CONCLUSION: MINIMAL DIVERGENCE. Adapter loaded, but undertrained (underfit).")
    else:
        print(">>> CONCLUSION: ACTIVE DIVERGENCE. LoRA model proves mathematically distinct from Base.")

if __name__ == "__main__":
    test_lora_divergence()
