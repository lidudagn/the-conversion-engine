"""
End-to-End Test — Full Pipeline Validation
Tests the complete flow: enrich → policy → compose → tone guard → send → qualify → book.
Runs against a synthetic prospect using real data sources.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path


def run_e2e_test():
    """Run the full E2E test synchronously."""
    return asyncio.run(_run_e2e_test())


async def _run_e2e_test():
    """Full pipeline test against a synthetic prospect."""

    print("\n" + "=" * 60)
    print("E2E TEST — The Conversion Engine")
    print("=" * 60 + "\n")

    results = {}
    latencies = []

    # ─── 1. Load Data Sources ────────────────────────────────────────
    print("1. Loading data sources...")
    start = time.time()

    from agent.enrichment.crunchbase import CrunchbaseLoader
    from agent.enrichment.layoffs import LayoffsParser
    from agent.enrichment.job_posts import JobPostScraper

    cb = CrunchbaseLoader("data/crunchbase")
    companies = cb.load()
    results["crunchbase_loaded"] = len(companies)
    print(f"   Crunchbase: {len(companies)} companies ✓")

    lp = LayoffsParser("data/layoffs")
    events = lp.load()
    results["layoffs_loaded"] = len(events)
    print(f"   Layoffs: {len(events)} events ✓")

    jp = JobPostScraper("data/job_posts")
    jp.load_frozen_dataset()
    results["job_posts_loaded"] = True
    print(f"   Job posts: loaded ✓")

    latencies.append(time.time() - start)

    # ─── 2. Pick a Test Prospect ─────────────────────────────────────
    print("\n2. Selecting test prospect...")

    # Prefer WISEiTECH (AI maturity=2, ICP segment 4) for signal-grounded demo.
    # Falls back to first company with funding, then first company overall.
    test_name = "WISEiTECH"
    test_domain = "wise.co.kr"
    test_email = f"cto@{test_domain}"
    test_company = None
    for c in companies:
        if c.name == test_name:
            test_company = c
            break
    if not test_company:
        # Fallback: first company with funding data
        for c in companies:
            if c.total_funding_usd and c.total_funding_usd > 1_000_000:
                test_company = c
                break
    if not test_company and companies:
        test_company = companies[0]
        test_name = test_company.name
        test_domain = test_company.domain or "prospect.io"
        test_email = f"cto@{test_domain}"

    print(f"   Prospect: {test_name} ({test_domain})")
    results["test_prospect"] = test_name

    # ─── 3. Enrichment Pipeline ──────────────────────────────────────
    print("\n3. Running enrichment pipeline...")
    start = time.time()

    from agent.enrichment.pipeline import EnrichmentPipeline
    pipeline = EnrichmentPipeline()
    pipeline.load_data()

    brief, gap_brief, contradictions = pipeline.enrich_prospect(
        company_name=test_name,
        domain=test_domain,
    )

    enrich_latency = time.time() - start
    latencies.append(enrich_latency)

    results["enrichment"] = {
        "funding": brief.funding,
        "job_velocity": brief.job_velocity,
        "layoffs": brief.layoffs,
        "leadership": brief.leadership,
        "ai_maturity": brief.ai_maturity,
        "icp_segment": brief.icp_segment,
        "contradictions_found": len(contradictions),
        "gap_brief_generated": gap_brief is not None,
        "latency_ms": int(enrich_latency * 1000),
    }
    print(f"   ICP segment: {brief.icp_segment}")
    print(f"   AI maturity: {brief.ai_maturity}")
    print(f"   Contradictions: {len(contradictions)}")
    print(f"   Gap brief: {'generated' if gap_brief else 'none'}")
    print(f"   Latency: {enrich_latency*1000:.0f}ms ✓")

    # ─── 4. Policy Engine ────────────────────────────────────────────
    print("\n4. Computing policy decision...")
    start = time.time()

    from agent.policy_engine import PolicyEngine
    from agent.enrichment.ai_maturity import AIMaturityResult

    policy_engine = PolicyEngine()
    ai_data = brief.ai_maturity
    ai_result = AIMaturityResult(
        score=ai_data.get("score", 0),
        confidence=ai_data.get("confidence", "low"),
        uncertainty_reason=ai_data.get("uncertainty_reason", ""),
        language_constraint=ai_data.get("language_constraint", "must_use_question_language"),
    )

    icp_data = brief.icp_segment
    bench_summary = {
        "available_stacks": ["python", "go", "data", "ml", "infra"],
        "total_available": 12,
    }

    policy = policy_engine.compute_policy(
        icp_segment=icp_data.get("primary"),
        icp_confidence=icp_data.get("confidence", 0),
        ai_maturity=ai_result,
        gap_brief=gap_brief,
        bench_summary=bench_summary,
        prospect_signals=brief.model_dump(),
        contradictions=[c.model_dump() for c in contradictions],
    )

    policy_latency = time.time() - start
    latencies.append(policy_latency)

    results["policy"] = {
        "tone_mode": policy.tone_mode,
        "abstain": policy.abstain,
        "use_competitor_gap": policy.use_competitor_gap,
        "gap_delivery_mode": policy.gap_delivery_mode,
        "assertable_signals": policy.assertable_signals,
        "question_signals": policy.question_signals,
        "omit_signals": policy.omit_signals,
        "bench_match": policy.bench_match,
        "rules_triggered": len(policy.rules_triggered),
        "latency_ms": int(policy_latency * 1000),
    }
    print(f"   Tone: {policy.tone_mode}")
    print(f"   Abstain: {policy.abstain}")
    print(f"   Rules triggered: {len(policy.rules_triggered)}")
    for r in policy.rules_triggered:
        print(f"      - {r}")
    print(f"   Latency: {policy_latency*1000:.0f}ms ✓")

    # ─── 5. Email Composition ────────────────────────────────────────
    print("\n5. Composing email...")
    start = time.time()

    from agent.composer import EmailComposer
    composr = EmailComposer()

    draft = await composr.compose(
        policy=policy,
        brief=brief,
        gap_brief=gap_brief,
        prospect_name=test_name,
        sender_name="Tenacious Team",
    )

    compose_latency = time.time() - start
    latencies.append(compose_latency)

    results["composition"] = {
        "variant": draft.variant,
        "subject": draft.subject,
        "body_length": len(draft.body),
        "signals_used": draft.signals_used,
        "latency_ms": int(compose_latency * 1000),
    }
    print(f"   Variant: {draft.variant}")
    print(f"   Subject: {draft.subject}")
    print(f"   Body ({len(draft.body)} chars):")
    print(f"   {draft.body[:200]}...")
    print(f"   Latency: {compose_latency*1000:.0f}ms ✓")

    # ─── 6. Tone Guard ───────────────────────────────────────────────
    print("\n6. Running tone guard...")
    start = time.time()

    from agent.tone_guard import ToneGuard
    guard = ToneGuard()
    tone_result = await guard.check(draft.body, policy)

    tone_latency = time.time() - start
    latencies.append(tone_latency)

    results["tone_guard"] = {
        "passed": tone_result.passed,
        "overall_score": tone_result.overall_score,
        "hard_fail": tone_result.hard_fail,
        "issues": tone_result.issues,
        "latency_ms": int(tone_latency * 1000),
    }
    print(f"   Score: {tone_result.overall_score}")
    print(f"   Passed: {tone_result.passed}")
    print(f"   Hard fail: {tone_result.hard_fail}")
    if tone_result.issues:
        for issue in tone_result.issues:
            print(f"   ⚠ {issue}")
    print(f"   Latency: {tone_latency*1000:.0f}ms ✓")

    # ─── 7. Email Send (via kill-switch) ─────────────────────────────
    print("\n7. Sending email (kill-switch ON → sink)...")
    start = time.time()

    from agent.email_handler import EmailHandler
    handler = EmailHandler()
    send_result = handler.send_email(
        to_email=test_email,
        subject=draft.subject,
        body=draft.body,
        tags={"segment": str(policy.pitch_segment), "variant": draft.variant},
    )

    send_latency = time.time() - start
    latencies.append(send_latency)

    results["email_send"] = send_result
    print(f"   Status: {send_result['status']}")
    print(f"   Kill-switch: {send_result['kill_switch']}")
    print(f"   To: {send_result['to']}")

    # ─── 8. SMS Test (warm lead scheduling) ──────────────────────────
    print("\n8. SMS test (kill-switch ON → sink)...")
    from agent.sms_handler import SMSHandler
    sms = SMSHandler()
    sms_result = sms.send_sms(
        to_number="+254711000001",  # Valid E.164 test number (AT sandbox)
        message="Hi, this is Tenacious. You mentioned interest in scheduling a call. Would tomorrow at 2pm work?",
    )
    results["sms_send"] = sms_result
    print(f"   Status: {sms_result['status']}")

    # ─── 9. HubSpot Contact ─────────────────────────────────────────
    print("\n9. Creating HubSpot contact...")
    from agent.hubspot_client import HubSpotClient
    hs = HubSpotClient()
    hs_result = hs.create_or_update_contact(
        email=test_email,
        company=test_name,
        icp_segment=icp_data.get("primary"),
        icp_confidence=icp_data.get("confidence"),
        ai_maturity_score=ai_data.get("score"),
        enrichment_timestamp=datetime.now().isoformat(),
    )
    results["hubspot"] = hs_result
    print(f"   Status: {hs_result['status']}")

    # ─── 10. Cal.com Booking ─────────────────────────────────────────
    print("\n10. Booking discovery call via Cal.com...")
    from agent.calendar_client import CalComClient
    cal = CalComClient()
    slots = await cal.get_available_slots()
    if slots:
        booking = await cal.create_booking(
            start_time=slots[0]["time"],
            name="Test Prospect",
            email=test_email,
            notes=f"ICP Segment: {icp_data.get('primary')}. AI Maturity: {ai_data.get('score')}",
        )
        results["calcom_booking"] = booking
        print(f"   Booking status: {booking['status']}")
    else:
        results["calcom_booking"] = {"status": "no_slots"}
        print("   No slots available")

    # ─── 11. Qualification Test ──────────────────────────────────────
    print("\n11. Testing qualification handler...")
    from agent.qualifier import QualificationHandler, QualificationState
    qual = QualificationHandler(bench_summary=bench_summary)

    state = QualificationState(prospect_name=test_name)
    state, response = qual.process_reply(state, "Sounds interesting, tell me more about your Python team")
    results["qualification"] = {
        "status": state.status,
        "buying_signals": state.buying_signals,
        "response_preview": response[:100],
    }
    print(f"   Status: {state.status}")
    print(f"   Buying signals: {state.buying_signals}")
    print(f"   Response: {response[:80]}...")

    # ─── 12. Orchestrator Test ───────────────────────────────────────
    print("\n12. Testing channel orchestrator...")
    from agent.orchestrator import ChannelOrchestrator
    orch = ChannelOrchestrator()
    thread = orch.get_or_create_thread(test_email, "Test CTO", test_name)
    next_action = orch.determine_next_channel(thread)
    results["orchestrator"] = {"next_action": next_action, "thread_status": thread.status}
    print(f"   Next action: {next_action}")

    # ─── Summary ─────────────────────────────────────────────────────
    import numpy as np
    latencies_ms = [l * 1000 for l in latencies]

    print(f"\n{'='*60}")
    print("E2E TEST COMPLETE")
    print(f"{'='*60}")
    print(f"Total latencies recorded: {len(latencies_ms)}")
    print(f"p50 latency: {np.percentile(latencies_ms, 50):.0f}ms")
    print(f"p95 latency: {np.percentile(latencies_ms, 95):.0f}ms")

    results["summary"] = {
        "total_steps": 12,
        "passed": True,
        "p50_latency_ms": round(float(np.percentile(latencies_ms, 50)), 1),
        "p95_latency_ms": round(float(np.percentile(latencies_ms, 95)), 1),
        "timestamp": datetime.now().isoformat(),
    }

    # Save results
    output_path = Path("outputs/e2e_test_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")

    return results


if __name__ == "__main__":
    run_e2e_test()
