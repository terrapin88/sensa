"""
Trading Agent Example
=====================

Demonstrates a crypto-trading-focused agent that uses Sensa to:
  - Monitor real-time prices for BTC, ETH, and SOL
  - Detect stale price data before making decisions
  - Incorporate market news into trading signals

This is a simplified example showing the integration pattern.
In production you'd add proper risk management, order execution,
and position sizing.

pip install sensa openai
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

from sensa import SensaClient


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WATCHED_SYMBOLS = ["BTC", "ETH", "SOL"]

# If price data is older than this many seconds, skip the trading decision.
# Stale data can lead to trades based on outdated prices — a common and
# expensive bug in algo trading systems.
MAX_STALENESS_SECONDS = 30


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PriceSnapshot:
    symbol: str
    price: float
    change_24h: float  # percent
    timestamp: float    # unix epoch


@dataclass
class TradingSignal:
    symbol: str
    action: str          # "buy", "sell", or "hold"
    confidence: float    # 0.0 - 1.0
    reasoning: str


# ---------------------------------------------------------------------------
# Staleness detection
# ---------------------------------------------------------------------------

def check_staleness(prices: list[PriceSnapshot]) -> list[str]:
    """
    Check if any price data is stale.

    Returns a list of warning strings for symbols with outdated data.
    In production, stale data should block trade execution — never
    trade on prices you can't trust.
    """
    warnings = []
    now = time.time()

    for p in prices:
        age = now - p.timestamp
        if age > MAX_STALENESS_SECONDS:
            warnings.append(
                f"WARNING: {p.symbol} price is {age:.0f}s old "
                f"(threshold: {MAX_STALENESS_SECONDS}s). "
                f"Skipping trade decisions for this asset."
            )

    return warnings


# ---------------------------------------------------------------------------
# Trading agent
# ---------------------------------------------------------------------------

class CryptoTradingAgent:
    """
    A simple trading agent that uses Sensa for real-time market context
    and an LLM for signal generation.
    """

    def __init__(self, sensa_api_key: str, openai_api_key: str):
        # Configure Sensa for crypto monitoring
        self.sensa = SensaClient(
            api_key=sensa_api_key,
            channels=["time", "crypto", "news"],
            channel_config={
                "crypto": {
                    "symbols": WATCHED_SYMBOLS,
                    "include_24h_change": True,
                    "include_volume": True,
                    "include_market_cap": True,
                },
                "news": {
                    # Filter news to crypto-relevant topics
                    "categories": ["crypto", "finance", "regulation"],
                },
            },
            # Tight staleness for trading — data must be fresh
            staleness_threshold=MAX_STALENESS_SECONDS,
        )
        self.openai_api_key = openai_api_key

    async def get_market_snapshot(self) -> dict:
        """Fetch the latest market data from Sensa."""
        # aget_channel returns structured data for a single channel
        crypto_data = await self.sensa.aget_channel("crypto")
        news_data = await self.sensa.aget_channel("news")
        time_data = await self.sensa.aget_channel("time")

        return {
            "crypto": crypto_data,
            "news": news_data,
            "time": time_data,
        }

    async def parse_prices(self, crypto_data: dict) -> list[PriceSnapshot]:
        """Parse Sensa crypto channel data into PriceSnapshot objects."""
        prices = []
        for coin in crypto_data.get("prices", []):
            prices.append(PriceSnapshot(
                symbol=coin["symbol"],
                price=coin["price"],
                change_24h=coin.get("change_24h", 0.0),
                timestamp=coin.get("timestamp", time.time()),
            ))
        return prices

    async def generate_signals(
        self,
        prices: list[PriceSnapshot],
        news_context: str,
    ) -> list[TradingSignal]:
        """
        Use an LLM to analyze prices + news and generate trading signals.

        The Sensa context ensures the LLM reasons about CURRENT prices,
        not training-data prices from months ago.
        """
        from openai import AsyncOpenAI

        openai = AsyncOpenAI(api_key=self.openai_api_key)

        price_summary = "\n".join(
            f"  {p.symbol}: ${p.price:,.2f} ({p.change_24h:+.1f}% 24h)"
            for p in prices
        )

        response = await openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a crypto trading analyst. Given current prices "
                        "and news, output a JSON array of trading signals.\n"
                        "Each signal: {symbol, action, confidence, reasoning}\n"
                        "action: 'buy', 'sell', or 'hold'\n"
                        "confidence: 0.0-1.0\n"
                        "Be conservative — default to 'hold' unless there's "
                        "a clear catalyst."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Current prices:\n{price_summary}\n\n"
                        f"Recent news:\n{news_context}\n\n"
                        f"Generate signals for: {', '.join(WATCHED_SYMBOLS)}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )

        # Parse response (simplified — add proper validation in production)
        import json
        data = json.loads(response.choices[0].message.content)
        signals = []
        for s in data.get("signals", []):
            signals.append(TradingSignal(
                symbol=s["symbol"],
                action=s["action"],
                confidence=s["confidence"],
                reasoning=s["reasoning"],
            ))
        return signals

    async def run_cycle(self):
        """
        Execute one trading cycle:
        1. Fetch fresh market data via Sensa
        2. Check for stale prices
        3. Generate trading signals
        4. (In production: execute orders)
        """
        print(f"\n{'='*60}")
        print("Trading Cycle Start")
        print(f"{'='*60}")

        # Step 1: Get fresh data
        snapshot = await self.get_market_snapshot()

        # Step 2: Parse and check staleness
        prices = await self.parse_prices(snapshot["crypto"])
        stale_warnings = check_staleness(prices)

        if stale_warnings:
            for w in stale_warnings:
                print(f"  {w}")
            # Filter out stale symbols
            stale_symbols = {
                p.symbol for p in prices
                if time.time() - p.timestamp > MAX_STALENESS_SECONDS
            }
            prices = [p for p in prices if p.symbol not in stale_symbols]
            if not prices:
                print("  All price data is stale. Skipping this cycle.")
                return

        # Print current prices
        print("\nCurrent Prices:")
        for p in prices:
            print(f"  {p.symbol}: ${p.price:,.2f} ({p.change_24h:+.1f}% 24h)")

        # Step 3: Generate signals
        # Get the full context string for news
        full_context = await self.sensa.aget_context()
        signals = await self.generate_signals(prices, full_context)

        # Step 4: Display signals
        print("\nTrading Signals:")
        for s in signals:
            emoji = {"buy": "BUY", "sell": "SELL", "hold": "HOLD"}.get(s.action, "?")
            print(f"  [{emoji}] {s.symbol} (confidence: {s.confidence:.0%})")
            print(f"         {s.reasoning}")

        # Step 5: In production, you'd execute orders here
        # execute_orders(signals)


    async def run_loop(self, interval_seconds: int = 60):
        """Run trading cycles in a loop."""
        print(f"Starting trading loop (interval: {interval_seconds}s)")
        print(f"Monitoring: {', '.join(WATCHED_SYMBOLS)}")
        print(f"Staleness threshold: {MAX_STALENESS_SECONDS}s")

        while True:
            try:
                await self.run_cycle()
            except Exception as e:
                print(f"  ERROR in trading cycle: {e}")

            print(f"\nNext cycle in {interval_seconds}s...")
            await asyncio.sleep(interval_seconds)


# ---------------------------------------------------------------------------
# Standalone staleness demo (no API keys needed)
# ---------------------------------------------------------------------------

def staleness_demo():
    """
    Demonstrate staleness detection without requiring API keys.

    This shows why staleness checking is critical: imagine your agent
    sees BTC at $84,000 but that price is actually 5 minutes old.
    In a volatile market, the real price could be $82,000 — and your
    agent just made a buy decision on stale data.
    """
    print("=== Staleness Detection Demo ===\n")

    # Simulate price data at different ages
    now = time.time()
    prices = [
        PriceSnapshot("BTC", 84210.50, 2.3, now - 5),       # 5s old — fresh
        PriceSnapshot("ETH", 1812.30, -0.4, now - 15),      # 15s old — fresh
        PriceSnapshot("SOL", 142.80, 5.1, now - 120),       # 120s old — STALE
    ]

    print("Price snapshots:")
    for p in prices:
        age = now - p.timestamp
        status = "FRESH" if age <= MAX_STALENESS_SECONDS else "STALE"
        print(f"  {p.symbol}: ${p.price:,.2f} (age: {age:.0f}s) [{status}]")

    print()
    warnings = check_staleness(prices)
    if warnings:
        for w in warnings:
            print(f"  {w}")
        print("\n  Result: SOL trading decisions BLOCKED due to stale data.")
        print("  BTC and ETH can proceed — their data is fresh.")
    else:
        print("  All data is fresh. Trading can proceed for all symbols.")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # This demo runs without API keys
    staleness_demo()

    # Uncomment to run the full trading agent (requires API keys):
    # agent = CryptoTradingAgent(
    #     sensa_api_key="your-sensa-api-key",
    #     openai_api_key="your-openai-api-key",
    # )
    # asyncio.run(agent.run_loop(interval_seconds=60))
