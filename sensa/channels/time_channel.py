"""Time channel — date, time, timezone, and session tracking."""

from __future__ import annotations

import time
from datetime import datetime, timezone as tz
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from sensa.channels.base import BaseChannel
from sensa.config import SensaConfig


class TimeChannel(BaseChannel):
    """Provides current date/time and session duration tracking.

    Uses only the Python standard library — always works offline.
    """

    name = "time"
    emoji = "⏱"

    def __init__(self, config: SensaConfig) -> None:
        super().__init__(config)
        self._init_ts: float = time.time()
        self._last_call_ts: Optional[float] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_tz(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.config.timezone)
        except Exception:
            return ZoneInfo("UTC")

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        """Format a duration in seconds into a human-readable string."""
        m = int(seconds // 60)
        if m < 1:
            return "<1m"
        if m < 60:
            return f"{m}m"
        h = m // 60
        rm = m % 60
        return f"{h}h{rm}m" if rm else f"{h}h"

    # ------------------------------------------------------------------
    # BaseChannel interface
    # ------------------------------------------------------------------

    async def fetch(self) -> Dict[str, Any]:
        now = time.time()
        tzinfo = self._get_tz()
        dt = datetime.now(tzinfo)

        elapsed = now - self._init_ts
        since_last = (now - self._last_call_ts) if self._last_call_ts else None
        self._last_call_ts = now

        return {
            "datetime": dt,
            "timezone_name": self.config.timezone,
            "elapsed_seconds": elapsed,
            "since_last_seconds": since_last,
        }

    def compress(self, data: Dict[str, Any]) -> str:
        dt: datetime = data["datetime"]
        tz_abbr = dt.strftime("%Z") or data["timezone_name"]
        header = dt.strftime(f"%a %b %-d, %Y %-I:%M %p") + f" {tz_abbr}"

        elapsed = self._fmt_duration(data["elapsed_seconds"])
        since = data.get("since_last_seconds")
        last_part = f" | Last call: {self._fmt_duration(since)}" if since else ""

        session_line = f"{self.emoji} Session: {elapsed}{last_part}"
        return session_line, header  # Return tuple; client uses header separately

    def get_header_and_line(self, data: Dict[str, Any]):
        """Return (header_str, session_line_str)."""
        dt: datetime = data["datetime"]
        tz_abbr = dt.strftime("%Z") or data["timezone_name"]
        header = f"[SENSA — {dt.strftime('%a %b %-d, %Y %-I:%M %p')} {tz_abbr}]"

        elapsed = self._fmt_duration(data["elapsed_seconds"])
        since = data.get("since_last_seconds")
        last_part = f" | Last call: {self._fmt_duration(since)}" if since else ""
        session_line = f"{self.emoji} Session: {elapsed}{last_part}"

        return header, session_line

    async def get_output(self) -> str:
        """Override to return just the session line (header handled separately)."""
        try:
            data = await self.fetch()
            _, session_line = self.get_header_and_line(data)
            return session_line
        except Exception:
            return f"{self.emoji} time: unavailable"

    async def get_header(self) -> str:
        """Fetch and return just the header string."""
        try:
            data = await self.fetch()
            header, _ = self.get_header_and_line(data)
            return header
        except Exception:
            return "[SENSA]"
