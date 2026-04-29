"""Generate memo.pdf from memo.md content — exactly 2 pages."""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

W, H = letter
ML = MR = 0.75 * inch
MT = MB = 0.65 * inch


def build():
    doc = SimpleDocTemplate(
        "memo.pdf",
        pagesize=letter,
        leftMargin=ML, rightMargin=MR,
        topMargin=MT, bottomMargin=MB,
    )

    styles = getSampleStyleSheet()
    body_w = W - ML - MR

    # ── style definitions ──────────────────────────────────────────────
    title_s = ParagraphStyle("title_s", fontSize=13, fontName="Helvetica-Bold",
                             spaceAfter=2, leading=16)
    meta_s = ParagraphStyle("meta_s", fontSize=8, fontName="Helvetica",
                            spaceAfter=1, leading=10, textColor=colors.HexColor("#444444"))
    h2_s = ParagraphStyle("h2_s", fontSize=9.5, fontName="Helvetica-Bold",
                          spaceBefore=5, spaceAfter=2, leading=12,
                          textColor=colors.HexColor("#1a1a2e"))
    body_s = ParagraphStyle("body_s", fontSize=7.6, fontName="Helvetica",
                            spaceAfter=3, leading=10.5)
    footnote_s = ParagraphStyle("fn_s", fontSize=6.8, fontName="Helvetica",
                                spaceAfter=2, leading=9,
                                textColor=colors.HexColor("#555555"))
    page_label_s = ParagraphStyle("pl_s", fontSize=8.5, fontName="Helvetica-Bold",
                                  spaceBefore=4, spaceAfter=3, leading=11,
                                  textColor=colors.HexColor("#2c3e50"))

    def h(text): return Paragraph(text, h2_s)
    def p(text): return Paragraph(text, body_s)
    def fn(text): return Paragraph(text, footnote_s)
    def sp(n=3): return Spacer(1, n)
    def hr(): return HRFlowable(width="100%", thickness=0.4,
                                color=colors.HexColor("#cccccc"), spaceAfter=3)

    # ── table helper ────────────────────────────────────────────────────
    def make_table(data, col_widths, header_cols=None):
        t = Table(data, colWidths=col_widths)
        style = [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("LEADING", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1),
             [colors.HexColor("#f5f5f5"), colors.white]),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde3ec")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bbbbbb")),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
        if header_cols:
            for col in header_cols:
                style.append(("FONTNAME", (col, 1), (col, -1), "Helvetica-Bold"))
        t.setStyle(TableStyle(style))
        return t

    story = []

    # ══════════════════════════════════════════════════════════════════
    # PAGE 1 — THE DECISION
    # ══════════════════════════════════════════════════════════════════
    story.append(Paragraph("Decision Memo: The Conversion Engine", title_s))
    story.append(Paragraph(
        "<b>To:</b> CEO &amp; CFO, Tenacious Consulting and Outsourcing &nbsp;&nbsp;"
        "<b>From:</b> Engineering &nbsp;&nbsp;<b>Date:</b> April 25, 2026", meta_s))
    story.append(Paragraph(
        "<b>Subject:</b> Automated Lead Generation System — Pilot Recommendation", meta_s))
    story.append(sp(2))
    story.append(hr())

    story.append(Paragraph("Page 1: The Decision", page_label_s))

    # Executive Summary
    story.append(h("Executive Summary"))
    story.append(p(
        "We built a signal-grounded outbound system enriching every prospect from Crunchbase "
        "firmographics, 60-day job-post velocity, layoffs.fyi, leadership-change detection, and "
        "AI maturity scoring — converting cold outreach into a verifiable research finding. "
        "Across 108 policy decisions, 52 (48%) qualified at a measured cost of "
        "<b>$0.013/qualified lead</b> (vs. ~$150–$400 for a manual SDR per qualified lead — a "
        "99.97% cost reduction); the full pipeline ran at <b>p50: 1.5 s, p95: 1.9 s</b> with "
        "100% tone-guard compliance in batch test (n=25). We recommend a bounded "
        "<b>30-day Segment 1 pilot: 200 prospects, $200 budget</b>, to establish live "
        "reply-rate data before scaling."
    ))
    story.append(sp(2))

    # τ²-Bench table
    story.append(h("τ²-Bench Baseline"))
    tau_data = [
        ["Metric", "Baseline (instructor)", "PEV V1 (ours)"],
        ["pass@1", "0.7267", "0.4615"],
        ["95% CI", "[0.6504, 0.7917]", "[0.2308, 0.7692]"],
        ["Delta A", "—", "−0.2652"],
        ["Cost/task", "$0.0199", "$0.0199 (est.)"],
        ["p50 / p95 latency", "105.95 s / 551.65 s", "166.13 s / 279.05 s"],
        ["n scored", "150", "13/20 (7 API errors*)"],
    ]
    cw = [body_w * 0.35, body_w * 0.32, body_w * 0.33]
    story.append(make_table(tau_data, cw, header_cols=[1]))
    story.append(fn(
        "*7 errors = OpenRouter timeouts/credit exhaustion; excluded from scoring; "
        "no systematic bias. Model: qwen/qwen3-next-80b-a3b-thinking. "
        "Baseline: instructor, commit d11a97072c."
    ))
    story.append(sp(3))

    # Cost table
    story.append(h("Cost per Qualified Lead — Trace-Derived"))
    story.append(fn("Source: outputs/policy_trace.jsonl (108 records), outputs/invoice_summary.json"))
    cost_data = [
        ["Component", "Unit cost", "Total"],
        ["Enrichment (Crunchbase + job posts + layoffs.fyi)", "$0.002/prospect", "$0.22 (108×)"],
        ["LLM composition", "$0.008/email", "$0.42 (52×)"],
        ["Tone-guard check", "$0.001/email", "$0.05 (52×)"],
        ["Cost per qualified lead", "", "$0.013"],
    ]
    cw2 = [body_w * 0.55, body_w * 0.22, body_w * 0.23]
    story.append(make_table(cost_data, cw2, header_cols=[2]))
    story.append(p(
        "ICP match: 52/108 = 48%. Policy engine abstained on 56 — no email sent. "
        "Tenacious target: $5/lead. <b>Actual: $0.013.</b> Estimated production cost: "
        "$0.05–$0.15/qualified lead — still well under target."
    ))
    story.append(sp(2))

    # Stalled-Thread
    story.append(h("Stalled-Thread Rate Delta"))
    story.append(p(
        "<i>Definition:</i> stalled-thread rate = fraction of inbound prospect replies that "
        "receive no follow-up action within 24 hours. Tenacious manual baseline: <b>30–40%</b> "
        "stall (executive interview; cause: human response lag of 1–3 days). System post-reply "
        "action rate: <b>100%</b> — every inbound webhook (/webhook/email, /webhook/sms) "
        "triggers qualifier processing at <b>p50 1.5 s</b> with zero dropped replies in batch "
        "test (n=25; source: e2e_batch_results.json). The eliminated stall component is human "
        "response latency (days → seconds). Prospect initial-reply rate and "
        "conversation-continuation rate are unmeasurable in synthetic evaluation — no live "
        "interactions simulated; these are the primary pilot success criteria."
    ))
    story.append(sp(2))

    # Competitive-Gap
    story.append(h("Competitive-Gap Outbound Performance"))
    story.append(fn("Source: outputs/policy_trace.jsonl (52 qualified) + reply_simulation_results.json (LLM judge: claude-3-5-haiku, n=52, seed=42, synthetic):"))
    gap_data = [
        ["Variant", "n", "Tone-guard", "Bench viol.", "Sim. reply rate", "Delta"],
        ["Signal-grounded (assertive/suggestive)", "30 (58%)", "100%", "0", "3.3% (1/30)", "—"],
        ["Exploratory (neutral tone)", "22 (42%)", "100%", "0", "0.0% (0/22)", "+3.3 pp"],
    ]
    cw3 = [body_w * 0.30, body_w * 0.10, body_w * 0.12, body_w * 0.12, body_w * 0.20, body_w * 0.16]
    story.append(make_table(gap_data, cw3))
    story.append(p(
        "Gap brief: 2/52 (4%) — thin sector coverage in test sample; expected 40–60% with full database. "
        "Delta direction consistent with industry data (Clay/Smartlead 2026: 7–12% vs. 1–3%). "
        "Absolute rates suppressed by cold outsourcing pitch; live pilot establishes calibrated baseline. "
        "Primary metric: A/B reply-rate delta tracked by policy_trace.variant in HubSpot over 30 days."
    ))
    story.append(sp(2))

    # Pilot Scope
    story.append(h("Pilot Scope"))
    story.append(p(
        "Segment 1 (Series A/B, $5–30M, ≤ 6 months ago) | "
        "<b>200 prospects / 30 days</b> | <b>$200 budget</b>"
    ))
    story.append(p(
        "Success criterion: <b>≥ 2 discovery calls</b> + zero tone-escalation complaints + "
        "zero bench violations + reply rate ≥ 4%. "
        "<i>(Math: 200 × 48% = 96 leads; at 4% reply = 4 replies; at 35% to call = 1.4 — "
        "target of 2 requires ~6% reply or 50% reply-to-call.)</i>"
    ))

    # ── page break ───────────────────────────────────────────────────
    from reportlab.platypus import PageBreak
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════
    # PAGE 2 — THE SKEPTIC'S APPENDIX
    # ══════════════════════════════════════════════════════════════════
    story.append(Paragraph("Page 2: The Skeptic's Appendix", page_label_s))
    story.append(hr())

    # Four Failure Modes
    story.append(h("Four Failure Modes τ²-Bench Does Not Capture"))
    story.append(p(
        "<b>1. Offshore-perception triggers.</b> τ²-Bench scores task completion, not emotional "
        "reception. \"Replace higher-cost roles with offshore equivalents\" passes every benchmark "
        "task while triggering in-house managers who forward it to their CTO as evidence of vendor "
        "aggression. No sentiment model for the recipient. "
        "Fix: ICP-persona tone-panel probes (~$200/month). Probes D01–D05 cover drift; D06 partially resolved."
    ))
    story.append(p(
        "<b>2. Bench over-commitment against a live inventory.</b> τ²-Bench uses a static world "
        "model; bench availability changes daily. Our hard-gate blocks unsupported commitments, "
        "but a context-refresh lag creates a window. Fix: webhook from bench system; 1–2 days."
    ))
    story.append(p(
        "<b>3. Condescending competitor-gap framing.</b> τ²-Bench cannot penalize an agent that "
        "is technically correct but socially wrong. A CTO who deliberately skipped the \"missing\" "
        "capability reads the gap analysis as arrogant. Probe G05 caught 60% escalation before "
        "tone-guard tuning. Fix: prospect-awareness hedge in templates; partially implemented."
    ))
    story.append(p(
        "<b>4. Multi-thread context leakage.</b> τ²-Bench is single-threaded. Simultaneous "
        "outreach to co-founder and VP Engineering can leak context — a GDPR incident. K01/K02 "
        "confirmed correct isolation at low concurrency; untested under 50+ concurrent threads."
    ))
    story.append(sp(3))

    # Public-Signal Lossiness
    story.append(h("Public-Signal Lossiness of AI Maturity Scoring"))
    story.append(p(
        "<i>Loud but shallow (false positive):</i> Company posts AI thought leadership — CEO "
        "keynotes, \"AI-first\" letters, one \"AI PM\" role — and scores 2–3. Agent pitches "
        "Segment 4 (ML platform migration) to a company with no data layer. Prospect responds "
        "\"we already have this.\" <i>Impact:</i> brand damage, wasted contact. Estimated FP "
        "rate at score ≥ 2: <b>15–25%</b> (qualitative review of 1,001-company sample; "
        "precision/recall not yet computed against labelled data)."
    ))
    story.append(p(
        "<i>Quiet but sophisticated (false negative):</i> Stealth AI startup keeps repos "
        "private, recruits by referral, scores 0. Agent sends generic email, missing the "
        "highest-margin Segment 4 engagement. <b>Mitigation before production:</b> hand-label "
        "20–30 Tenacious past prospects to compute precision/recall."
    ))
    story.append(sp(3))

    # Honest Unresolved Failure
    story.append(h("Honest Unresolved Failure — PEV Does Not Beat Baseline"))
    story.append(p(
        "Delta A = <b>−0.2652</b> (V1 pass@1 = 0.4615 vs. baseline 0.7267; t = −1.84, df = 12, "
        "p = 0.955 one-sided; source: eval/score_log.json). The mechanism made performance worse. "
        "Diagnosis: the thinking model already applies chain-of-thought internally; explicit "
        "UNDERSTAND/VERIFY/PLAN instructions compete with native reasoning. V1/V2 also produced "
        "a confirmation anti-pattern (agent asked user to confirm → user said yes + stopped → "
        "tool never called → reward = 0). V3 corrected this but n=3 valid scores (17/20 lost to "
        "credit exhaustion) — statistically meaningless. <b>What to deploy:</b> the enrichment + "
        "policy + compose stack, not the PEV agent. The τ²-Bench result documents benchmark "
        "performance honestly; it does not reflect outreach pipeline readiness."
    ))
    story.append(sp(3))

    # Kill-Switch
    story.append(h("Kill-Switch Clause"))
    story.append(p(
        "<font name='Courier' size='7'>KILL_SWITCH</font> defaults "
        "<b>ON</b>; all outbound routes to staff sink until "
        "<font name='Courier' size='7'>CONVERSION_ENGINE_LIVE=true</font> is set by the CEO "
        "(<font name='Courier' size='7'>bash smoke_test.sh</font> exits 0). "
        "Pause if: (a) bench commitment not in bench summary; "
        "(b) Langfuse tone-compliance &lt; 95% over any 7-day window; or "
        "(c) reply rate &lt; 2% after 500 contacts."
    ))

    doc.build(story)
    print("memo.pdf written")


if __name__ == "__main__":
    build()
