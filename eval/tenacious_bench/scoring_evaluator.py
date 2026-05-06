import argparse
import json
import re
import textwrap
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
    diagnostics: Dict[str, Any] = field(default_factory=dict)


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

    def _validate_task(self, task_data: dict) -> None:
        """Raise ValueError with a descriptive message if task_data is malformed."""
        if not isinstance(task_data, dict):
            raise ValueError(f"task_data must be a dict, got {type(task_data).__name__}")

        task_id = task_data.get("task_id", "<unknown>")

        output = task_data.get("candidate_output")
        if output is None:
            raise ValueError(f"[{task_id}] Missing required field: 'candidate_output'")
        if not isinstance(output, str):
            raise ValueError(f"[{task_id}] 'candidate_output' must be a str, got {type(output).__name__}")

        gt = task_data.get("ground_truth")
        if gt is not None and not isinstance(gt, dict):
            raise ValueError(f"[{task_id}] 'ground_truth' must be a dict, got {type(gt).__name__}")

        if gt:
            seg = gt.get("inferred_segment")
            if seg is not None and not isinstance(seg, int):
                raise ValueError(f"[{task_id}] 'ground_truth.inferred_segment' must be an int, got {type(seg).__name__}")
            if seg is not None and seg not in (1, 2, 3, 4):
                raise ValueError(f"[{task_id}] 'ground_truth.inferred_segment' must be 1–4, got {seg}")

            for list_field in ("forbidden_signals", "required_signals"):
                val = gt.get(list_field)
                if val is not None and not isinstance(val, list):
                    raise ValueError(f"[{task_id}] 'ground_truth.{list_field}' must be a list, got {type(val).__name__}")

    def evaluate_task(self, task_data: dict) -> ScoreResult:
        self._validate_task(task_data)

        output = task_data.get("candidate_output", "").lower()
        output_raw = task_data.get("candidate_output", "")
        ground_truth = task_data.get("ground_truth", {})
        inferred_segment = ground_truth.get("inferred_segment")
        
        dimensions = {}
        fatal_flags = []
        failure_types_detected = []
        diag: Dict[str, Any] = {}

        # ============================================================
        # LAYER 1: STYLE CHECKS (deterministic, zero-cost)
        # ============================================================

        # 1a. Banned Phrase Check
        # Calibration: 1.0 = Clean. 0.0 = Contains 1+ banned phrases (e.g. 'ninja', 'supercharge').
        banned_matches = self.banned_regex.findall(output)
        if banned_matches:
            fatal_flags.append(f"banned_phrase:{','.join(set(banned_matches))}")
            failure_types_detected.append(STYLE_VIOLATION)
        dimensions["banned_phrases"] = 0.0 if banned_matches else 1.0
        diag["banned_matches"] = list(set(banned_matches))

        # 1b. Condescension Pattern Check
        # Calibration: 1.0 = Professional/Equal footing. 0.3 = Uses condescending 'falling behind' phrases.
        condescension_score = 1.0
        condescension_match = self.condescension_patterns.search(output)
        if condescension_match:
            condescension_score = 0.3
            failure_types_detected.append(STYLE_VIOLATION)
        dimensions["tone_compliance"] = condescension_score
        diag["condescension_match"] = condescension_match.group(0) if condescension_match else None

        # 1c. Word Count Enforcement
        word_count = len(output.split())
        email_type = task_data.get("email_type", "cold")
        word_limits = {"cold": 120, "warm": 200, "re_engagement": 100}
        max_words = word_limits.get(email_type, 120)
        diag["word_count"] = word_count
        diag["word_limit"] = max_words
        diag["email_type"] = email_type

        style_score = 1.0
        style_deductions = []
        if word_count > max_words:
            style_score -= 0.3
            style_deductions.append(f"over word limit ({word_count} > {max_words}): −0.30")
            failure_types_detected.append(STYLE_VIOLATION)
        if word_count < 20:
            style_score -= 0.2
            style_deductions.append("too short (<20 words): −0.20")

        # 1d. CTA Check
        cta_keywords = ["?", "let me know", "call", "schedule", "calendar"]
        cta_found = any(cta in output for cta in cta_keywords)
        if not cta_found:
            style_score -= 0.2
            style_deductions.append("no CTA detected: −0.20")
        dimensions["style_guide_match"] = max(0.0, style_score)
        diag["cta_found"] = cta_found
        diag["style_deductions"] = style_deductions

        # ============================================================
        # LAYER 2: STRUCTURAL CHECKS (rule-based logic)
        # ============================================================

        # 2a. Multi-ask detection
        # Calibration: 1.0 = Clean single call to action. 0.0 = Cluttered with multiple asks (>1 'first/second' or >3 '?')
        ask_indicators = output.count("first,") + output.count("second,") + output.count("third,") + output.count("fourth,")
        question_marks = output.count("?")
        multi_ask = ask_indicators >= 2 or question_marks >= 4
        if multi_ask:
            fatal_flags.append("multi_ask")
            failure_types_detected.append(STRUCTURAL_VIOLATION)
        dimensions["single_ask"] = 0.0 if multi_ask else 1.0
        diag["ask_indicators"] = ask_indicators
        diag["question_marks"] = question_marks

        # 2b. Cold PDF attachment
        has_attachment = "[attachment" in output or "please find attached" in output
        if has_attachment:
            fatal_flags.append("cold_pdf")
            failure_types_detected.append(STRUCTURAL_VIOLATION)
        dimensions["no_attachment"] = 0.0 if has_attachment else 1.0

        # 2c. Overclaiming / Guarantees
        # Calibration: 1.0 = Measured claims. 0.0 = Uses forbidden 'guarantee' or '#1 ranked' overclaims.
        overclaim_score = 1.0
        overclaim_kw = None
        for kw in GUARANTEE_KWS:
            if kw in output:
                overclaim_score = 0.0
                overclaim_kw = kw
                fatal_flags.append("overclaiming")
                failure_types_detected.append(STRUCTURAL_VIOLATION)
                break
        dimensions["overclaiming"] = overclaim_score
        diag["overclaim_kw"] = overclaim_kw

        # ============================================================
        # LAYER 3: REASONING CHECKS (segment alignment — D06 core)
        # ============================================================

        # 3a. Segment Alignment (D06 Proxy)
        # Calibration: 1.0 = Matches ground truth inferred segment. 0.0 = Target segment mismatch (fatal).
        segment_counts = {seg: 0 for seg in self.segment_heuristics}
        segment_kw_hits: Dict[int, List[str]] = {seg: [] for seg in self.segment_heuristics}
        for seg, keywords in self.segment_heuristics.items():
            for kw in keywords:
                if kw in output:
                    segment_counts[seg] += 1
                    segment_kw_hits[seg].append(kw)

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
        diag["segment_counts"] = segment_counts
        diag["segment_kw_hits"] = segment_kw_hits
        diag["predicted_segment"] = predicted_segment
        diag["inferred_segment"] = inferred_segment

        # 3b. Honesty Constraints (I03 / Policy)
        # Calibration: 1.0 = Clean. 0.0 = Exposed forbidden signal (e.g. non-public layoff news).
        honesty_score = 1.0
        forbidden = ground_truth.get("forbidden_signals", [])
        forbidden_hit = None
        for signal in forbidden:
            if signal.lower() in output:
                honesty_score = 0.0
                forbidden_hit = signal
                fatal_flags.append("honesty_violation")
                failure_types_detected.append(REASONING_FAILURE)
                break
        dimensions["honesty_constraint"] = honesty_score
        diag["forbidden_signals"] = forbidden
        diag["forbidden_hit"] = forbidden_hit

        # ============================================================
        # LAYER 4: SEMANTIC TRUTH CHECKS (plausibility constraints)
        # ============================================================

        # 4a. Signal Grounding
        # Calibration: 1.0 = All required signals mentioned. Fractions (e.g. 0.5) if partially hit. 0.0 = Missed entirely.
        required = ground_truth.get("required_signals", [])
        signal_entities = self.signal_entity_regex.findall(output_raw)
        if not required:
            grounding_score = min(1.0, len(signal_entities) * 0.25) if signal_entities else 0.5
            found_required = None
        else:
            found_required = [s for s in required if s.lower() in output]
            found = len(found_required)
            grounding_score = found / len(required)
            if grounding_score == 0.0:
                failure_types_detected.append(SEMANTIC_FALSEHOOD)
        dimensions["signal_grounding"] = grounding_score
        diag["required_signals"] = required
        diag["signal_entities"] = signal_entities
        diag["found_required"] = found_required

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
            failure_type=primary_failure,
            diagnostics=diag,
        )


