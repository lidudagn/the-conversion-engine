#!/usr/bin/env python3
"""
Colab pre-flight check for Tenacious Judge LoRA training.

Run this FIRST in Google Colab before train_judge_lora.py:
  !python scripts/colab_preflight.py

Verifies:
  - CUDA GPU is available with sufficient VRAM
  - Required packages are installed
  - Training data file exists with expected count
  - HF token is set
  - Contamination between training data and held-out is within spec
"""
import sys
import os
import json
from pathlib import Path

OK = "[OK]"
WARN = "[WARN]"
FAIL = "[FAIL]"
errors = 0

print("=" * 60)
print("Tenacious Judge LoRA — Colab Pre-flight Check")
print("=" * 60)

# 1. GPU / CUDA
try:
    import torch
    if torch.cuda.is_available():
        gpu = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"{OK}  GPU: {gpu} ({vram:.1f} GB)")
        if vram < 12:
            print(f"{WARN}  VRAM < 12 GB. DPO reference model may OOM. Use 4-bit or smaller backbone.")
    else:
        print(f"{FAIL}  No CUDA GPU detected. Training requires a T4 or better.")
        errors += 1
except ImportError:
    print(f"{FAIL}  torch not installed.")
    errors += 1

# 2. Required packages
for pkg in ["unsloth", "trl", "peft", "datasets", "transformers", "accelerate"]:
    try:
        __import__(pkg)
        print(f"{OK}  {pkg} installed")
    except ImportError:
        print(f"{FAIL}  {pkg} not installed. Run: pip install {pkg}")
        errors += 1

# 3. HF Token
hf_token = os.environ.get("HUGGING_FACE_HUB_TOKEN", "")
if hf_token:
    print(f"{OK}  HUGGING_FACE_HUB_TOKEN set ({hf_token[:8]}...)")
else:
    print(f"{FAIL}  HUGGING_FACE_HUB_TOKEN not set. Add to Colab secrets.")
    errors += 1

# 4. Training data
td_path = Path("eval/tenacious_bench/training_data/pairs_v2.jsonl")
if td_path.exists():
    with open(td_path) as f:
        count = sum(1 for l in f if l.strip())
    print(f"{OK}  Training data: {td_path} ({count} pairs)")
    if count < 100:
        print(f"{WARN}  Only {count} pairs — expected 279. Check generation scripts.")
else:
    print(f"{FAIL}  Training data not found at {td_path}")
    errors += 1

# 5. Contamination check result
cc_path = Path("eval/tenacious_bench/pilot_50/contamination_check.json")
if cc_path.exists():
    with open(cc_path) as f:
        cc = json.load(f)
    all_pass = all(v.get("status") == "pass" for v in cc.get("checks", {}).values())
    if all_pass:
        print(f"{OK}  Contamination check: all 3 checks pass")
    else:
        failed = [k for k, v in cc.get("checks", {}).items() if v.get("status") != "pass"]
        print(f"{WARN}  Contamination check: {failed} failed")
else:
    print(f"{WARN}  contamination_check.json not found — run scripts/contamination_check.py")

# 6. Held-out sealed
held_out_path = Path("eval/tenacious_bench/pilot_50/splits/held_out.jsonl")
if held_out_path.exists():
    with open(held_out_path) as f:
        ho_count = sum(1 for l in f if l.strip())
    print(f"{OK}  Held-out partition: {ho_count} tasks")
else:
    print(f"{FAIL}  Held-out partition not found")
    errors += 1

print("=" * 60)
if errors == 0:
    print("All checks passed. Ready for training.")
    print("Next step: python scripts/train_judge_lora.py")
else:
    print(f"{errors} check(s) failed. Fix above before training.")
    sys.exit(1)
