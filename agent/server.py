"""
FastAPI Backend — Full Production Stack
Ties all modules together: enrichment, policy, composition, tone, outreach, CRM, calendar.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

import config
from agent.enrichment.pipeline import EnrichmentPipeline
from agent.policy_engine import PolicyEngine
from agent.tone_guard import ToneGuard
from agent.composer import EmailComposer
from agent.qualifier import QualificationHandler, QualificationState
from agent.email_handler import EmailHandler
from agent.sms_handler import SMSHandler
from agent.hubspot_client import HubSpotClient
from agent.calendar_client import CalComClient
from agent.orchestrator import ChannelOrchestrator
from agent.langfuse_wrapper import log_outreach_trace, log_enrichment_trace
from agent.llm_client import get_llm_client

app = FastAPI(
    title="The Conversion Engine",
    description="Automated Lead Generation & Conversion System for Tenacious",
    version="1.0.0",
)

# ─── Load Seed Data ──────────────────────────────────────────────────────────
_seed_dir = Path(__file__).parent.parent / "data" / "seed"

def _load_seed_text(filename: str) -> str:
    path = _seed_dir / filename
    return path.read_text() if path.exists() else ""

def _load_seed_json(filename: str) -> dict:
    path = _seed_dir / filename
    if path.exists():
        return json.loads(path.read_text())
    return {}

_style_guide = _load_seed_text("style_guide.md")
_bench_summary = _load_seed_json("bench_summary.json")

# Build bench summary for qualifier from real data
_bench_for_qualifier = {
    "available_stacks": list(_bench_summary.get("stacks", {}).keys()),
    "total_available": _bench_summary.get("total_engineers_on_bench", 36),
    "by_stack": {k: v.get("available_engineers", 0) for k, v in _bench_summary.get("stacks", {}).items()},
}

# ─── Initialize Components ──────────────────────────────────────────────────
pipeline = EnrichmentPipeline()
policy_engine = PolicyEngine()
tone_guard = ToneGuard(style_guide=_style_guide, llm_client=get_llm_client())
composer = EmailComposer(llm_client=get_llm_client(), style_guide=_style_guide)
qualifier = QualificationHandler(bench_summary=_bench_for_qualifier)
email_handler = EmailHandler()
sms_handler = SMSHandler()
hubspot = HubSpotClient()
hubspot.ensure_custom_properties()
calcom = CalComClient()
orchestrator = ChannelOrchestrator()

# Track latencies for p50/p95
_latencies: list[float] = []


# ─── Request Models ─────────────────────────────────────────────────────────
class EnrichRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None


class OutreachRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    prospect_email: Optional[str] = None
    prospect_name: Optional[str] = None
    sender_name: str = "Tenacious Team"


class QualifyRequest(BaseModel):
    prospect_name: str
    prospect_email: str = ""
    thread_id: str = ""
    reply_text: str


class BookRequest(BaseModel):
    prospect_name: str
    prospect_email: str
    company_name: str
    timezone: str = "UTC"
    notes: str = ""


# ─── Endpoints ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "kill_switch": config.KILL_SWITCH,
        "model": config.DEV_MODEL,
        "timestamp": datetime.now().isoformat(),
        "integrations": {
            "resend": bool(config.RESEND_API_KEY),
            "africastalking": bool(config.AFRICASTALKING_API_KEY),
            "hubspot": bool(config.HUBSPOT_ACCESS_TOKEN
                           and not config.HUBSPOT_ACCESS_TOKEN.startswith("pat-...")),
            "calcom": bool(config.CALCOM_API_KEY
                           and not config.CALCOM_API_KEY.startswith("cal_...")),
            "langfuse": bool(config.LANGFUSE_PUBLIC_KEY
                             and not config.LANGFUSE_PUBLIC_KEY.startswith("pk-lf-...")),
            "openrouter": bool(config.OPENROUTER_API_KEY),
        },
    }


@app.get("/metrics")
async def metrics():
    import numpy as np
    lat = _latencies if _latencies else [0]
    return {
        "total_interactions": len(_latencies),
        "p50_latency_ms": round(float(np.percentile(lat, 50)), 1) if _latencies else 0,
        "p95_latency_ms": round(float(np.percentile(lat, 95)), 1) if _latencies else 0,
        "kill_switch_active": config.KILL_SWITCH,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/enrich")
async def enrich_prospect(req: EnrichRequest):
    """Run full enrichment pipeline for a prospect."""
    start = time.time()
    try:
        brief, gap_brief, contradictions = pipeline.enrich_prospect(
            company_name=req.company_name,
            domain=req.domain,
        )
        latency_ms = int((time.time() - start) * 1000)
        _latencies.append(latency_ms)

        log_enrichment_trace(req.company_name, brief.model_dump(), latency_ms)

        return {
            "status": "success",
            "brief": brief.model_dump(),
            "gap_brief": gap_brief.model_dump() if gap_brief else None,
            "contradictions": [c.model_dump() for c in contradictions],
            "latency_ms": latency_ms,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/outreach")
async def generate_outreach(req: OutreachRequest):
    """Full pipeline: enrich → policy → compose → tone guard → send."""
    start = time.time()
    try:
        # 1. Enrich
        brief, gap_brief, contradictions = pipeline.enrich_prospect(
            company_name=req.company_name,
            domain=req.domain,
        )

        # 2. Policy decision
        from agent.enrichment.ai_maturity import AIMaturityResult
        ai_data = brief.ai_maturity
        ai_result = AIMaturityResult(
            score=ai_data.get("score", 0),
            confidence=ai_data.get("confidence", "low"),
            uncertainty_reason=ai_data.get("uncertainty_reason", ""),
            language_constraint=ai_data.get("language_constraint", "must_use_question_language"),
        )

        icp_data = brief.icp_segment
        policy = policy_engine.compute_policy(
            icp_segment=icp_data.get("primary"),
            icp_confidence=icp_data.get("confidence", 0),
            ai_maturity=ai_result,
            gap_brief=gap_brief,
            bench_summary=qualifier.bench_summary,
            prospect_signals=brief.model_dump(),
            contradictions=[c.model_dump() for c in contradictions],
        )

        # 3. Compose email
        draft = await composer.compose(
            policy=policy,
            brief=brief,
            gap_brief=gap_brief,
            prospect_name=req.company_name,
            sender_name=req.sender_name,
        )

        # 4. Tone guard check
        tone_result = await tone_guard.check(draft.body, policy)

        if tone_result.hard_fail:
            return {
                "status": "blocked",
                "reason": tone_result.hard_fail_reason,
                "issues": tone_result.issues,
            }

        if not tone_result.passed:
            return {
                "status": "needs_regen",
                "tone_score": tone_result.overall_score,
                "issues": tone_result.issues,
                "draft": draft.body,
            }

        # 5. Send email (through kill-switch)
        to_email = req.prospect_email or f"prospect@{req.domain or 'example.com'}"
        send_result = email_handler.send_email(
            to_email=to_email,
            subject=draft.subject,
            body=draft.body,
            tags={
                "policy_decision_id": policy.decision_id,
                "segment": str(policy.pitch_segment),
                "variant": draft.variant,
            }
        )

        # 6. Create HubSpot contact
        hs_result = hubspot.create_or_update_contact(
            email=to_email,
            company=req.company_name,
            icp_segment=icp_data.get("primary"),
            icp_confidence=icp_data.get("confidence"),
            ai_maturity_score=ai_data.get("score"),
            enrichment_timestamp=datetime.now().isoformat(),
        )

        # 7. Log activity
        hubspot.log_activity(
            contact_id=hs_result.get("id", ""),
            activity_type="outbound_email",
            body=f"Sent {draft.variant} email. Segment: {policy.pitch_segment}. "
                 f"Tone: {policy.tone_mode}. Score: {tone_result.overall_score}"
        )

        # 8. Create thread
        thread = orchestrator.get_or_create_thread(
            prospect_email=to_email,
            prospect_name=req.prospect_name or "",
            company=req.company_name,
        )
        thread.email_sent = True

        latency_ms = int((time.time() - start) * 1000)
        _latencies.append(latency_ms)

        # 9. Langfuse trace
        log_outreach_trace(
            prospect_name=req.company_name,
            policy_decision_id=policy.decision_id,
            variant=draft.variant,
            tone_score=tone_result.overall_score,
            email_sent=send_result.get("status") == "sent",
            cost_usd=0.002,
            latency_ms=latency_ms,
        )

        return {
            "status": "sent",
            "email": send_result,
            "hubspot": hs_result,
            "policy_decision_id": policy.decision_id,
            "draft_variant": draft.variant,
            "tone_score": tone_result.overall_score,
            "signals_used": draft.signals_used,
            "latency_ms": latency_ms,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/qualify")
async def process_qualification(req: QualifyRequest):
    """Process a qualification reply."""
    start = time.time()
    try:
        # Update thread
        if req.prospect_email:
            thread = orchestrator.handle_reply(req.prospect_email, "email", req.reply_text)

        state = QualificationState(
            prospect_name=req.prospect_name,
            thread_id=req.thread_id,
        )
        updated_state, response = qualifier.process_reply(state, req.reply_text)

        # Log to HubSpot
        hubspot.log_activity(
            contact_id="",
            activity_type="qualification_reply",
            body=f"Status: {updated_state.status}. "
                 f"Buying signals: {updated_state.buying_signals}. "
                 f"Objections: {updated_state.objections}"
        )

        # If ready to book, determine next channel
        next_action = None
        if req.prospect_email:
            next_action = orchestrator.determine_next_channel(thread)

        latency_ms = int((time.time() - start) * 1000)
        _latencies.append(latency_ms)

        return {
            "status": updated_state.status,
            "response": response,
            "buying_signals": updated_state.buying_signals,
            "objections": updated_state.objections,
            "escalation_reason": updated_state.escalation_reason,
            "next_action": next_action,
            "latency_ms": latency_ms,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/book")
async def book_discovery_call(req: BookRequest):
    """Book a discovery call via Cal.com."""
    start = time.time()
    try:
        # Get available slots
        slots = await calcom.get_available_slots(timezone=req.timezone)

        if not slots:
            return {"status": "no_slots", "message": "No available slots"}

        # Book first available slot
        first_slot = slots[0]
        booking = await calcom.create_booking(
            start_time=first_slot["time"],
            name=req.prospect_name,
            email=req.prospect_email,
            timezone=req.timezone,
            notes=req.notes,
            metadata={"company": req.company_name, "source": "conversion_engine"},
        )

        # Update thread state
        if req.prospect_email:
            orchestrator.mark_booked(req.prospect_email)

        # Create HubSpot deal
        deal = hubspot.create_deal(
            deal_name=f"Discovery: {req.company_name}",
            stage="appointmentscheduled",
        )

        # Log activity
        hubspot.log_activity(
            contact_id="",
            activity_type="call_booked",
            body=f"Discovery call booked for {req.prospect_name} at {req.company_name}. "
                 f"Time: {first_slot['time']}"
        )

        latency_ms = int((time.time() - start) * 1000)
        _latencies.append(latency_ms)

        return {
            "status": "booked",
            "booking": booking,
            "deal": deal,
            "slot": first_slot,
            "latency_ms": latency_ms,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SMSSendRequest(BaseModel):
    prospect_phone: str
    prospect_email: str
    message: str


@app.post("/sms/send")
async def send_sms(req: SMSSendRequest):
    """
    Send SMS for warm-lead scheduling.
    Channel hierarchy enforced: SMS is only allowed if the prospect
    has an active thread AND has already replied to an email (warm lead).
    """
    # --- Channel hierarchy gate ---
    thread = orchestrator._threads.get(req.prospect_email)
    if not thread:
        raise HTTPException(
            status_code=400,
            detail="No conversation thread found for this prospect. "
                   "Email outreach must happen before SMS.",
        )
    if not thread.email_replied:
        raise HTTPException(
            status_code=400,
            detail="Channel hierarchy violation: prospect has not replied "
                   "to email yet. SMS is reserved for warm leads only.",
        )

    result = sms_handler.send_sms(to_number=req.prospect_phone, message=req.message)

    # Update thread state
    thread.sms_sent = True
    thread.last_activity = datetime.now().isoformat()

    # Log to HubSpot
    hubspot.log_activity(
        contact_id="",
        activity_type="sms_sent",
        body=f"SMS sent to {req.prospect_phone}. Kill-switch: {config.KILL_SWITCH}",
    )

    return {"status": "sent", "sms_result": result, "channel_gate": "passed"}


@app.post("/webhook/email")
async def email_webhook(request: Request):
    """Handle Resend email webhooks (reply received)."""
    payload = await request.json()
    parsed = email_handler.process_webhook(payload)

    # Route reply to qualifier
    if parsed.get("text"):
        from_email = parsed.get("from", "")
        thread = orchestrator.handle_reply(from_email, "email", parsed["text"])

    return {"status": "received", "parsed": parsed}


@app.post("/webhook/sms")
async def sms_webhook(request: Request):
    """Handle Africa's Talking inbound SMS webhooks.
    Routes parsed replies to orchestrator and qualification handler."""
    payload = await request.json()
    parsed = sms_handler.process_webhook(payload)

    # Route inbound SMS to orchestrator for thread state update
    from_number = parsed.get("from", "")
    reply_text = parsed.get("text", "")

    # Resolve prospect email from phone number by scanning active threads
    prospect_email = None
    for email, thread in orchestrator._threads.items():
        if thread.sms_sent:  # this thread has had SMS interaction
            prospect_email = email
            break

    if prospect_email and reply_text:
        # Update thread state via orchestrator
        thread = orchestrator.handle_reply(prospect_email, "sms", reply_text)

        # Route to qualification handler
        state = QualificationState(
            prospect_name=thread.prospect_name,
            thread_id=thread.thread_id,
        )
        updated_state, response = qualifier.process_reply(state, reply_text)

        # Determine next action based on updated thread
        next_action = orchestrator.determine_next_channel(thread)

        # Log to HubSpot
        hubspot.log_activity(
            contact_id="",
            activity_type="sms_reply_received",
            body=f"SMS reply from {from_number}. Status: {updated_state.status}. "
                 f"Next action: {next_action}",
        )

        return {
            "status": "processed",
            "parsed": parsed,
            "thread_status": thread.status,
            "qualification_status": updated_state.status,
            "next_action": next_action,
        }

    return {"status": "received", "parsed": parsed, "routed": False}


@app.get("/threads")
async def list_threads():
    """List all conversation threads."""
    threads = orchestrator.get_all_threads()
    return {
        "total": len(threads),
        "threads": [t.model_dump() for t in threads],
        "stalled": len(orchestrator.get_stalled_threads()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
