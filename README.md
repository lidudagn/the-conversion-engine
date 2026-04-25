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

## Key Design Decisions

1. **Policy Engine before LLM** — Deterministic rules control what the agent can say. The LLM follows policies, not intuition.
2. **Tone Guard after LLM** — Every draft is scored against the Tenacious style guide. Hard-fail on over-claiming.
3. **Signal Usage Contract** — The composer can only reference signals classified as assertable or question by the policy engine.
4. **Contradiction Detection** — Cross-signal contradictions make outreach feel like research findings, not pitches.
5. **Bench Gate Enforcement** — The agent never commits capacity the bench summary doesn't show. Escalates to human.
