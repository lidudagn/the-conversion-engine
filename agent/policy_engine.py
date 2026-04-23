"""
★ Decision Policy Engine — Pre-LLM Decision Layer
Deterministic rules that control what the LLM can and cannot do.
The LLM follows policies, not intuition.

Every decision is logged to outputs/policy_trace.jsonl for Act IV traceability.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict

from agent.enrichment.ai_maturity import AIMaturityResult
from agent.enrichment.competitor_gap import CompetitorGapBrief


@dataclass
class PolicyDecision:
    """Output of the policy engine — consumed by composer before any LLM call."""

    decision_id: str = ""

    # Segment selection
    pitch_segment: Optional[int] = None   # 1-4 or None if abstaining
    segment_confidence: float = 0.0       # 0-1
    abstain: bool = False                 # True = send exploratory email only

    # Tone control
    tone_mode: str = "exploratory"        # "assertive" | "suggestive" | "exploratory"

    # Competitor gap usage
    use_competitor_gap: bool = False
    gap_delivery_mode: str = "soft"       # "direct" | "soft"

    # Signal usage constraints
    assertable_signals: list = field(default_factory=list)   # Can state as fact
    question_signals: list = field(default_factory=list)     # Must phrase as question
    omit_signals: list = field(default_factory=list)         # Too weak to mention

    # Contradictions
    contradictions: list = field(default_factory=list)
    contradiction_framing: str = ""

    # Bench constraint
    bench_match: bool = True
    available_capacity: dict = field(default_factory=dict)

    # Audit trail
    rules_triggered: list = field(default_factory=list)


class PolicyEngine:
    """
    Pre-LLM decision layer. All rules are deterministic — no LLM calls.
    Every decision is logged to policy_trace.jsonl.
    """

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.output_dir / "policy_trace.jsonl"

    def compute_policy(
        self,
        icp_segment: Optional[int],
        icp_confidence: float,
        ai_maturity: AIMaturityResult,
        gap_brief: Optional[CompetitorGapBrief],
        bench_summary: dict,
        prospect_signals: dict,
        contradictions: list[dict] | None = None,
    ) -> PolicyDecision:
        """
        Compute policy decision from enrichment data.
        This runs BEFORE any LLM call.
        """

        decision = PolicyDecision(
            decision_id=str(uuid.uuid4()),
            pitch_segment=icp_segment,
            segment_confidence=icp_confidence,
        )
        rules = []

        # ─── 1. Segment + Abstention ─────────────────────────────────────
        if icp_confidence < 0.5:
            decision.abstain = True
            decision.tone_mode = "exploratory"
            rules.append("ICP_CONFIDENCE_BELOW_0.5 → abstain + exploratory tone")
        elif icp_confidence < 0.7:
            decision.tone_mode = "exploratory"
            rules.append("ICP_CONFIDENCE_BELOW_0.7 → exploratory tone")
        elif icp_confidence < 0.85:
            decision.tone_mode = "suggestive"
            rules.append("ICP_CONFIDENCE_BELOW_0.85 → suggestive tone")
        else:
            decision.tone_mode = "assertive"
            rules.append("ICP_CONFIDENCE_ABOVE_0.85 → assertive tone")

        # ─── 2. Segment 4 Hard Gate ──────────────────────────────────────
        if icp_segment == 4 and ai_maturity.score < 2:
            decision.pitch_segment = None
            decision.abstain = True
            rules.append("SEGMENT_4_AI_MATURITY_BELOW_2 → hard block, abstain")

        # ─── 3. Competitor Gap Gating ────────────────────────────────────
        if ai_maturity.score < 2:
            decision.use_competitor_gap = False
            rules.append("AI_MATURITY_BELOW_2 → block competitor gap")
        elif ai_maturity.confidence == "low":
            decision.use_competitor_gap = False
            rules.append("AI_MATURITY_LOW_CONFIDENCE → block competitor gap")
        elif gap_brief and gap_brief.confidence_avg < 0.6:
            decision.use_competitor_gap = False
            rules.append("GAP_CONFIDENCE_BELOW_0.6 → hard block competitor gap (fake insight risk)")
        elif gap_brief and gap_brief.confidence_avg < 0.7:
            decision.use_competitor_gap = True
            decision.gap_delivery_mode = "soft"
            rules.append("GAP_CONFIDENCE_BELOW_0.7 → soft delivery mode")
        elif gap_brief:
            decision.use_competitor_gap = True
            decision.gap_delivery_mode = "direct"
            rules.append("GAP_CONFIDENCE_ABOVE_0.7 → direct delivery mode")
        else:
            decision.use_competitor_gap = False
            rules.append("NO_GAP_BRIEF → skip competitor gap")

        # ─── 4. Signal Classification ────────────────────────────────────
        signal_keys = ["funding", "job_velocity", "layoffs", "leadership", "ai_maturity"]
        for signal_name in signal_keys:
            signal_data = prospect_signals.get(signal_name)
            if not isinstance(signal_data, dict):
                continue
            confidence = signal_data.get("confidence", "low")
            if confidence == "high":
                decision.assertable_signals.append(signal_name)
                rules.append(f"SIGNAL_{signal_name.upper()}_HIGH → assertable")
            elif confidence == "medium":
                decision.question_signals.append(signal_name)
                rules.append(f"SIGNAL_{signal_name.upper()}_MEDIUM → question only")
            else:
                decision.omit_signals.append(signal_name)
                rules.append(f"SIGNAL_{signal_name.upper()}_LOW → omit")

        # ─── 5. AI Maturity Language Constraint Override ─────────────────
        if ai_maturity.language_constraint == "must_use_question_language":
            # Force AI-related signals to question mode even if individually "medium"
            if "ai_maturity" in decision.assertable_signals:
                decision.assertable_signals.remove("ai_maturity")
                decision.question_signals.append("ai_maturity")
                rules.append("AI_MATURITY_QUESTION_LANGUAGE → override to question")

        # ─── 6. Bench Hard Constraint ────────────────────────────────────
        prospect_stack = prospect_signals.get("tech_stack", {}).get("value", [])
        if isinstance(prospect_stack, list):
            matched = []
            for stack in prospect_stack:
                if stack.lower() in [s.lower() for s in bench_summary.get("available_stacks", [])]:
                    matched.append(stack)
            decision.available_capacity = {
                "matched_stacks": matched,
                "bench_available": bench_summary.get("total_available", 0)
            }
            if not matched:
                decision.bench_match = False
                rules.append("BENCH_NO_MATCH → route to human")
            else:
                decision.bench_match = True
                rules.append(f"BENCH_MATCH → {matched}")

        # ─── 7. Contradictions ───────────────────────────────────────────
        if contradictions:
            # Only include high-confidence contradictions
            high_conf = [c for c in contradictions if c.get("confidence", 0) >= 0.6]
            decision.contradictions = high_conf
            if high_conf:
                decision.contradiction_framing = high_conf[0].get("framing", "")
                c_name = high_conf[0].get("name", "unknown").upper()
                rules.append(f"CONTRADICTION_{c_name} → include framing")
            low_conf = [c for c in contradictions if c.get("confidence", 0) < 0.6]
            for c in low_conf:
                c_name = c.get("name", "unknown").upper()
                rules.append(f"CONTRADICTION_{c_name}_LOW_CONF → omit")

        decision.rules_triggered = rules

        # ─── Log Decision ────────────────────────────────────────────────
        self._log_decision(decision, icp_confidence, ai_maturity, gap_brief)

        return decision

    def _log_decision(
        self,
        decision: PolicyDecision,
        icp_confidence: float,
        ai_maturity: AIMaturityResult,
        gap_brief: Optional[CompetitorGapBrief]
    ):
        """Log decision to policy_trace.jsonl for Act IV traceability."""
        trace = {
            "decision_id": decision.decision_id,
            "timestamp": datetime.now().isoformat(),
            "inputs": {
                "icp_confidence": icp_confidence,
                "ai_maturity_score": ai_maturity.score,
                "ai_maturity_confidence": ai_maturity.confidence,
                "gap_confidence_avg": gap_brief.confidence_avg if gap_brief else None,
            },
            "rules_triggered": decision.rules_triggered,
            "output": {
                "abstain": decision.abstain,
                "tone_mode": decision.tone_mode,
                "pitch_segment": decision.pitch_segment,
                "use_competitor_gap": decision.use_competitor_gap,
                "gap_delivery_mode": decision.gap_delivery_mode,
                "bench_match": decision.bench_match,
                "assertable_signals": decision.assertable_signals,
                "question_signals": decision.question_signals,
                "omit_signals": decision.omit_signals,
                "contradictions_used": len(decision.contradictions),
            }
        }

        with open(self.trace_file, "a") as f:
            f.write(json.dumps(trace) + "\n")
