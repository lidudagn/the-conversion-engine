import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
from trl import SFTTrainer
from datasets import Dataset

# Dummy 5-task dataset
data = [
    {"instruction": "Critique this outreach", "input": "Hey, we are the best!", "output": "REJECT: Overclaiming and missing grounding."},
    {"instruction": "Critique this outreach", "input": "Request: Discussion on your Q3 AI roadmap.", "output": "ACCEPT: Direct and grounded."},
    {"instruction": "Critique this outreach", "input": "We can save you millions.", "output": "REJECT: Unauthorized pricing/savings claim."},
    {"instruction": "Critique this outreach", "input": "You mentioned hiring for Python roles.", "output": "ACCEPT: Grounded in signal."},
    {"instruction": "Critique this outreach", "input": "Your team is failing.", "output": "REJECT: Aggressive framing."}
]

dataset = Dataset.from_list(data)

model_id = "Qwen/Qwen2.5-0.5B" # Small model for dummy run

tokenizer = AutoTokenizer.from_pretrained(model_id)
tokenizer.pad_token = tokenizer.eos_token

# Load model in 4-bit for speed if possible, but here we just do a small CPU/GPU run
# Unsloth usually handles this, but for a dummy script we use pure transformers
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32)

training_args = TrainingArguments(
    output_dir="./dummy_model",
    max_steps=5,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=1,
    learning_rate=2e-4,
    fp16=torch.cuda.is_available(),
    logging_steps=1,
)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    dataset_text_field="output",
    max_seq_length=128,
    tokenizer=tokenizer,
    args=training_args,
)

print("Starting dummy training...")
trainer.train()
print("Training complete!")
