"""
Cal.com Calendar Client
Books discovery calls. Attaches context brief.
Works with both self-hosted and cloud Cal.com.
"""

import json
from datetime import datetime, timedelta
from typing import Optional

import httpx
import config


class CalComClient:
    """
    Cal.com integration for booking discovery calls.
    """

    def __init__(self):
        self.api_key = config.CALCOM_API_KEY
        self.base_url = config.CALCOM_BASE_URL.rstrip("/")
        if "/v2" not in self.base_url:
            self.base_url = f"{self.base_url}/v2"
        self._active = bool(self.api_key and not self.api_key.startswith("cal_..."))
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "cal-api-version": "2024-08-13",
            "Content-Type": "application/json",
        }

    async def get_available_slots(
        self,
        event_type_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        timezone: str = "UTC",
    ) -> list[dict]:
        """Get available booking slots."""
        if not self._active:
            # Return mock slots for dry run
            today = datetime.now()
            return [
                {"time": (today + timedelta(days=d, hours=h)).isoformat(),
                 "timezone": timezone}
                for d in range(1, 4) for h in [10, 14, 16]
            ]

        start = start_date or datetime.now().strftime("%Y-%m-%d")
        end = end_date or (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/slots/available",
                    headers=self.headers,
                    params={
                        "eventTypeId": event_type_id or int(config.CALCOM_EVENT_TYPE_ID),
                        "startTime": f"{start}T00:00:00Z",
                        "endTime": f"{end}T23:59:59Z",
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # V2 structure: {"status": "success", "data": {"slots": {"date": [{"time": "..."}]}}}
                    slots_data = data.get("data", {}).get("slots", {})
                    slots = []
                    for date_key, times in slots_data.items():
                        for slot in times:
                            slots.append({"time": slot.get("time", ""), "timezone": timezone})
                    return slots
                else:
                    print(f"Cal.com API error: {resp.status_code}")
                    return []
        except Exception as e:
            print(f"Cal.com error: {e}")
            return []

    async def create_booking(
        self,
        event_type_id: Optional[int] = None,
        start_time: str = "",
        name: str = "",
        email: str = "",
        timezone: str = "UTC",
        notes: str = "",
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Create a booking (discovery call).
        Attaches context brief as notes/metadata.
        """
        booking_data = {
            "start": start_time,
            "eventTypeId": event_type_id or int(config.CALCOM_EVENT_TYPE_ID),
            "attendee": {
                "name": name,
                "email": email,
                "timeZone": timezone,
            },
            "meetingNotes": notes,
            "metadata": metadata or {},
        }

        if not self._active:
            return {
                "status": "dry_run",
                "booking": booking_data,
                "note": "Cal.com not configured — dry run",
            }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/bookings",
                    headers=self.headers,
                    json=booking_data,
                    timeout=15,
                )
                if resp.status_code in (200, 201):
                    result = resp.json().get("data", {})
                    return {
                        "status": "booked",
                        "booking_id": result.get("id"),
                        "start_time": start_time,
                        "attendee": email,
                    }
                else:
                    return {
                        "status": "error",
                        "code": resp.status_code,
                        "detail": resp.text[:200],
                    }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def cancel_booking(self, booking_id: int, reason: str = "") -> dict:
        """Cancel a booking."""
        if not self._active:
            return {"status": "dry_run", "booking_id": booking_id}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/bookings/{booking_id}/cancel",
                    headers=self.headers,
                    json={"reason": reason},
                    timeout=15,
                )
                return {"status": "cancelled" if resp.status_code == 200 else "error"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
