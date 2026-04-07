"""SensaClient — main entry point for the Sensa library."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from sensa.channels import CHANNEL_REGISTRY, BaseChannel
from sensa.channels.time_channel import TimeChannel
from sensa.compression import compress_context, count_tokens
from sensa.config import SensaConfig, DEFAULT_TOKEN_WEIGHTS
from sensa.staleness import StalenessTracker


class SensaClient:
    """Main Sensa client — assembles channel data into a compact context string.

    Usage::

        client = SensaClient(
            channels=["time", "weather", "crypto", "news"],
            location="Austin, TX",
            timezone="America/Chicago",
        )
        context = await client.get_context()

    Or synchronously::

        context = client.get_context_sync()
    """

    def __init__(
        self,
        channels: Optional[List[str]] = None,
        location: str = "",
        timezone: str = "UTC",
        max_tokens: int = 200,
        api_keys: Optional[Dict[str, str]] = None,
        staleness_thresholds: Optional[Dict[str, float]] = None,
        token_weights: Optional[Dict[str, float]] = None,
        crypto_coins: Optional[List[str]] = None,
        news_feeds: Optional[List[str]] = None,
    ) -> None:
        self.config = SensaConfig(
            channels=channels or ["time"],
            location=location,
            timezone=timezone,
            max_tokens=max_tokens,
            api_keys=api_keys or {},
            staleness_thresholds=staleness_thresholds or {},
            token_weights=token_weights or {},
            crypto_coins=crypto_coins or ["bitcoin", "ethereum", "solana"],
            news_feeds=news_feeds or [],
        )

        # Initialize staleness tracker
        self._staleness = StalenessTracker(
            thresholds={
                ch: self.config.get_staleness(ch)
                for ch in self.config.channels
            }
        )

        # Instantiate channel objects
        self._channel_instances: Dict[str, BaseChannel] = {}
        for ch_name in self.config.channels:
            cls = CHANNEL_REGISTRY.get(ch_name)
            if cls is not None:
                self._channel_instances[ch_name] = cls(self.config)

    async def get_context(self) -> str:
        """Fetch all channel data and return a compressed context string.

        This is the primary async API. All channels are fetched
        concurrently via asyncio.gather.
        """
        channel_names = list(self._channel_instances.keys())

        # Build header from time channel
        header = "[SENSA]"
        time_ch = self._channel_instances.get("time")
        if isinstance(time_ch, TimeChannel):
            header = await time_ch.get_header()

        # Fetch all channels concurrently
        async def _fetch_one(name: str, ch: BaseChannel) -> tuple:
            output = await ch.get_output()
            self._staleness.record(name, output)
            return name, output

        results = await asyncio.gather(
            *[_fetch_one(n, c) for n, c in self._channel_instances.items()],
            return_exceptions=True,
        )

        channel_outputs: Dict[str, str] = {}
        for r in results:
            if isinstance(r, Exception):
                continue
            name, output = r
            if output:
                channel_outputs[name] = output

        # Staleness warnings
        stale_warnings = self._staleness.format_warnings(channel_names)

        # Token weights
        weights = {
            ch: self.config.get_token_weight(ch) for ch in channel_names
        }

        # Compress and return
        return compress_context(
            channel_outputs=channel_outputs,
            channel_order=channel_names,
            token_weights=weights,
            max_tokens=self.config.max_tokens,
            header=header,
            staleness_warnings=stale_warnings,
        )

    def get_context_sync(self) -> str:
        """Synchronous wrapper around :meth:`get_context`.

        Creates a new event loop if none is running, or uses
        ``asyncio.run`` for simplicity.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside an existing async context (e.g. Jupyter).
            # Create a new thread to avoid blocking the loop.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, self.get_context())
                return future.result(timeout=30)
        else:
            return asyncio.run(self.get_context())
