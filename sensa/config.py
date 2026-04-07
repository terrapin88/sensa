"""Configuration management for Sensa."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Default staleness thresholds in minutes per channel
DEFAULT_STALENESS: Dict[str, float] = {
    "time": 60.0,
    "weather": 15.0,
    "crypto": 5.0,
    "news": 30.0,
    "sports": 2.0,
}

# Default token allocations (priority weights)
DEFAULT_TOKEN_WEIGHTS: Dict[str, float] = {
    "time": 0.10,
    "weather": 0.25,
    "crypto": 0.35,
    "news": 0.30,
    "sports": 0.40,
}


@dataclass
class SensaConfig:
    """Central configuration for a Sensa client instance."""

    channels: List[str] = field(default_factory=lambda: ["time"])
    location: str = ""
    timezone: str = "UTC"
    max_tokens: int = 200
    api_keys: Dict[str, str] = field(default_factory=dict)
    staleness_thresholds: Dict[str, float] = field(default_factory=dict)
    token_weights: Dict[str, float] = field(default_factory=dict)
    crypto_coins: List[str] = field(default_factory=lambda: ["bitcoin", "ethereum", "solana"])
    news_feeds: List[str] = field(default_factory=list)
    cache_ttl: float = 60.0  # seconds before refetching

    def get_staleness(self, channel: str) -> float:
        """Get staleness threshold in minutes for a channel."""
        return self.staleness_thresholds.get(channel, DEFAULT_STALENESS.get(channel, 15.0))

    def get_token_weight(self, channel: str) -> float:
        """Get token weight for a channel."""
        return self.token_weights.get(channel, DEFAULT_TOKEN_WEIGHTS.get(channel, 0.25))

    def get_api_key(self, service: str) -> Optional[str]:
        """Get an API key by service name, or None."""
        return self.api_keys.get(service)
