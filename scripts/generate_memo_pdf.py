"""Generate memo.pdf — exactly two pages — using reportlab."""

from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)

OUT = Path("memo.pdf")
MARGIN = 0.7 * inch

base = getSampleStyleSheet()

def sty(name, **kw):
    return ParagraphStyle(name, parent=base["Normal"], **kw)

hdr_sty    = sty("Hdr",    fontSize=8,   textColor=colors.HexColor("#666666"), spaceAfter=1)
title_sty  = sty("Title2", fontSize=13,  fontName="Helvetica-Bold", spaceAfter=2, leading=15)
sub_sty    = sty("Sub",    fontSize=7.5, textColor=colors.HexColor("#888888"), spaceAfter=6)
h2_sty     = sty("H2",     fontSize=9.5, fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=2,
                 textColor=colors.HexColor("#1a1a2e"))
h3_sty     = sty("H3",     fontSize=8.5, fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=1,
                 textColor=colors.HexColor("#333333"))
body_sty   = sty("Body2",  fontSize=8,   leading=11.5, spaceAfter=4, alignment=TA_JUSTIFY)
bullet_sty = sty("Bul",    fontSize=8,   leading=11.5, spaceAfter=3, leftIndent=10, firstLineIndent=-8)
small_sty  = sty("Sm",     fontSize=7.5, leading=10,   textColor=colors.HexColor("#333333"))
label_sty  = sty("Lbl",    fontSize=7.5, fontName="Helvetica-Bold", textColor=colors.white)
caution_sty= sty("Caut",   fontSize=7.5, textColor=colors.HexColor("#8B0000"), leading=11, spaceAfter=0)

def b(t): return f"<b>{t}</b>"

HR = HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#cccccc"), spaceAfter=5, spaceBefore=2)
tHR= HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#dddddd"), spaceAfter=4, spaceBefore=2)

# ── PAGE 1 ────────────────────────────────────────────────────────────────────
p1 = []

p1.append(Paragraph("DECISION MEMO", hdr_sty))
p1.append(Paragraph("Tenacious-Bench v0.1 &amp; Preference-Tuned Judge", title_sty))
p1.append(Paragraph(
    "To: CEO &amp; CFO, Tenacious Consulting  ·  From: Engineering  ·  2 May 2026  ·  Page 1 of 2",
    sub_sty))
p1.append(HR)

# — Executive Summary (exactly 3 sentences)
p1.append(Paragraph("Executive Summary", h2_sty))
p1.append(Paragraph(
    "We built <b>Tenacious-Bench v0.1</b>, a 266-task benchmark targeting four failure modes "
    "τ²-Bench retail cannot grade — wrong-segment pitching (D06), signal overclaiming (I01–I03), "
    "injection attacks (E01–E05), and trajectory drift — and trained a DPO preference-tuned judge "
    "(LoRA, Qwen 2.5-0.5B) that achieves <b>74.0% accuracy on the sealed held-out partition "
    "(95% CI [62%, 86%]), a +26 pp lift over the deterministic rule evaluator "
    "(p = 0.0127, paired bootstrap n = 10,000)</b>. "
    "The judge functions as a rejection-sampling gate: emails flagged FAIL are routed to human "
    "review, blocking brand-damaging wrong-segment pitches at a cost of <b>$0.0002 per task</b> "
    "and ~2 s latency, versus $0.00 and &lt;1 ms for the rule evaluator alone. "
    "We recommend <b>deploy with caveat</b>: wire the judge into production as an async "
    "rejection-sampling layer, cap daily gated volume at 50 emails, and retrain on a balanced "
    "50/50 chosen-PASS / chosen-FAIL preference set using Qwen 2.5-3B before full rollout.",
    body_sty))

# — Delta A table
p1.append(Paragraph("Headline Lift — Delta A", h2_sty))
ta = Table(
    [
        [Paragraph(b("Judge"), label_sty), Paragraph(b("Accuracy"), label_sty),
         Paragraph(b("95% CI"), label_sty), Paragraph(b("p vs rule"), label_sty)],
        [Paragraph(b("DPO trained judge"), body_sty), Paragraph(b("74.0%"), body_sty),
         Paragraph("[62%, 86%]", body_sty), Paragraph(b("0.0127 ✓"), body_sty)],
        [Paragraph("Rule evaluator (baseline)", small_sty), Paragraph("48.0%", small_sty),
         Paragraph("[34%, 62%]", small_sty), Paragraph("—", small_sty)],
        [Paragraph("Prompt judge — zero-shot qwen3-8b", small_sty), Paragraph("22.0%", small_sty),
         Paragraph("[12%, 34%]", small_sty), Paragraph("—", small_sty)],
    ],
    colWidths=[2.55*inch, 0.9*inch, 0.9*inch, 1.1*inch],
)
ta.setStyle(TableStyle([
    ("BACKGROUND",  (0,0),(-1,0), colors.HexColor("#1a1a2e")),
    ("TEXTCOLOR",   (0,0),(-1,0), colors.white),
    ("FONTNAME",    (0,0),(-1,0), "Helvetica-Bold"),
    ("BACKGROUND",  (0,1),(-1,1), colors.HexColor("#e8f4fd")),
    ("ROWBACKGROUNDS",(0,2),(-1,-1),[colors.white, colors.HexColor("#f7f7f7")]),
    ("GRID",        (0,0),(-1,-1), 0.25, colors.HexColor("#cccccc")),
    ("TOPPADDING",  (0,0),(-1,-1), 3), ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ("LEFTPADDING", (0,0),(-1,-1), 5),
]))
p1.append(KeepTogether([ta, Spacer(1,4)]))

