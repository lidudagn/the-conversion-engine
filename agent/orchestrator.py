"""
Multi-Channel Orchestrator
Email → SMS → Voice handoff logic.
Thread state per prospect. Anti-leakage between threads at same company.
"""

import json
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ThreadState(BaseModel):
    """Per-prospect conversation thread state."""
    prospect_name: str
    prospect_email: str
    company: str
    thread_id: str = ""
    channel: str = "email"  # email | sms | voice
    status: str = "cold"    # cold | warm | hot | booked | stalled
    turn_count: int = 0
    email_sent: bool = False
    email_replied: bool = False
    sms_sent: bool = False
    sms_replied: bool = False
    call_booked: bool = False
    last_activity: str = ""
    stalled_days: int = 0
    context_brief: Optional[str] = None


class ChannelOrchestrator:
    """
    Multi-channel flow controller.
    Email is primary. SMS for warm leads. Voice for booked calls.

    Anti-leakage: separate thread state per prospect at same company.
    """

    def __init__(self):
        self._threads: dict[str, ThreadState] = {}

    def get_or_create_thread(
        self,
        prospect_email: str,
        prospect_name: str = "",
        company: str = "",
    ) -> ThreadState:
        """Get or create a thread for a prospect."""
        if prospect_email in self._threads:
            return self._threads[prospect_email]

        import uuid
        thread = ThreadState(
            prospect_name=prospect_name,
            prospect_email=prospect_email,
            company=company,
            thread_id=str(uuid.uuid4()),
            last_activity=datetime.now().isoformat(),
        )
        self._threads[prospect_email] = thread
        return thread

    def determine_next_channel(self, thread: ThreadState) -> str:
        """Determine the next channel action based on thread state."""

        # Email is always first
        if not thread.email_sent:
            return "send_email"

        # If email replied → warm lead, offer SMS for scheduling
        if thread.email_replied and not thread.call_booked:
            if not thread.sms_sent:
                return "send_sms_scheduling"
            return "continue_email"

        # If stalled 3+ days → re-engagement email
        if thread.stalled_days >= 3 and thread.turn_count < 3:
            return "send_reengagement_email"

        # If stalled 7+ days → mark as stalled, stop
        if thread.stalled_days >= 7:
            thread.status = "stalled"
            return "stalled"

        # If call booked → voice handoff
        if thread.call_booked:
            return "voice_handoff"

        return "wait"

    def handle_reply(self, prospect_email: str, channel: str, reply_text: str) -> ThreadState:
        """Update thread when a reply is received."""
        thread = self._threads.get(prospect_email)
        if not thread:
            return self.get_or_create_thread(prospect_email)

        thread.turn_count += 1
        thread.last_activity = datetime.now().isoformat()
        thread.stalled_days = 0

        if channel == "email":
            thread.email_replied = True
            thread.status = "warm"
        elif channel == "sms":
            thread.sms_replied = True
            thread.status = "hot"

        return thread

    def mark_booked(self, prospect_email: str) -> ThreadState:
        """Mark a thread as booked for discovery call."""
        thread = self._threads.get(prospect_email)
        if thread:
            thread.call_booked = True
            thread.status = "booked"
        return thread

    def get_company_threads(self, company: str) -> list[ThreadState]:
        """Get all threads for a company (for anti-leakage checks)."""
        return [t for t in self._threads.values()
                if t.company.lower() == company.lower()]

    def check_leakage_risk(self, prospect_email: str) -> bool:
        """Check if sending to this prospect risks cross-thread leakage."""
        thread = self._threads.get(prospect_email)
        if not thread:
            return False
        company_threads = self.get_company_threads(thread.company)
        # Risk if multiple active threads at same company
        active = [t for t in company_threads if t.status not in ("stalled", "booked")]
        return len(active) > 1

    def get_all_threads(self) -> list[ThreadState]:
        return list(self._threads.values())

    def get_stalled_threads(self, days: int = 3) -> list[ThreadState]:
        return [t for t in self._threads.values() if t.stalled_days >= days]
