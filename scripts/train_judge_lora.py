import os
import json
import torch
from datasets import Dataset

try:
    from unsloth import FastLanguageModel, is_bfloat16_supported
    from trl import DPOTrainer, DPOConfig
except ImportError:
    print("ERROR: Unsloth or TRL not installed. This script MUST run in Colab with GPU.")
    exit(1)

# Strict HF Token Requirement
HF_TOKEN = os.environ.get("HUGGING_FACE_HUB_TOKEN")
if not HF_TOKEN:
    raise ValueError("CRITICAL: HUGGING_FACE_HUB_TOKEN is not set. Colab execution requires this to load Qwen and push adapter.")

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
# TODO: Update this to your huggingface username/org
HUB_MODEL_ID = "YOUR_HF_ORG/tenacious-judge-lora-v1" 
TRAINING_DATA = "eval/tenacious_bench/training_data/pairs.jsonl"
OUTPUT_DIR = "eval/tenacious_bench/judge_lora_v1"

def format_dpo_data(data_path, tokenizer):
    with open(data_path, "r") as f:
        pairs = [json.loads(line) for line in f]
    
    formatted_data = {"prompt": [], "chosen": [], "rejected": []}
    
    for pair in pairs:
        # Consistent Chat Template Application
        messages = [{"role": "user", "content": pair["prompt"]}]
        prompt_formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        chosen = pair.get("chosen_output", pair.get("chosen", "")).strip() + "\n"
        rejected = pair.get("rejected_output", pair.get("rejected", "")).strip() + "\n"
        
        formatted_data["prompt"].append(prompt_formatted)
        formatted_data["chosen"].append(chosen)
        formatted_data["rejected"].append(rejected)
        
    return Dataset.from_dict(formatted_data)

def main():
    print("Loading model and tokenizer from HF...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=2048,
        dtype=None, 
        load_in_4bit=True,
        token=HF_TOKEN # Verified load
    )
    
    print("Applying LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=32,
        lora_dropout=0, 
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )
    
    print("Formatting dataset...")
    dataset = format_dpo_data(TRAINING_DATA, tokenizer)
    print(f"Loaded {len(dataset)} preference pairs.")
    
    print("Initializing DPOTrainer...")
    trainer = DPOTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=DPOConfig(
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            warmup_ratio=0.1,
            num_train_epochs=3,
            learning_rate=2e-5,
            fp16=not is_bfloat16_supported(),
            bf16=is_bfloat16_supported(),
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=3407,
            output_dir=OUTPUT_DIR,
            remove_unused_columns=False,
            report_to="none"
        ),
        beta=0.1,
    )
    
    print("Starting DPO training...")
    trainer.train()
    
    print(f"Saving adapter to disk ({OUTPUT_DIR})...")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    print(f"Pushing adapter to HuggingFace Hub ({HUB_MODEL_ID})...")
    try:
        model.push_to_hub(HUB_MODEL_ID, token=HF_TOKEN)
        tokenizer.push_to_hub(HUB_MODEL_ID, token=HF_TOKEN)
        print("Push successful. Adapter is now persistent.")
    except Exception as e:
        print(f"WARNING: Failed to push to hub: {e}. Model is only saved locally.")

if __name__ == "__main__":
    main()