SEG_NAMES = {1: "Growth", 2: "Restructuring", 3: "Enterprise", 4: "AI"}
W = 56  # box width


def _box(title: str) -> str:
    return f"\n{'═' * W}\n{title}\n{'═' * W}"


def _rule() -> str:
    return "─" * W


def _dim_line(name: str, score: float, note: str = "") -> str:
    note_str = f"  {note}" if note else ""
    return f"  {name:<22} {score:.2f}{note_str}"


def print_verbose_report(task_data: dict, result: ScoreResult) -> None:
    d = result.diagnostics
    task_id = task_data.get("task_id", "?")
    category = task_data.get("category", "?")
    difficulty = task_data.get("difficulty", "?")
    mode = task_data.get("authoring_mode", "?")
    gt = task_data.get("ground_truth", {})
    inp = task_data.get("input", {})

    print(_box(f"TENACIOUS-BENCH  —  END-TO-END SCORING TRACE\n"
               f"Task : {task_id}  |  {category} / {difficulty} / {mode}"))

    # --- INPUT ---
    print("\nINPUT")
    brief = inp.get("hiring_signal_brief", {})
    if brief:
        prospect = brief.get("prospect_name", "—")
        funding = brief.get("funding", {})
        print(f"  Prospect  : {prospect}")
        if funding:
            amt = funding.get('total_usd', '')
            amt_fmt = f"${amt/1_000_000:.0f}M" if isinstance(amt, (int, float)) else str(amt)
            print(f"  Funding   : {amt_fmt} {funding.get('type', '')}  ({funding.get('date', '')})")
    seg_num = gt.get("inferred_segment")
    if seg_num:
        print(f"  GT Segment: {seg_num} — {SEG_NAMES.get(seg_num, '?')}")

    # --- CANDIDATE OUTPUT ---
    output_raw = task_data.get("candidate_output", "")
    word_count = d.get("word_count", len(output_raw.split()))
    print(f"\nCANDIDATE OUTPUT  ({word_count} words)")
    wrapped = textwrap.fill(f'"{output_raw}"', width=W - 2,
                            initial_indent="  ", subsequent_indent="   ")
    print(wrapped)

    # --- LAYER 1 ---
    print(f"\n{_rule()}")
    print("LAYER 1 — STYLE")
    banned = d.get("banned_matches", [])
    print(_dim_line("banned_phrases", result.dimensions.get("banned_phrases", 1.0),
                    f"FATAL: {banned}" if banned else "clean"))
    cond = d.get("condescension_match")
    print(_dim_line("tone_compliance", result.dimensions.get("tone_compliance", 1.0),
                    f"WARN: \"{cond}\"" if cond else "no condescension"))
    sg = result.dimensions.get("style_guide_match", 1.0)
    deductions = d.get("style_deductions", [])
    limit = d.get("word_limit", 120)
    etype = d.get("email_type", "cold")
    base_note = f"word count: {word_count}/{limit} ({etype})"
    if deductions:
        print(_dim_line("style_guide_match", sg, base_note))
        for ded in deductions:
            print(f"    {'':22} WARN: {ded}")
    else:
        print(_dim_line("style_guide_match", sg, f"{base_note}  ✓  CTA present"))

    # --- LAYER 2 ---
    print(f"\n{_rule()}")
    print("LAYER 2 — STRUCTURAL")
    qm = d.get("question_marks", 0)
    ai = d.get("ask_indicators", 0)
    print(_dim_line("single_ask", result.dimensions.get("single_ask", 1.0),
                    f"FATAL: multi-ask ({qm} '?', {ai} list markers)" if result.dimensions.get("single_ask", 1.0) == 0.0
                    else f"{qm} question mark(s), {ai} list marker(s)"))
    print(_dim_line("no_attachment", result.dimensions.get("no_attachment", 1.0),
                    "FATAL: PDF attached" if result.dimensions.get("no_attachment", 1.0) == 0.0 else "no attachment"))
    oc_kw = d.get("overclaim_kw")
    print(_dim_line("overclaiming", result.dimensions.get("overclaiming", 1.0),
                    f"FATAL: \"{oc_kw}\"" if oc_kw else "no guarantee language"))

    # --- LAYER 3 ---
    print(f"\n{_rule()}")
    print("LAYER 3 — REASONING")
    pred = d.get("predicted_segment")
    gt_seg = d.get("inferred_segment")
    kw_hits = d.get("segment_kw_hits", {})
    seg_score = result.dimensions.get("segment_alignment", 1.0)
    if pred is not None:
        hit_kws = kw_hits.get(pred, [])
        match_sym = "✓" if seg_score == 1.0 else "✗"
        note = (f"predicted Seg{pred} ({SEG_NAMES.get(pred,'?')}) {match_sym}  "
                f"gt=Seg{gt_seg}  kws={hit_kws}")
    else:
        note = "no segment keywords matched — pass-through"
    print(_dim_line("segment_alignment", seg_score,
                    f"FATAL: {note}" if seg_score == 0.0 else note))

    forb_hit = d.get("forbidden_hit")
    forb_all = d.get("forbidden_signals", [])
    forb_note = (f"FATAL: leaked \"{forb_hit}\"" if forb_hit
                 else f"checked {len(forb_all)} signal(s)  clean" if forb_all
                 else "no forbidden signals defined")
    print(_dim_line("honesty_constraint", result.dimensions.get("honesty_constraint", 1.0), forb_note))

    # --- LAYER 4 ---
    print(f"\n{_rule()}")
    print("LAYER 4 — SEMANTIC TRUTH")
    req = d.get("required_signals", [])
    entities = d.get("signal_entities", [])
    found_req = d.get("found_required")
    gs = result.dimensions.get("signal_grounding", 0.0)
    if req:
        hit_count = len(found_req) if found_req else 0
        grounding_note = f"{hit_count}/{len(req)} required signals found: {found_req or []}"
    else:
        grounding_note = (f"{len(entities)} entities found: {entities}  →  "
                          f"{len(entities)}×0.25 = {gs:.2f}")
    print(_dim_line("signal_grounding", gs, grounding_note))

    # --- COMPOSITE ---
    print(f"\n{_rule()}")
    print("COMPOSITE CALCULATION")
    weights = [
        ("segment_alignment",  0.30),
        ("signal_grounding",   0.25),
        ("tone_compliance",    0.20),
        ("honesty_constraint", 0.15),
        ("style_guide_match",  0.10),
    ]
    running = 0.0
    for dim, w in weights:
        v = result.dimensions.get(dim, 1.0)
        contrib = v * w
        running += contrib
        print(f"  {dim:<22}  {v:.2f} × {w:.2f} = {contrib:.3f}")
    print(f"  {'':22}          {'─' * 5}")
    if result.fatal_reasons:
        print(f"  {'FATAL FLAGS — zeroed':22}          0.000")
    else:
        print(f"  {'COMPOSITE':22}          {running:.3f}  →  {result.composite:.2f}")

    # --- VERDICT ---
    print(f"\n{_rule()}")
    flags_str = ", ".join(result.fatal_reasons) if result.fatal_reasons else "none"
    print(f"  FATAL FLAGS   {flags_str}")
    verdict_sym = "✓" if result.verdict == "PASS" else "✗"
    ft = result.failure_type or "—"
    print(f"  VERDICT       {result.verdict}  {verdict_sym}  "
          f"(composite={result.composite:.2f}, threshold≥{PASS_THRESHOLD:.2f}, type={ft})")
    print(f"{'═' * W}\n")


def main():
    parser = argparse.ArgumentParser(description="Tenacious-Bench scoring evaluator")
    parser.add_argument(
        "--task",
        metavar="TASK_ID",
        help="Score a single task end-to-end with full layer trace (e.g. TB-PASS-001)",
    )
    args = parser.parse_args()

    evaluator = ScoringEvaluator()
    examples_dir = Path("eval/tenacious_bench/examples")

    if args.task:
        task_file = examples_dir / f"{args.task.lower().replace('-', '_')}.json"
        if not task_file.exists():
            # fallback: search by task_id field
            task_file = next(
                (f for f in examples_dir.glob("*.json")
                 if json.loads(f.read_text()).get("task_id") == args.task),
                None,
            )
        if task_file is None:
            print(f"ERROR: task '{args.task}' not found in {examples_dir}")
            return
        with open(task_file) as f:
            task = json.load(f)
        result = evaluator.evaluate_task(task)
        print_verbose_report(task, result)
        return

    # Default: summary table for all examples
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

