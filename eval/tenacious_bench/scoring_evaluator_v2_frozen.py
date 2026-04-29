import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    from eval.tenacious_bench.constants import SEGMENTS, GUARANTEE_KWS, WEIGHTS, PASS_THRESHOLD
except ImportError:
    SEGMENTS = {1: "Growth", 2: "Restructuring", 3: "Enterprise", 4: "AI"}
    GUARANTEE_KWS = ["guarantee", "#1 ranked"]
    WEIGHTS = {"segment_alignment": 0.3, "signal_grounding": 0.25, "tone_compliance": 0.2, "honesty_constraint": 0.15, "style_guide_match": 0.1}
    PASS_THRESHOLD = 0.70

# === 4-Level Failure Taxonomy ===
STYLE_VIOLATION = "STYLE_VIOLATION"           # Banned phrases, word count, template tokens
STRUCTURAL_VIOLATION = "STRUCTURAL_VIOLATION" # Multi-ask, formatting, cold PDF
REASONING_FAILURE = "REASONING_FAILURE"       # Wrong segment, AI maturity gating error
SEMANTIC_FALSEHOOD = "SEMANTIC_FALSEHOOD"     # Fabricated data, invented capacity, fake urgency


@dataclass
class ScoreResult:
    verdict: str
    composite: float
    dimensions: Dict[str, float]
    fatal_reasons: List[str]
    failure_type: Optional[str] = None  # One of the 4 taxonomy levels, or None for PASS


