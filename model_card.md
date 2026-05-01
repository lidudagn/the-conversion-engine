---
language:
- en
license: cc-by-4.0
base_model: Qwen/Qwen2.5-0.5B-Instruct
tags:
- dpo
- text-classification
- lora
- tenacious-bench
metrics:
- accuracy
---

# Tenacious-Bench Judge LoRA v1

A PEFT LoRA adapter for `Qwen/Qwen2.5-0.5B-Instruct`, designed to act as a
preference-tuned binary judge for Tenacious Consulting B2B outreach evaluation.
The judge classifies whether cold outreach emails correctly match the target
segment (Growth / Restructuring / Enterprise / AI-Maturity) and are grounded
in provided hiring signals.

**Training status: READY FOR COLAB EXECUTION**
The adapter has not yet been pushed to HuggingFace Hub because training requires
a GPU runtime (Colab T4 or RunPod A40). The training script and all prerequisite
data are fully prepared. See "Reproducing Training" below.

## Model Details

| Field | Value |
|---|---|
| Base model | Qwen/Qwen2.5-0.5B-Instruct |
| Training method | DPO (Rafailov et al., 2023), β=0.1 |
| Adapter type | LoRA (r=16, α=32) |
| Task | Binary PASS/FAIL + 4-level failure taxonomy |
| Training pairs | 279 preference pairs |
| Language | English |

## Intended Use

This judge runs in a rejection-sampling loop ahead of the Conversion Engine's
outbound email sender. If the judge returns FAIL, the email is either rewritten
or escalated for human review.

**Inputs:**
- Prospect hiring signal brief (JSON)
- Policy decision / target segment (JSON)
- Candidate email text

**Outputs:**
- `VERDICT`: PASS or FAIL
- `FAILURE_TYPE`: STYLE_VIOLATION | STRUCTURAL_VIOLATION | REASONING_FAILURE | SEMANTIC_FALSEHOOD
- `REASON`: One-sentence justification

## Training Data

Preference pairs from `eval/tenacious_bench/training_data/pairs_v2.jsonl`.
Built from the 102-task train partition of Tenacious-Bench v0.1.

| Property | Value |
|---|---|
| Total pairs | 279 (blatant 34%, subtle 34%, hard-negative 33%) |
| Generation model | openai/gpt-4o-mini |
| Judge filter model | meta-llama/llama-3.1-70b-instruct |
| Leakage prevention | Generation model ≠ judge model (Li et al., 2025) |
| N-gram contamination (n=8) | 0 violations vs held-out |
| Embedding contamination (cos > 0.85) | 0 violations vs held-out |

## Evaluation Results

### Available Now (no GPU required)

Rule-based scoring evaluator (deterministic judge, our primary artifact)
evaluated on the 50-task held-out partition. Results computed via
`scripts/run_real_ablation.py` with 10,000-iteration paired bootstrap.

See `eval/ablation_results.json` for full statistics.

| Condition | Accuracy | 95% CI |
|---|---|---|
| Rule-based evaluator (our judge) | see ablation_results.json | — |
| Prompt-only judge (zero-shot LLM, Delta B baseline) | see ablation_results.json | — |
| Week 10 τ²-Bench baseline | 72.67% | [65.0%, 79.2%] |

### Pending (requires GPU)

Delta A (LoRA-trained model vs baseline) will populate after Colab training run.
Scripts are complete and ready: `scripts/train_judge_lora.py` → `scripts/run_ablation.py`.

## Reproducing Training

```bash
# 1. In Google Colab T4 runtime:
!pip install unsloth trl peft datasets transformers accelerate

# 2. Set secrets:
import os
os.environ["HUGGING_FACE_HUB_TOKEN"] = "your_hf_token"
os.environ["OPENROUTER_API_KEY"] = "your_openrouter_key"

# 3. Verify prerequisites:
!python scripts/colab_preflight.py

# 4. Train (≈45 min on T4):
!python scripts/train_judge_lora.py

# 5. Ablate (≈30 min on T4):
!python scripts/run_ablation.py
```

The training script uses Unsloth's `FastLanguageModel` with DPO, pushing the
adapter to HuggingFace Hub on completion. Set `HUB_MODEL_ID` in
`scripts/train_judge_lora.py` to your HuggingFace username/repo.

## Failure Modes

- **Segment overfit**: Heavily tuned to Tenacious's four segments. Will misclassify
  valid emails from companies with different sales methodologies.
- **Language**: English only; not evaluated on multilingual outreach.
- **Single-turn bias**: Evaluates one email in isolation. Cannot reliably judge
  multi-turn tone drift beyond the first touchpoint.
- **Kill switch**: If judge accuracy on live production samples drops below 70%
  (measured monthly), revert to rule-based evaluator until retrained.

## Environmental Impact

| Property | Value |
|---|---|
| Hardware | Google Colab T4 (16 GB VRAM) |
| Estimated wall time | 45–90 minutes |
| Cloud provider | Google Cloud |
| Estimated CO₂ | < 0.05 kg CO₂eq (single T4 GPU, < 2 hr) |

## Citation

```bibtex
@misc{tenacious-judge-lora-v1,
  title={Tenacious-Bench Judge LoRA v1},
  author={lidudagn},
  year={2026},
  note={DPO-trained segment-alignment judge for B2B sales outreach evaluation}
}
```
