"""
SMS Handler — Africa's Talking Integration
Secondary channel for warm leads who prefer SMS for scheduling.
Kill-switch routes to sink.
"""

import json
from datetime import datetime
from typing import Optional

import config


class SMSHandler:
    """
    Africa's Talking SMS integration.
    Used only for warm leads (post-email-reply) for scheduling coordination.
    """

    def __init__(self):
        self.api_key = config.AFRICASTALKING_API_KEY
        self.username = config.AFRICASTALKING_USERNAME
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize Africa's Talking SDK."""
        try:
            import africastalking
            if self.api_key:
                africastalking.initialize(self.username, self.api_key)
                self._client = africastalking.SMS
        except ImportError:
            print("Warning: africastalking package not available")
        except Exception as e:
            print(f"Warning: Africa's Talking init failed: {e}")

    def send_sms(
        self,
        to_number: str,
        message: str,
        sender_id: Optional[str] = None,
    ) -> dict:
        """
        Send SMS. Kill-switch routes to sink number.
        Only used for warm leads (scheduling after email reply).
        """
        actual_to = config.SINK_SMS if config.KILL_SWITCH else to_number

        result = {
            "to": actual_to,
            "original_to": to_number,
            "message": message[:160],  # SMS length limit
            "timestamp": datetime.now().isoformat(),
            "kill_switch": config.KILL_SWITCH,
            "status": "pending",
        }

        if not self._client:
            result["status"] = "dry_run"
            result["note"] = "No AT client available — dry run"
            return result

        try:
            response = self._client.send(
                message=message[:160],
                recipients=[actual_to],
                sender_id=sender_id,
            )
            result["status"] = "sent"
            result["at_response"] = str(response)
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def process_webhook(self, payload: dict) -> dict:
        """Process an inbound SMS webhook from Africa's Talking."""
        return {
            "from": payload.get("from", ""),
            "to": payload.get("to", ""),
            "text": payload.get("text", ""),
            "date": payload.get("date", ""),
            "id": payload.get("id", ""),
            "timestamp": datetime.now().isoformat(),
        }