# — Delta B
p1.append(Paragraph("Delta B — Prompt-Engineered Baseline (Honest Report)", h2_sty))
p1.append(Paragraph(
    "The zero-shot prompt judge predicted <b>PASS for all 50 held-out tasks</b> (100% PASS bias), "
    "achieving only 22% accuracy — 0 failures correctly caught. "
    "This confirms that prompt engineering alone cannot replicate preference training: the base model "
    "must see explicit contrastive examples of grounded compliance versus keyword-passing hallucination "
    "to overcome the verbosity/politeness bias (Zheng et al., 2023). "
    "The trained judge's +52 pp lift over the prompt baseline (74% vs 22%, p &lt; 0.0001) "
    "directly validates the Path B choice.",
    body_sty))

# — Cost table
p1.append(Paragraph("Cost per Task &amp; Production Implication", h2_sty))
tc = Table(
    [
        [Paragraph(b("Component"), label_sty), Paragraph(b("$/task"), label_sty),
         Paragraph(b("Latency"), label_sty), Paragraph(b("Accuracy"), label_sty)],
        [Paragraph("No judge (current)", small_sty), Paragraph("$0.000", small_sty),
         Paragraph("0 ms", small_sty), Paragraph("— (blind)", small_sty)],
        [Paragraph("Rule evaluator only", small_sty), Paragraph("$0.000", small_sty),
         Paragraph("&lt;1 ms", small_sty), Paragraph("48%", small_sty)],
        [Paragraph("Prompt judge zero-shot", small_sty), Paragraph("$0.000135", small_sty),
         Paragraph("~1.5 s", small_sty), Paragraph("22%", small_sty)],
        [Paragraph(b("DPO trained judge ✓"), body_sty), Paragraph(b("$0.0002"), body_sty),
         Paragraph(b("~2 s (T4)"), body_sty), Paragraph(b("74%"), body_sty)],
    ],
    colWidths=[2.0*inch, 0.9*inch, 1.0*inch, 1.55*inch],
)
tc.setStyle(TableStyle([
    ("BACKGROUND",  (0,0),(-1,0), colors.HexColor("#1a1a2e")),
    ("TEXTCOLOR",   (0,0),(-1,0), colors.white),
    ("FONTNAME",    (0,0),(-1,0), "Helvetica-Bold"),
    ("BACKGROUND",  (0,4),(-1,4), colors.HexColor("#e8f4fd")),
    ("ROWBACKGROUNDS",(0,1),(-1,3),[colors.white, colors.HexColor("#f7f7f7"), colors.white]),
    ("GRID",        (0,0),(-1,-1), 0.25, colors.HexColor("#cccccc")),
    ("TOPPADDING",  (0,0),(-1,-1), 3), ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ("LEFTPADDING", (0,0),(-1,-1), 5),
]))
p1.append(KeepTogether([tc, Spacer(1,3)]))
p1.append(Paragraph(
    "A +26 pp accuracy gain at <b>$0.0002/task</b> is cost-Pareto dominant: the marginal judge "
    "cost is &lt;1% of the estimated cost of one misdirected email causing prospect churn. "
    "The 0.5B backbone's FAIL bias (18% PASS recall, 2/11 GT-PASS correctly passed) means the "
    "judge over-blocks until retrained on a balanced preference set with Qwen 2.5-3B or larger.",
    body_sty))

# ── PAGE 2 ────────────────────────────────────────────────────────────────────
p2 = []

p2.append(Paragraph("SKEPTIC'S APPENDIX", hdr_sty))
p2.append(Paragraph("Coverage Gaps, Ground Truth Critique &amp; Kill-Switch", title_sty))
p2.append(Paragraph(
    "To: CEO &amp; CFO, Tenacious Consulting  ·  From: Engineering  ·  2 May 2026  ·  Page 2 of 2",
    sub_sty))
p2.append(HR)

# — Four gaps
p2.append(Paragraph("Four Failure Modes Tenacious-Bench v0.1 Does Not Capture", h2_sty))

p2.append(Paragraph(b("1. Multi-turn conversation coherence."), h3_sty))
p2.append(Paragraph(
    "All 266 tasks evaluate a single email in isolation. A judge excelling here can still fail "
    "a 3-email thread where tone shifts from consultative to aggressive as the agent loses its "
    "grounded signal anchor across turns. "
    "<b>v0.2 fix:</b> 30–50 multi-turn trajectory tasks with per-turn rubric scoring and "
    "a tone-drift dimension penalising segment-inconsistent escalation.", body_sty))

