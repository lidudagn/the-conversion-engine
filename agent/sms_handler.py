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

        import time
        last_error = None
        for attempt in range(3):
            try:
                response = self._client.send(
                    message=message[:160],
                    recipients=[actual_to],
                    sender_id=sender_id,
                )
                result["at_response"] = str(response)
                at_recipients = []
                if isinstance(response, dict):
                    at_recipients = response.get("SMSMessageData", {}).get("Recipients", [])
                at_status = at_recipients[0].get("status", "") if at_recipients else ""
                if at_status in ("Success", ""):
                    result["status"] = "sent"
                else:
                    result["status"] = "at_sandbox_queued"
                    result["at_status"] = at_status
                    result["note"] = "AT sandbox: message queued; status reflects sandbox limits not delivery failure"
                return result
            except Exception as e:
                last_error = e
                if attempt < 2:
                    time.sleep(2 ** attempt)  # 1s, 2s backoff

        result["status"] = "error"
        result["error"] = str(last_error)
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
