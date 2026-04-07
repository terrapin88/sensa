"""Abstract base class for all Sensa channels."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from sensa.config import SensaConfig


class BaseChannel(ABC):
    """Base class that every Sensa channel must inherit from.

    Subclasses implement ``fetch()`` to retrieve raw data and
    ``compress()`` to format it into a compact, token-efficient string.
    """

    #: Human-readable channel name (override in subclass)
    name: str = "base"

    #: Emoji prefix used in compressed output
    emoji: str = ""

    def __init__(self, config: SensaConfig) -> None:
        self.config = config

    @abstractmethod
    async def fetch(self) -> Dict[str, Any]:
        """Fetch raw data from the channel's data source.

        Returns:
            Dictionary of raw data fields.

        Raises:
            Should NOT raise — catch exceptions internally and return
            a dict with an ``"error"`` key instead.
        """
        ...

    @abstractmethod
    def compress(self, data: Dict[str, Any]) -> str:
        """Compress raw data into a compact display string.

        Args:
            data: The dict returned by ``fetch()``.

        Returns:
            A single-line string suitable for the context block.
        """
        ...

    async def get_output(self) -> str:
        """Fetch and compress in one step. Handles errors gracefully."""
        try:
            data = await self.fetch()
            if "error" in data:
                return f"{self.emoji} {self.name}: unavailable"
            return self.compress(data)
        except Exception:
            return f"{self.emoji} {self.name}: unavailable"
