"""Crypto channel — prices and 24h change via CoinGecko free API."""

from __future__ import annotations

from typing import Any, Dict, List

import aiohttp

from sensa.channels.base import BaseChannel
from sensa.config import SensaConfig

# Mapping of CoinGecko IDs to ticker symbols
_TICKER_MAP = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "dogecoin": "DOGE",
    "cardano": "ADA",
    "ripple": "XRP",
}


class CryptoChannel(BaseChannel):
    """Cryptocurrency prices using CoinGecko's free public API."""

    name = "crypto"
    emoji = "📈"

    async def fetch(self) -> Dict[str, Any]:
        coins = self.config.crypto_coins or ["bitcoin", "ethereum", "solana"]
        ids_param = ",".join(coins)
        url = (
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={ids_param}&vs_currencies=usd"
            f"&include_24hr_change=true"
        )

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get(url) as resp:
                    if resp.status == 429:
                        return {"error": "rate limited"}
                    if resp.status != 200:
                        return {"error": f"CoinGecko HTTP {resp.status}"}
                    raw = await resp.json()

            results: List[Dict[str, Any]] = []
            for coin_id in coins:
                coin_data = raw.get(coin_id, {})
                price = coin_data.get("usd")
                change = coin_data.get("usd_24h_change")
                if price is not None:
                    results.append({
                        "id": coin_id,
                        "ticker": _TICKER_MAP.get(coin_id, coin_id.upper()[:4]),
                        "price": price,
                        "change_24h": change,
                    })

            return {"coins": results}
        except Exception as exc:
            return {"error": str(exc)}

    def compress(self, data: Dict[str, Any]) -> str:
        coins = data.get("coins", [])
        if not coins:
            return f"{self.emoji} crypto: no data"

        parts: List[str] = []
        for c in coins:
            price = c["price"]
            # Format price nicely
            if price >= 1000:
                price_str = f"${price:,.0f}"
            elif price >= 1:
                price_str = f"${price:,.2f}"
            else:
                price_str = f"${price:.4f}"

            change = c.get("change_24h")
            if change is not None:
                sign = "+" if change >= 0 else ""
                change_str = f" ({sign}{change:.1f}%)"
            else:
                change_str = ""

            parts.append(f"{c['ticker']}: {price_str}{change_str}")

        return f"{self.emoji} " + " | ".join(parts)
