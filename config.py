"""
The Conversion Engine — Central Configuration
Kill-switch defaults to ON (all outbound → staff sink).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Kill Switch ───────────────────────────────────────────────────────────────
# When True (default): all emails/SMS route to staff sink
# When False: routes to real recipients (requires Tenacious CEO approval)
KILL_SWITCH = os.getenv("CONVERSION_ENGINE_LIVE", "false").lower() != "true"

# ─── LLM ───────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEV_MODEL = "qwen/qwen3-235b-a22b"       # Acts I-IV, budget target <$4
EVAL_MODEL = "anthropic/claude-sonnet-4"  # Act IV sealed eval, budget <$12

# ─── Email (Resend) ────────────────────────────────────────────────────────────
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "outreach@tenacious-challenge.test")

# ─── SMS (Africa's Talking) ───────────────────────────────────────────────────
AFRICASTALKING_API_KEY = os.getenv("AFRICASTALKING_API_KEY")
AFRICASTALKING_USERNAME = os.getenv("AFRICASTALKING_USERNAME", "sandbox")

# ─── CRM (HubSpot) ────────────────────────────────────────────────────────────
HUBSPOT_ACCESS_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN")

# ─── Observability (Langfuse) ─────────────────────────────────────────────────
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# ─── Calendar (Cal.com) ───────────────────────────────────────────────────────
CALCOM_API_KEY = os.getenv("CALCOM_API_KEY")
CALCOM_BASE_URL = os.getenv("CALCOM_BASE_URL", "http://localhost:3000")
CALCOM_EVENT_TYPE_ID = os.getenv("CALCOM_EVENT_TYPE_ID", "1")

# ─── Sink Addresses (used when kill-switch is active) ─────────────────────────
SINK_EMAIL = os.getenv("SINK_EMAIL", "sink@tenacious-challenge.test")
SINK_SMS = os.getenv("SINK_SMS", "+15550000000")
