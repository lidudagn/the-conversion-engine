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
│   ├── tau2_harness.py      # τ²-Bench wrapper
│   ├── score_log.json       # Baseline results
│   ├── trace_log.jsonl      # Eval traces
│   └── baseline.md          # 400-word report
├── data/
│   ├── crunchbase/          # 1,001 company CSV
│   ├── layoffs/             # layoffs.fyi data
│   └── seed/                # Tenacious materials
├── outputs/
│   ├── policy_trace.jsonl   # Decision audit trail
│   └── bench_escalation_log.jsonl
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
