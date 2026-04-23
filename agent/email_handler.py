"""
Email Handler — Resend Integration
All outbound routes through kill-switch.
Reply webhook consumed by qualifier agent.
"""

import json
from datetime import datetime
from typing import Optional

import config


class EmailHandler:
    """
    Send and receive emails via Resend.
    Kill-switch routes all outbound to staff sink.
    """

    def __init__(self):
        self.api_key = config.RESEND_API_KEY
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize Resend client."""
        try:
            import resend
            if self.api_key:
                resend.api_key = self.api_key
                self._client = resend
        except ImportError:
            print("Warning: resend package not available")

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        tags: Optional[dict] = None,
    ) -> dict:
        """
        Send an email via Resend.
        When kill-switch is ON, redirects to sink address.
        """
        # Kill-switch enforcement
        actual_to = config.SINK_EMAIL if config.KILL_SWITCH else to_email

        result = {
            "to": actual_to,
            "original_to": to_email,
            "subject": subject,
            "timestamp": datetime.now().isoformat(),
            "kill_switch": config.KILL_SWITCH,
            "status": "pending",
        }

        if not self._client:
            result["status"] = "dry_run"
            result["note"] = "No Resend client available — dry run"
            return result

        try:
            params = {
                "from": from_email or config.RESEND_FROM_EMAIL,
                "to": [actual_to],
                "subject": f"[DRAFT] {subject}" if config.KILL_SWITCH else subject,
                "text": body,
            }
            if reply_to:
                params["reply_to"] = reply_to
            if tags:
                params["tags"] = [{"name": k, "value": str(v)} for k, v in tags.items()]

            response = self._client.Emails.send(params)
            result["status"] = "sent"
            result["resend_id"] = getattr(response, "id", str(response))
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def process_webhook(self, payload: dict) -> dict:
        """
        Process a Resend webhook (reply received).
        Returns parsed reply data for the qualifier agent.
        """
        event_type = payload.get("type", "")
        data = payload.get("data", {})

        return {
            "event_type": event_type,
            "from": data.get("from", ""),
            "to": data.get("to", []),
            "subject": data.get("subject", ""),
            "text": data.get("text", ""),
            "timestamp": datetime.now().isoformat(),
        }
