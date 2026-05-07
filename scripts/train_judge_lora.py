"""
DPO LoRA training script — Tenacious-Bench preference-tuned judge.

Hardware & expected wall-clock time
------------------------------------
Google Colab free tier, T4 GPU (15.6 GB VRAM):  ~47 min for 3 epochs / 279 pairs
RunPod community RTX 4090 (~$0.34/hr):          ~18 min
RunPod A40 (~$0.39/hr):                         ~22 min

Precision: fp16 on T4 (no bfloat16 support); bf16 on L4/A40/4090.
Batch: per_device=2, grad_accum=8 → effective batch 16 on T4.
LoRA: r=16, α=32, 1.75% trainable params (8.8M / 502.8M).

Reproducibility
---------------
Backbone pinned to a specific HF commit via BASE_MODEL_REVISION.
All randomness seeded at seed=3407 (LoRA init + trainer).
Loss logged per step to training/loss_log.jsonl for offline analysis.
"""

import os
import json
import time
import torch
from pathlib import Path
from dataclasses import dataclass

from datasets import Dataset
from transformers import TrainerCallback, TrainerState, TrainerControl, TrainingArguments

try:
    from unsloth import FastLanguageModel, is_bfloat16_supported
    from trl import DPOTrainer, DPOConfig
except ImportError:
    print("ERROR: Unsloth or TRL not installed. Run in Colab with GPU.")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
HF_TOKEN = os.environ.get("HUGGING_FACE_HUB_TOKEN")
if not HF_TOKEN:
    raise ValueError("HUGGING_FACE_HUB_TOKEN not set. Required to load Qwen and push adapter.")

BASE_MODEL          = "Qwen/Qwen2.5-0.5B-Instruct"
# Pinned HF commit — verified 2026-05-01.
# Re-verify: git ls-remote https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct HEAD
BASE_MODEL_REVISION = "c90f8a5e40a75df38b88beb62efebaa5e5e2e4e4"

HUB_MODEL_ID  = "lidudagn/tenacious-judge-lora-v1"
TRAINING_DATA = "eval/tenacious_bench/training_data/pairs_v2.jsonl"
OUTPUT_DIR    = "eval/tenacious_bench/judge_lora_v1"
LOSS_LOG_PATH = Path("training/loss_log.jsonl")

# ---------------------------------------------------------------------------
# JSONL loss callback
# ---------------------------------------------------------------------------

class JsonlLossCallback(TrainerCallback):
    """
    Appends one JSON line per logging step to LOSS_LOG_PATH.

    Fields logged per step/epoch:
      epoch          – fractional epoch number
      step           – global optimiser step
      train/loss     – DPO total loss at this step
      train/rewards/chosen   – mean log-ratio for chosen responses
      train/rewards/rejected – mean log-ratio for rejected responses
      train/rewards/accuracies – fraction of pairs where chosen > rejected
      train/rewards/margins    – mean (chosen_reward − rejected_reward)
      train/logps/chosen       – mean log-prob of chosen under policy
      train/logps/rejected     – mean log-prob of rejected under policy
      train/learning_rate      – current LR from scheduler
      wall_time_s    – seconds elapsed since training started
    """

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._start = None

    def on_train_begin(self, args, state, control, **kwargs):
        self._start = time.time()
        # Truncate any previous run's log
        self.log_path.write_text("")

    def on_log(self, args, state: TrainerState, control: TrainerControl, logs=None, **kwargs):
        if logs is None:
            return
        record = {
            "epoch":                      round(state.epoch or 0, 4),
            "step":                       state.global_step,
            "train/loss":                 logs.get("loss"),
            "train/rewards/chosen":       logs.get("rewards/chosen"),
            "train/rewards/rejected":     logs.get("rewards/rejected"),
            "train/rewards/accuracies":   logs.get("rewards/accuracies"),
            "train/rewards/margins":      logs.get("rewards/margins"),
            "train/logps/chosen":         logs.get("logps/chosen"),
            "train/logps/rejected":       logs.get("logps/rejected"),
            "train/learning_rate":        logs.get("learning_rate"),
            "wall_time_s":                round(time.time() - self._start, 1) if self._start else None,
        }
        with self.log_path.open("a") as f:
            f.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# Data formatting
# ---------------------------------------------------------------------------

def format_dpo_data(data_path: str, tokenizer) -> Dataset:
    with open(data_path) as f:
        pairs = [json.loads(line) for line in f]

    formatted: dict[str, list] = {"prompt": [], "chosen": [], "rejected": []}
    for pair in pairs:
        messages = [{"role": "user", "content": pair["prompt"]}]
        prompt_formatted = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        formatted["prompt"].append(prompt_formatted)
        formatted["chosen"].append(pair.get("chosen_output", pair.get("chosen", "")).strip() + "\n")
        formatted["rejected"].append(pair.get("rejected_output", pair.get("rejected", "")).strip() + "\n")

    return Dataset.from_dict(formatted)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Loading {BASE_MODEL} @ revision {BASE_MODEL_REVISION} …")
    # 16-bit LoRA per Unsloth Qwen guide: load_in_4bit=False for DPO stability.
    # DPO needs a reference model copy in memory; 4-bit + ref OOMs on T4 at 0.5B.
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        revision=BASE_MODEL_REVISION,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=False,
        token=HF_TOKEN,
    )

    print("Applying LoRA adapters …")
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

    print("Formatting dataset …")
    dataset = format_dpo_data(TRAINING_DATA, tokenizer)
    print(f"Loaded {len(dataset)} preference pairs.")

    print(f"Loss log → {LOSS_LOG_PATH}")
    print("Starting DPO training …")

    trainer = DPOTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        callbacks=[JsonlLossCallback(LOSS_LOG_PATH)],
        args=DPOConfig(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=8,
            warmup_ratio=0.1,
            num_train_epochs=3,
            learning_rate=2e-5,
            fp16=not is_bfloat16_supported(),
            bf16=is_bfloat16_supported(),
            logging_steps=10,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=3407,
            output_dir=OUTPUT_DIR,
            remove_unused_columns=False,
            report_to="none",       # JSONL callback handles logging
        ),
        # Mechanical Gap Closure (Day 3): beta=0.1 is the DPO "Trust Budget."
        # Higher beta (1.0) increases the KL penalty, forcing the policy to stay close 
        # to the reference (higher stability, lower learning). Lower beta (0.1) provides 
        # a larger gradient budget to satisfy preference pairs. For Qwen-0.5B, 0.1 
        # prevents 'policy collapse' while remaining responsive to the segment alignment goal.
        beta=0.1,
    )

    train_result = trainer.train()
    print(f"\nTraining complete. Total steps: {train_result.global_step}")
    print(f"Loss log written to {LOSS_LOG_PATH} ({LOSS_LOG_PATH.stat().st_size} bytes)")

    print(f"Saving adapter to {OUTPUT_DIR} …")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print(f"Pushing adapter to HuggingFace Hub ({HUB_MODEL_ID}) …")
    try:
        model.push_to_hub(HUB_MODEL_ID, token=HF_TOKEN)
        tokenizer.push_to_hub(HUB_MODEL_ID, token=HF_TOKEN)
        print("Push successful.")
    except Exception as e:
        print(f"WARNING: Hub push failed: {e}. Adapter saved locally only.")


if __name__ == "__main__":
    main()
