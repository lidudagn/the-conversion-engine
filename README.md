# The Conversion Engine

> Automated Lead Generation & Conversion System for Tenacious Consulting and Outsourcing

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    THE CONVERSION ENGINE                         │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │  Enrichment   │   │ ★ POLICY     │   │   LLM Agent  │        │
│  │  Pipeline     │──▶│   ENGINE     │──▶│   Core       │        │
│  │               │   │ (pre-LLM)    │   │              │        │
│  │ • Crunchbase  │   │ • Tone mode  │   │ • Composer   │        │
│  │ • Job Posts   │   │ • Gap gate   │   │ • Qualifier  │        │
│  │ • Layoffs.fyi │   │ • Abstain?   │   │ • Scheduler  │        │
│  │ • Leadership  │   │ • Signal     │   └──────┬───────┘        │
│  │ • AI Maturity │   │   classify   │          │                │
│  │ • Gap Brief   │   └──────────────┘   ┌──────▼───────┐        │
│  │ • Contradict. │                      │ ★ TONE GUARD │        │
│  └──────────────┘                       │  (post-LLM)  │        │
│                                         │ • Style check│        │
│                                         │ • Hard-fail  │        │
│                                         └──────┬───────┘        │
│                                         ┌──────▼───────┐        │
│                                         │  Outreach    │        │
│                                         │ • Email (1°) │        │
│                                         │ • SMS   (2°) │        │
│                                         │ • Voice (3°) │        │
│                                         └──────────────┘        │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │ HubSpot    │  │ Cal.com    │  │ Langfuse   │                │
│  │ CRM        │  │ Booking    │  │ Tracing    │                │
│  └────────────┘  └────────────┘  └────────────┘                │
│                                                                  │
│  ┌─────────────────────────────────────────────┐                │
│  │  τ²-Bench Evaluation Harness (30 dev tasks) │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
│  ★ = Decision-intelligence layers (top-1 differentiators)       │
│  Kill-switch ON by default → all outbound routes to staff sink  │
└─────────────────────────────────────────────────────────────────┘
```

## Setup

### Requirements
- Python 3.11+
- API keys (see `.env.example`)

### Installation
```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Fill in your API keys in .env
```

### Run the server
```bash
python agent/server.py
# → http://localhost:8000
# → http://localhost:8000/docs (Swagger)
```

### Run τ²-Bench baseline
```bash
python eval/tau2_harness.py --domain retail --trials 5
```

## Directory Structure
```
├── agent/
│   ├── enrichment/          # Signal enrichment pipeline
│   │   ├── pipeline.py      # Master orchestrator
│   │   ├── crunchbase.py    # Crunchbase ODM (CSV)
│   │   ├── job_posts.py     # Job velocity signal
│   │   ├── layoffs.py       # layoffs.fyi parser
│   │   ├── leadership.py    # CTO/VP Eng transitions
│   │   ├── ai_maturity.py   # AI readiness 0-3
│   │   └── competitor_gap.py # Top-quartile gap brief
│   ├── policy_engine.py     # ★ Pre-LLM decision rules
│   ├── contradiction_detector.py # ★ Cross-signal intelligence
│   ├── tone_guard.py        # ★ Post-LLM compliance
│   ├── icp_classifier.py    # 4-segment classifier
│   ├── composer.py          # Signal-grounded email writer
│   ├── qualifier.py         # Qualification + bench gate
│   ├── orchestrator.py      # Email→SMS→Voice handoff
│   ├── llm_client.py        # OpenRouter integration
│   ├── email_handler.py     # Resend (kill-switch)
│   ├── sms_handler.py       # Africa's Talking
│   ├── hubspot_client.py    # HubSpot CRM
│   ├── calendar_client.py   # Cal.com booking
│   ├── langfuse_wrapper.py  # Per-trace cost
│   └── server.py            # FastAPI backend
├── eval/
│   ├── tau2_harness.py      # τ²-Bench wrapper (Week 10 baseline)
│   ├── score_log.json       # Baseline results
│   ├── trace_log.jsonl      # Eval traces (Week 10)
│   ├── baseline.md          # 400-word report
│   └── tenacious_bench/     # ★ Week 11 benchmark
│       ├── schema.json          # 10-category task schema
│       ├── scoring_evaluator.py # 4-layer deterministic evaluator
│       ├── datasheet.md         # Gebru + Pushkarna documentation
│       ├── inter_rater_agreement.md
│       ├── style_guide_v2.md
│       ├── examples/            # 3 hand-built example tasks
│       └── pilot_50/
│           └── splits/          # train.jsonl / dev.jsonl / held_out.jsonl
├── scripts/                 # ★ Week 11 generation & contamination pipeline
│   ├── generate_programmatic.py  # Combinatorial tasks (seed=42)
│   ├── generate_synthetic.py     # LLM synthesis (GPT-4o-mini)
│   ├── generate_supplemental.py  # Underrepresented category fill
│   ├── hand_authored_adversarial.py
│   ├── extract_traces.py
│   ├── merge_and_partition.py    # Dedup + stratified split
│   ├── contamination_check.py    # N-gram + embedding + time-shift
│   └── test_evaluator.py         # Unit tests for scoring_evaluator
├── synthesis_memos/         # ★ Week 11 paper memos
│   ├── synthesis_memo_synthetic_data.md   # Liu et al. (COLM 2024)
│   └── synthesis_memo_datasheets.md       # Gebru/Pushkarna
├── memos/                   # ★ Week 11 paper memos (cont.)
│   ├── contamination_survey.md            # Chen et al. (EMNLP 2025)
│   └── llm_judge_survey.md                # Gu et al. (2024-2025)
├── data/
│   ├── crunchbase/          # 1,001 company CSV
│   ├── layoffs/             # layoffs.fyi data
│   └── seed/                # Tenacious materials
├── outputs/
│   ├── policy_trace.jsonl   # Decision audit trail
│   └── bench_escalation_log.jsonl
├── audit_memo.md            # ★ Week 11 Act I gap analysis
├── methodology.md           # ★ Week 11 Path B rationale + contamination log
├── config.py                # Kill-switch + API config
├── requirements.txt
└── .env.example
```

## Data Handling Policy

All data handling rules — scope, PII constraints, kill-switch requirements, rate limits, and incident reporting — are documented in [`data/policy/data_handling_policy.md`](data/policy/data_handling_policy.md). Read before enabling live mode or running against real prospects.

## Kill-Switch

**Default: ON (safe mode).** All outbound email/SMS routes to staff sink addresses.

```python
# config.py
KILL_SWITCH = os.getenv("CONVERSION_ENGINE_LIVE", "false").lower() != "true"
```

To verify kill-switch is active before any run:
```bash
bash smoke_test.sh   # exits 0 if kill-switch ON, exits 1 if live mode accidentally enabled
```

To enable live mode (requires Tenacious CEO approval):
```bash
CONVERSION_ENGINE_LIVE=true python agent/server.py
```

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Health check + kill-switch status |
| `/enrich` | POST | Run enrichment pipeline for a prospect |
| `/outreach` | POST | Full pipeline: enrich → policy → compose → tone guard → send |
| `/qualify` | POST | Process qualification reply |
| `/webhook/email` | POST | Resend reply webhook |
| `/webhook/sms` | POST | Africa's Talking inbound |

## HubSpot Integration — REST API vs MCP

The challenge spec references "HubSpot MCP for every conversation event." This system uses the **HubSpot REST API via `hubspot-api-client`** (the official Python SDK), which is functionally equivalent for all required operations:

- Contact creation and update (`/crm/v3/contacts`)
- Custom property sync (icp_segment, ai_maturity_score, enrichment_timestamp)
- Activity logging per conversation event

The HubSpot MCP server wraps the same REST API. Using the SDK directly gives identical data fidelity, eliminates the MCP server dependency, and keeps the stack simpler for the challenge week. Every conversation event still writes to HubSpot — the transport layer is REST rather than MCP protocol.

## Handoff Notes — Known Limitations & Suggested Next Steps

A prioritised list for the next engineer picking this up.

### Missing tests (highest priority)
- **No unit tests** for `policy_engine.py`, `tone_guard.py`, or `composer.py`. These are the highest-risk paths: a logic regression here silently sends wrong outreach.
- **No integration test** covering the full `enrich → policy → compose → tone_guard → send` pipeline end-to-end against a fixture company.
- **Probe library is manual** (`probes/probe_library.md`). Probes run by hand; there is no `pytest` suite that executes them automatically on CI.

### Scaling assumptions (break before 10k companies/day)
- `EnrichmentPipeline.load_data()` loads all 1,001 Crunchbase companies into memory. Fine at this scale; will need chunking or a database at 10k+.
- `competitor_gap.py` iterates up to 15 sector peers per prospect in-process. At high concurrency this multiplies API calls linearly — add a sector cache keyed on `(sector, date)`.
- `JobPostScraper` is backed by a frozen JSON dataset. Live scraping via Playwright is sequential (concurrency=1 enforced by robots.txt courtesy). Do not increase concurrency without per-domain rate limiting.

### Brittle integrations
- **OpenRouter model string** — `qwen/qwen3-next-80b-a3b-thinking` resolves to a versioned alias (`-2509` suffix). Model routing changes on OpenRouter without notice; pin to a versioned model ID and add a health-check in `config.py`.
- **Resend API** — email delivery uses `resend` SDK v1. The `Emails.send()` call signature changed in v2; pin `resend==1.*` in `requirements.txt`.
- **Africa's Talking SMS** — `send_sms()` has no delivery receipt polling. Failed sends (wrong number, country block) return HTTP 200 with a `status: Failed` body that the current handler does not check.
- **HubSpot property sync** — custom properties (`icp_segment`, `ai_maturity_score`) must be pre-created in HubSpot before first use. There is no auto-provisioning step; missing properties cause silent data loss.

### Suggested next steps (in order)
1. Add `pytest` tests for policy engine and tone guard — 30 min, highest risk reduction.
2. Wire probes into CI (`pytest probes/` via a lightweight harness) so regressions surface automatically.
3. Replace frozen Crunchbase CSV with a nightly S3 sync or Crunchbase Basic API call to keep funding dates fresh.
4. Add Africa's Talking delivery receipt webhook handler in `server.py` (`/webhook/sms/receipt`) and update HubSpot activity on failure.
5. Hand-label 20–30 Tenacious past prospects to calibrate `AIMaturityScorer` precision/recall before enabling live mode.

## Key Design Decisions

1. **Policy Engine before LLM** — Deterministic rules control what the agent can say. The LLM follows policies, not intuition.
2. **Tone Guard after LLM** — Every draft is scored against the Tenacious style guide. Hard-fail on over-claiming.
3. **Signal Usage Contract** — The composer can only reference signals classified as assertable or question by the policy engine.
4. **Contradiction Detection** — Cross-signal contradictions make outreach feel like research findings, not pitches.
5. **Bench Gate Enforcement** — The agent never commits capacity the bench summary doesn't show. Escalates to human.

---

## Week 11: Tenacious-Bench v0.1

### Status

| Deliverable | Status | Location |
|---|---|---|
| Audit Memo (600 words, 5 trace IDs, 8+ probe IDs) | ✅ Complete | [audit_memo.md](audit_memo.md) |
| Schema JSON (10 categories, 4 authoring modes) | ✅ Complete | [eval/tenacious_bench/schema.json](eval/tenacious_bench/schema.json) |
| Scoring Evaluator (4-layer, fatal gates, composite) | ✅ Complete | [eval/tenacious_bench/scoring_evaluator.py](eval/tenacious_bench/scoring_evaluator.py) |
| Dataset (198 tasks, 3 partitions) | ✅ Complete | [eval/tenacious_bench/pilot_50/splits/](eval/tenacious_bench/pilot_50/splits/) |
| Contamination Check (all 3 checks passing) | ✅ Pass | [contamination_check.json](eval/tenacious_bench/pilot_50/contamination_check.json) |
| Datasheet (Gebru + Pushkarna, CC-BY-4.0) | ✅ Complete | [eval/tenacious_bench/datasheet.md](eval/tenacious_bench/datasheet.md) |
| Inter-Rater Agreement (30 tasks, 2 raters, 24h re-label) | ✅ Complete | [eval/tenacious_bench/inter_rater_agreement.md](eval/tenacious_bench/inter_rater_agreement.md) |
| Synthesis Memos (4 common papers, 400-500 words each) | ✅ Complete | [synthesis_memos/](synthesis_memos/) + [memos/](memos/) |
| Methodology (Path B, trace IDs, paper citations) | ✅ Complete | [methodology.md](methodology.md) |
| Generation Scripts (reproducible, seeded) | ✅ Complete | [scripts/](scripts/) |
| Path B training data (preference pairs) | ✅ Complete | [eval/tenacious_bench/training_data/pairs.jsonl](eval/tenacious_bench/training_data/pairs.jsonl) |
| Training run (Acts III-V) | ⏳ Pending (Days 4-7) | — |
| HuggingFace publication | ⏳ Pending (Day 7) | — |

### The Semantic Alignment Gap
The Conversion Engine passed τ²-Bench (retail baseline, 72.67% pass@1) but failed internal audits (e.g., Probe D06: Wrong-Segment Pitch) due to the "Semantic Alignment Gap" — the inability of keyword filters to catch contextually tone-deaf B2B outreach. The **Tenacious-Bench** closes this by establishing a rigorous, machine-verifiable evaluation harness for preference-tuned judges.

### Key Resources
- **[Audit Memo](audit_memo.md)** — gap analysis of baseline failures, citing trace IDs 1, 11, 34, 66, 76, 92 and probes D06, H01-H10, I01-I03, E01-E05.
- **[Methodology](methodology.md)** — Path B justification (Rafailov et al. DPO + Kim et al. Prometheus 2), judge rotation policy, contamination remediation log.
- **[Datasheet](eval/tenacious_bench/datasheet.md)** — CC-BY-4.0, Gebru 7-section + Pushkarna telescopic/periscopic/microscopic layers.
- **[Synthesis Memos](synthesis_memos/)** + **[Common Memos](memos/)** — 4 papers (Liu et al., Gebru/Pushkarna, Chen et al., Gu et al.) each with specific disagreement and evidence.
- **[Failure Taxonomy](probes/failure_taxonomy.md)** — the 10 failure categories tested.
- **[Generation Scripts](scripts/)** — reproducible authoring code with model routes, judge prompts, dedup logic, and contamination check.

### Dataset Structure (`eval/tenacious_bench/pilot_50/splits/`)
- **Total Tasks: 198** (after contamination remediation: 5 near-duplicate train tasks removed, 3 held-out tasks replaced with clean dev tasks)
- `train.jsonl` — **98 tasks** (49.5%)
- `dev.jsonl` — **50 tasks** (25.3%)
- `held_out.jsonl` — **50 tasks** (25.3%, sealed test set)
- Contamination: ✅ All checks pass (n-gram PASS, embedding PASS, time-shift PASS)
- Schema: 10 failure categories × 4 authoring modes (Hand 40, Synth 96, Programmatic 65, Trace 2)

### Running the Evaluator
```bash
# Score example tasks (from repo root)
python eval/tenacious_bench/scoring_evaluator.py

# Run evaluator unit tests
python scripts/test_evaluator.py

# Run contamination check
python scripts/contamination_check.py

# Validate schema compliance (requires: pip install jsonschema)
python scripts/validate_schema.py
```

### What Is Next (Acts III–V)
1. **Day 4**: Read Path B papers (Rafailov DPO, Kim Prometheus 2, Li Preference Leakage). Format training data from `training_data/pairs.jsonl`.
2. **Day 5**: Training run — LoRA on Qwen 2.5 0.5B via Unsloth on Colab T4 (free). Log loss curves.
3. **Day 5-6**: Ablations — Delta A (trained vs baseline on held_out), Delta B (trained vs prompt-engineered on same backbone), cost-Pareto.
4. **Day 7**: Publish to HuggingFace, write blog post, community engagement (GitHub issue on τ²-Bench repo).
