"""
Qualification Conversation Handler
Multi-turn email thread management with bench gate enforcement.

Every bench escalation logged to outputs/bench_escalation_log.jsonl.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class QualificationState(BaseModel):
    """State tracking for a qualification thread."""
    prospect_name: str
    thread_id: str = ""
    turn_count: int = 0
    status: str = "initial"  # initial, qualifying, objection, ready_to_book, escalated
    buying_signals: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    capacity_requested: Optional[dict] = None
    bench_available: Optional[dict] = None
    last_reply: Optional[str] = None
    escalation_reason: Optional[str] = None


class QualificationHandler:
    """
    Handle multi-turn qualification conversations.
    Enforces bench gate — never over-commits capacity.
    """

    def __init__(self, bench_summary: dict, output_dir: str = "outputs"):
        self.bench_summary = bench_summary
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.escalation_log = self.output_dir / "bench_escalation_log.jsonl"

    def process_reply(
        self,
        state: QualificationState,
        reply_text: str,
        policy_decision=None,
    ) -> tuple[QualificationState, str]:
        """
        Process a prospect's reply and generate response.

        Returns:
            (updated_state, response_text)
        """
        state.turn_count += 1
        state.last_reply = reply_text
        reply_lower = reply_text.lower()

        # Detect buying signals
        buying_keywords = [
            "interested", "tell me more", "how much", "pricing",
            "timeline", "availability", "schedule", "when can",
            "let's talk", "sounds good", "worth exploring"
        ]
        for kw in buying_keywords:
            if kw in reply_lower and kw not in state.buying_signals:
                state.buying_signals.append(kw)

        # Detect objections
        objection_keywords = [
            "too expensive", "not ready", "maybe later", "already have",
            "already working with", "no budget", "not interested",
            "not a priority", "bad timing"
        ]
        for kw in objection_keywords:
            if kw in reply_lower and kw not in state.objections:
                state.objections.append(kw)

        # ─── Bench Gate Enforcement ──────────────────────────────────
        capacity_keywords = [
            "how many", "team of", "need", "engineers",
            "developers", "people", "resources"
        ]
        if any(kw in reply_lower for kw in capacity_keywords):
            # Check if they're requesting specific capacity
            requested = self._parse_capacity_request(reply_text)
            if requested:
                state.capacity_requested = requested
                bench_available = self.bench_summary.get("total_available", 0)

                requested_count = requested.get("count", 0)
                if requested_count > bench_available:
                    state.status = "escalated"
                    state.escalation_reason = "bench_exceeded"
                    self._log_escalation(state, requested_count, bench_available)
                    return state, self._escalate_to_human(state)

        # ─── Pricing Gate ────────────────────────────────────────────
        pricing_keywords = [
            "custom pricing", "negotiate", "discount", "bulk rate",
            "enterprise pricing", "volume"
        ]
        if any(kw in reply_lower for kw in pricing_keywords):
            state.status = "escalated"
            state.escalation_reason = "pricing_beyond_public"
            self._log_escalation(state, 0, 0)
            return state, self._escalate_pricing(state)

        # ─── Generate Response ───────────────────────────────────────
        if state.objections and not state.buying_signals:
            state.status = "objection"
            response = self._handle_objection(state)
        elif len(state.buying_signals) >= 2 or "schedule" in state.buying_signals:
            state.status = "ready_to_book"
            response = self._propose_booking(state)
        else:
            state.status = "qualifying"
            response = self._continue_qualification(state)

        return state, response

    def _parse_capacity_request(self, text: str) -> Optional[dict]:
        """Parse a capacity request from reply text.

        Priority order (preserve specificity first, then fallback):
          1. number + role  — highest precision, retains role type
          2. team of N      — structured idiom
          3. verb + number  — fallback only, role inferred as 'engineer'
        """
        import re

        _ROLE_NORM = {
            'engineer': 'engineer',   'engineers': 'engineer',
            'ml engineer': 'engineer', 'ml engineers': 'engineer',
            'developer': 'developer', 'developers': 'developer',
            'dev': 'developer',       'devs': 'developer',
            'people': 'general',      'person': 'general',
            'persons': 'general',     'resource': 'general',
            'resources': 'general',   'team': 'general',
        }

        lower = text.lower()

        # 1. number + up to 2 modifier words + role keyword
        #    Handles: "10 engineers", "10 ML engineers", "10 senior developers",
        #             "10 ML-engineers", "10 senior ML engineers"
        role_pat = (
            r'ml[\s\-]engineer(?:s)?'
            r'|engineer(?:s)?'
            r'|developer(?:s)?'
            r'|dev(?:s)?'
            r'|people|person(?:s)?'
            r'|resource(?:s)?'
        )
        m = re.search(rf'(\d+)\s+(?:[\w\-]+\s+){{0,2}}({role_pat})', lower)
        if m:
            raw = m.group(2).replace('-', ' ').strip()
            return {'count': int(m.group(1)), 'role_type': _ROLE_NORM.get(raw, 'engineer')}

        # 2. "team of N" idiom  →  role normalised to 'general'
        #    Handles: "team of 15", "a team of 10"
        m = re.search(r'team\s+of\s+(\d+)', lower)
        if m:
            return {'count': int(m.group(1)), 'role_type': 'general'}

        # 3. action verb + bare number (fallback — role type inferred)
        #    Handles: "can you provide 10", "send us 8", "hire 5"
        m = re.search(r'(?:provide|send|hire|onboard)\s+(\d+)', lower)
        if m:
            return {'count': int(m.group(1)), 'role_type': 'engineer'}

        return None

    def _escalate_to_human(self, state: QualificationState) -> str:
        """Generate human escalation response."""
        return (
            f"Great question — for a team of that size, I'd want to connect you "
            f"with our delivery lead who can speak to timeline and availability "
            f"specifically. Let me set that up for you. Would tomorrow or Thursday work?"
        )

    def _escalate_pricing(self, state: QualificationState) -> str:
        """Generate pricing escalation response."""
        return (
            "Absolutely — for custom pricing we'd want to loop in our engagement "
            "lead who handles that directly. I'll connect you. What's the best "
            "time for a quick call this week?"
        )

    def _handle_objection(self, state: QualificationState) -> str:
        """Handle objection with empathy."""
        return (
            "Totally understand — no pressure at all. If things change, "
            "we're here. In the meantime, I'm happy to share a quick case study "
            "from a team in a similar position — would that be useful?"
        )

    def _propose_booking(self, state: QualificationState) -> str:
        """Propose booking a discovery call."""
        return (
            "Sounds like it could be worth a quick conversation. "
            "I can send you a booking link for a 30-minute discovery call "
            "with our delivery lead — no prep needed. Would that work?"
        )

    def _continue_qualification(self, state: QualificationState) -> str:
        """Continue qualification conversation."""
        return (
            "Thanks for the response! To make sure I'm not wasting your time — "
            "what's the most pressing challenge on the engineering side right now? "
            "Happy to share what we're seeing from similar teams."
        )

    def _log_escalation(self, state: QualificationState, requested: int, available: int):
        """Log bench escalation to jsonl."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "prospect": state.prospect_name,
            "thread_id": state.thread_id,
            "reason": state.escalation_reason,
            "requested_capacity": requested,
            "bench_available": available,
            "turn_count": state.turn_count,
        }
        with open(self.escalation_log, "a") as f:
            f.write(json.dumps(entry) + "\n")