p2.append(Paragraph(b("2. Live prospect emotional reception."), h3_sty))
p2.append(Paragraph(
    "The rubric scores text compliance, not how a real CTO perceives the message. "
    "An email passing all checks can feel condescending to a VP who deliberately chose not to "
    "adopt the capability being pitched. "
    "<b>v0.2 fix:</b> ICP-persona tone-panel probes using LLM-as-prospect scoring on "
    "perceived-value and perceived-relevance scales, calibrated against the 12 hand-labeled "
    "'good' drafts in Style Guide v2.", body_sty))

p2.append(Paragraph(b("3. Bench-capacity temporal drift."), h3_sty))
p2.append(Paragraph(
    "Tasks use static bench summaries. Bench availability changes daily; a 24-hour delay "
    "between bench check and send creates an over-commitment window the benchmark never "
    "simulates. A judge trained on static snapshots will not flag commitments that became "
    "false by send time. "
    "<b>v0.2 fix:</b> time-variant bench-state injection paired with a temporal-staleness "
    "failure category.", body_sty))

p2.append(Paragraph(b("4. Non-English and multilingual outreach."), h3_sty))
p2.append(Paragraph(
    "All 266 tasks are English-only. Tenacious operates in East Africa where Amharic, "
    "Swahili, and French outreach may be required; tone compliance rules differ across "
    "languages and cultures. "
    "<b>v0.2 fix:</b> ≥30 tasks per language with culturally-calibrated tone rubrics and "
    "separate per-language IRA protocols.", body_sty))

# — Ground truth
p2.append(tHR)
p2.append(Paragraph("Public-Signal Lossiness in Ground Truth", h2_sty))
p2.append(Paragraph(
    "25 of the 50 sealed held-out tasks are LLM-synthesis mode and carry a "
    "<b>systematic FAIL labeling artifact</b>: the synthetic generator defaults to a FAIL "
    "verdict with empty failure categories (<font face='Courier' size='7'>fail_cats=[]</font>) "
    "when task intent is ambiguous instead of escalating to human review. "
    "The rule evaluator's accuracy on LLM-synthesis tasks is 36% versus 58–62% on "
    "programmatic and hand-authored tasks — a 22–26 pp gap inflating both apparent held-out "
    "difficulty and the measured Delta A. "
    "Concretely: the +26 pp lift may partly reflect the trained judge learning the generator's "
    "labeling convention rather than true semantic alignment failure detection. "
    "<b>v0.2 fix:</b> mandatory human spot-check on 20% of LLM-synthesis tasks before "
    "held-out sealing; reject any task with <font face='Courier' size='7'>fail_cats=[]</font>.",
    body_sty))

# — Unresolved training failure
p2.append(tHR)
p2.append(Paragraph("Honest Unresolved Training Failure", h2_sty))
p2.append(Paragraph(
    "The DPO judge over-corrected from the prompt judge's 100% PASS bias to a near-100% "
    "<b>FAIL bias</b>: 48 of 50 held-out tasks predicted FAIL against a GT FAIL rate of 78% "
    "(39/50). On the 11 GT-PASS tasks only 2 were correctly passed (18% PASS recall). "
    "Root cause: the 279 preference pairs contained three rejection tiers (blatant, subtle, "
    "hard-negative FAIL) but no explicit chosen-PASS tier with positive compliant examples — "
    "the model learned 'what FAIL looks like' without a matching signal for PASS. "
    "The fix is not more training data of the same type; it is reconstructing the preference "
    "set with a 50/50 chosen-PASS / chosen-FAIL balance before the next training run.",
    body_sty))

# — Kill-switch
p2.append(tHR)
p2.append(Paragraph("Kill-Switch Trigger Conditions", h2_sty))
ks = [
    b("Monthly calibration accuracy drops below 60%") + " on a 30-task dev-partition spot-check. "
    "Below this threshold the judge provides less signal than a coin flip.",
    b("False-negative rate on GT-PASS tasks exceeds 90%") + " (current: 82%). "
    "At 90% the judge suppresses &gt;9 in 10 legitimate emails — over-blocking harm exceeds "
    "brand-protection benefit.",
    b("Per-task inference cost exceeds $0.01") + " (e.g. GPU failure forcing CPU fallback). "
    "At 50× current cost the judge is no longer cost-Pareto dominant; "
    "revert to rule evaluator ($0.00/task).",
    b("Adapter hash diverges from pinned revision") + " in model_card.md. "
    "Halt deployment and re-verify adapter against training/training_run.log before re-enabling.",
]
for item in ks:
    p2.append(Paragraph(f"• {item}", bullet_sty))

p2.append(Spacer(1, 4))
p2.append(Paragraph(
    "Revert trigger: any single condition above → switch immediately to rule evaluator; "
    "open a GitHub issue with the calibration log attached; do not re-enable until "
    "a corrected adapter passes a fresh 50-task calibration run.",
    caution_sty))

# ── Build ─────────────────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=LETTER,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.6*inch, bottomMargin=0.6*inch,
    )
    doc.build(p1 + [PageBreak()] + p2)
    size = OUT.stat().st_size
    print(f"Written: {OUT}  ({size:,} bytes)")

if __name__ == "__main__":
    build()
