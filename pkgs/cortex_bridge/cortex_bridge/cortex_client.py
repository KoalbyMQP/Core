"""HTTP client for Cortex control plane (localhost, no auth required)."""

import json
import urllib.request
import urllib.error
from typing import Optional


class CortexClient:
    """Thin HTTP client for the Cortex API running on localhost."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080"):
        self.base_url = base_url

    def _get(self, path: str) -> Optional[dict]:
        """Send GET request, return parsed JSON or None on error."""
        try:
            req = urllib.request.Request(f"{self.base_url}{path}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
            return None

    def _get_or_raise(self, path: str) -> dict:
        """Send GET request, raise on failure."""
        req = urllib.request.Request(f"{self.base_url}{path}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())

    def get_pending_code(self) -> Optional[dict]:
        """Get pending auth pairing code. Returns {code, expires_at} or None."""
        return self._get("/internal/auth/pending")

    def get_instances(self) -> list[dict]:
        """Get all container instances."""
        data = self._get("/instances")
        if data and "instances" in data:
            return data["instances"]
        return []

    def get_events(self, since: Optional[str] = None, event_type: Optional[str] = None,
                   limit: int = 50) -> list[dict]:
        """Get recent events from the event log."""
        params = []
        if since:
            params.append(f"since={since}")
        if event_type:
            params.append(f"type={event_type}")
        if limit:
            params.append(f"limit={limit}")
        query = "&".join(params)
        path = f"/events?{query}" if query else "/events"
        data = self._get(path)
        if data and "events" in data:
            return data["events"]
        return []

    def get_instance_logs(self, instance_id: str, tail: int = 50) -> Optional[str]:
        """Get recent logs for an instance (non-streaming)."""
        data = self._get(f"/instances/{instance_id}/logs?tail={tail}")
        return data
