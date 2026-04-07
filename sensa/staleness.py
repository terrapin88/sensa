"""Staleness detection engine for channel data."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ChannelSnapshot:
    """Cached snapshot of a channel's output."""
    data: str
    fetched_at: float  # time.time()


class StalenessTracker:
    """Tracks data freshness across channels and emits warnings."""

    def __init__(self, thresholds: Optional[Dict[str, float]] = None) -> None:
        """Initialize the staleness tracker.

        Args:
            thresholds: Mapping of channel name -> max age in minutes
                        before data is considered stale.
        """
        self._thresholds: Dict[str, float] = thresholds or {}
        self._snapshots: Dict[str, ChannelSnapshot] = {}

    def set_threshold(self, channel: str, minutes: float) -> None:
        """Set staleness threshold for a channel."""
        self._thresholds[channel] = minutes

    def record(self, channel: str, data: str) -> None:
        """Record a fresh data fetch for a channel."""
        self._snapshots[channel] = ChannelSnapshot(data=data, fetched_at=time.time())

    def get_cached(self, channel: str) -> Optional[str]:
        """Return cached data for a channel, or None."""
        snap = self._snapshots.get(channel)
        return snap.data if snap else None

    def age_minutes(self, channel: str) -> Optional[float]:
        """Return age of cached data in minutes, or None if no data."""
        snap = self._snapshots.get(channel)
        if snap is None:
            return None
        return (time.time() - snap.fetched_at) / 60.0

    def is_stale(self, channel: str) -> bool:
        """Check if a channel's data exceeds its staleness threshold."""
        age = self.age_minutes(channel)
        if age is None:
            return False
        threshold = self._thresholds.get(channel, 15.0)
        return age > threshold

    def detect_stale(self, channels: List[str]) -> List[str]:
        """Detect all stale channels and return human-readable warnings.

        Returns:
            List of warning strings for channels that are stale.
        """
        warnings: List[str] = []
        for ch in channels:
            if self.is_stale(ch):
                age = self.age_minutes(ch)
                threshold = self._thresholds.get(ch, 15.0)
                if age is not None:
                    warnings.append(
                        f"⚠ STALE: {ch.capitalize()} data is "
                        f"{int(age)} min old (threshold: {int(threshold)} min)"
                    )
        return warnings

    def format_warnings(self, channels: List[str]) -> str:
        """Return staleness warnings as a single string (may be empty)."""
        warnings = self.detect_stale(channels)
        return "\n".join(warnings)