class ScoringEvaluator:
    """
    Automated evaluator for Tenacious-Bench (v2 — Style Guide integrated).
    Architecture: Deterministic Rule Layer + Failure Taxonomy Classification.
    
    Frozen for Act IV training — do not modify after snapshot.
    """

    def __init__(self):
        # --- Segment Detection (Reasoning layer) ---
        self.segment_heuristics = {
            1: ["growth", "scale fast", "funding", "series", "accelerate", "round", "scaling"],
            2: ["efficiency", "cost control", "reduction", "doing more with less", "freeze", "headcount", "restructuring"],
            3: ["legacy", "migration", "security", "enterprise", "stability", "compliance", "outsourcing"],
            4: ["llm", "ai infrastructure", "machine learning", "maturity", "r&d to prod", "trained model"],
        }
        
        # --- Style Guide v2: Banned phrases (Style layer) ---
        self.banned_phrases = [
            "world-class", "top talent", "a-players", "rockstar", "ninja", "wizard",
            "skyrocket", "supercharge", "10x",
            "i hope this email finds you well",
            "just following up", "circling back",
            "quick question", "quick chat",
            "synergize", "synergy", "leverage", "ecosystem",
            "game-changer", "disruptor", "paradigm shift",
            "our proprietary", "our ai-powered",
            "you'll regret", "don't miss out",
            "per my last email", "per my last",
            "our 500 employees", "our 20 years",
            "i'll keep this brief",
            "i noticed you're a",
            "gold standard",
        ]
        self.banned_regex = re.compile("|".join(re.escape(p) for p in self.banned_phrases), re.IGNORECASE)
        
        # --- Condescension patterns (Style layer) ---
        self.condescension_patterns = re.compile(
            r"(falling behind|behind the curve|you need to|you should|catch up|missing out|you are behind|your .* is behind)",
            re.IGNORECASE
        )
        
        # --- Signal entity detection (Grounding layer) ---
        self.signal_entity_regex = re.compile(
            r"(\$[\d,.]+[MBK]?|\d+%|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b|\bSeries [A-D]\b|\b\d+ (?:open |new )?(?:roles?|positions?|engineers?|hires?)\b)",
            re.IGNORECASE
        )
        
        # --- Plausibility constraint ranges (Semantic truth layer) ---
        self.funding_ranges = {
            "seed": (0.1, 5),       # $100K - $5M
            "series a": (2, 30),    # $2M - $30M
            "series b": (10, 100),  # $10M - $100M
            "series c": (30, 500),  # $30M - $500M
        }

    def evaluate_task(self, task_data: dict) -> ScoreResult:
        output = task_data.get("candidate_output", "").lower()
        output_raw = task_data.get("candidate_output", "")
        ground_truth = task_data.get("ground_truth", {})
        inferred_segment = ground_truth.get("inferred_segment")
        
        dimensions = {}
        fatal_flags = []
        failure_types_detected = []

        # ============================================================
        # LAYER 1: STYLE CHECKS (deterministic, zero-cost)
        # ============================================================
        
        # 1a. Banned Phrase Check
        banned_matches = self.banned_regex.findall(output)
        if banned_matches:
            fatal_flags.append(f"banned_phrase:{','.join(set(banned_matches))}")
            failure_types_detected.append(STYLE_VIOLATION)
        dimensions["banned_phrases"] = 0.0 if banned_matches else 1.0

        # 1b. Condescension Pattern Check
        condescension_score = 1.0
        if self.condescension_patterns.search(output):
            condescension_score = 0.3
            failure_types_detected.append(STYLE_VIOLATION)
        dimensions["tone_compliance"] = condescension_score

        # 1c. Word Count Enforcement
        word_count = len(output.split())
        email_type = task_data.get("email_type", "cold")
        word_limits = {"cold": 120, "warm": 200, "re_engagement": 100}
        max_words = word_limits.get(email_type, 120)
        
        style_score = 1.0
        if word_count > max_words:
            style_score -= 0.3
            failure_types_detected.append(STYLE_VIOLATION)
        if word_count < 20:
            style_score -= 0.2
        
        # 1d. CTA Check
        if not any(cta in output for cta in ["?", "let me know", "call", "schedule", "calendar"]):
            style_score -= 0.2
        dimensions["style_guide_match"] = max(0.0, style_score)

        # ============================================================
        # LAYER 2: STRUCTURAL CHECKS (rule-based logic)
        # ============================================================
        
        # 2a. Multi-ask detection
        ask_indicators = output.count("first,") + output.count("second,") + output.count("third,") + output.count("fourth,")
        question_marks = output.count("?")
        multi_ask = ask_indicators >= 2 or question_marks >= 4
        if multi_ask:
            fatal_flags.append("multi_ask")
            failure_types_detected.append(STRUCTURAL_VIOLATION)
        dimensions["single_ask"] = 0.0 if multi_ask else 1.0
        
        # 2b. Cold PDF attachment
        has_attachment = "[attachment" in output or "please find attached" in output
        if has_attachment:
            fatal_flags.append("cold_pdf")
            failure_types_detected.append(STRUCTURAL_VIOLATION)
        dimensions["no_attachment"] = 0.0 if has_attachment else 1.0

        # 2c. Overclaiming / Guarantees
        overclaim_score = 1.0
        for kw in GUARANTEE_KWS:
            if kw in output:
                overclaim_score = 0.0
                fatal_flags.append("overclaiming")
                failure_types_detected.append(STRUCTURAL_VIOLATION)
                break
        dimensions["overclaiming"] = overclaim_score

        # ============================================================
        # LAYER 3: REASONING CHECKS (segment alignment — D06 core)
        # ============================================================
        
        # 3a. Segment Alignment (D06 Proxy)
        segment_counts = {seg: 0 for seg in self.segment_heuristics}
        for seg, keywords in self.segment_heuristics.items():
            for kw in keywords:
                if kw in output:
                    segment_counts[seg] += 1
        
        if any(segment_counts.values()):
            predicted_segment = max(segment_counts, key=segment_counts.get)
        else:
            predicted_segment = None

        if predicted_segment is not None and inferred_segment is not None and predicted_segment != inferred_segment:
            seg_score = 0.0
            fatal_flags.append("segment_alignment")
            failure_types_detected.append(REASONING_FAILURE)
        else:
            seg_score = 1.0
        dimensions["segment_alignment"] = seg_score

        # 3b. Honesty Constraints (I03 / Policy)
        honesty_score = 1.0
        forbidden = ground_truth.get("forbidden_signals", [])
        for signal in forbidden:
            if signal.lower() in output:
                honesty_score = 0.0
                fatal_flags.append("honesty_violation")
                failure_types_detected.append(REASONING_FAILURE)
                break
        dimensions["honesty_constraint"] = honesty_score

        # ============================================================
        # LAYER 4: SEMANTIC TRUTH CHECKS (plausibility constraints)
        # ============================================================
        
        # 4a. Signal Grounding
        required = ground_truth.get("required_signals", [])
        signal_entities = self.signal_entity_regex.findall(output_raw)
        if not required:
            grounding_score = min(1.0, len(signal_entities) * 0.25) if signal_entities else 0.5
        else:
            found = sum(1 for s in required if s.lower() in output)
            grounding_score = found / len(required)
            if grounding_score == 0.0:
                failure_types_detected.append(SEMANTIC_FALSEHOOD)
        dimensions["signal_grounding"] = grounding_score

        # 4b. Funding Plausibility (cross-field consistency)
        stated_funding = ground_truth.get("stated_funding_stage")
        stated_amount = ground_truth.get("stated_funding_amount")
        if stated_funding and stated_amount:
            expected_range = self.funding_ranges.get(stated_funding.lower())
            if expected_range:
                low, high = expected_range
                if stated_amount < low or stated_amount > high:
                    fatal_flags.append("funding_plausibility")
                    failure_types_detected.append(SEMANTIC_FALSEHOOD)
                    dimensions["funding_plausibility"] = 0.0
                else:
                    dimensions["funding_plausibility"] = 1.0
        
        # 4c. Bench capacity check (if ground truth provides bench data)
        bench_available = ground_truth.get("bench_available")
        committed_count = ground_truth.get("committed_engineers")
        if bench_available is not None and committed_count is not None:
            if committed_count > bench_available:
                fatal_flags.append("bench_overcommit")
                failure_types_detected.append(SEMANTIC_FALSEHOOD)
                dimensions["bench_plausibility"] = 0.0
            else:
                dimensions["bench_plausibility"] = 1.0

        # ============================================================
        # COMPOSITE SCORING & VERDICT
        # ============================================================
        is_fatal = len(fatal_flags) > 0
        
        if is_fatal:
            composite = 0.0
        else:
            composite = (
                dimensions.get("segment_alignment", 1.0) * 0.30 +
                dimensions.get("signal_grounding", 1.0) * 0.25 +
                dimensions.get("tone_compliance", 1.0) * 0.20 +
                dimensions.get("honesty_constraint", 1.0) * 0.15 +
                dimensions.get("style_guide_match", 1.0) * 0.10
            )
        
        # Determine primary failure type (highest-severity wins)
        severity_order = [SEMANTIC_FALSEHOOD, REASONING_FAILURE, STRUCTURAL_VIOLATION, STYLE_VIOLATION]
        primary_failure = None
        for sev in severity_order:
            if sev in failure_types_detected:
                primary_failure = sev
                break
        
        if is_fatal:
            verdict = "FAIL"
        elif composite >= 0.70:
            verdict = "PASS"
        elif composite >= 0.60:
            verdict = "BORDERLINE"
        else:
            verdict = "FAIL"
        
        return ScoreResult(
            verdict=verdict,
            composite=round(composite, 2),
            dimensions={k: round(v, 2) for k, v in dimensions.items()},
            fatal_reasons=fatal_flags,
            failure_type=primary_failure
        )


def main():
    evaluator = ScoringEvaluator()
    examples_dir = Path("eval/tenacious_bench/examples")
    
    print(f"{'TASK_ID':<15} | {'VERDICT':<10} | {'FAILURE_TYPE':<22} | {'SCORE':<7} | {'FLAGS'}")
    print("-" * 110)
    
    for task_file in sorted(examples_dir.glob("*.json")):
        with open(task_file) as f:
            task = json.load(f)
        result = evaluator.evaluate_task(task)
        reasons = "; ".join(result.fatal_reasons)
        ft = result.failure_type or "-"
        print(f"{task['task_id']:<15} | {result.verdict:<10} | {ft:<22} | {result.composite:<7} | {reasons}")

if __name__ == "__main__":
    main()

