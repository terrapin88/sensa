#!/usr/bin/env python3
"""Standalone test for the Sensa sports channel."""

import asyncio

from sensa.config import SensaConfig
from sensa.channels.sports import SportsChannel


async def main():
    config = SensaConfig(
        channels=["sports"],
        location="Augusta, GA",
    )
    ch = SportsChannel(config)

    print("=== Fetching sports data ===\n")
    data = await ch.fetch()

    # Show raw keys for debugging
    print(f"Raw data keys: {list(data.keys())}")
    if data.get("tournament"):
        t = data["tournament"]
        print(f"Tournament: {t.get('name')} | State: {t.get('state')} | Venue: {t.get('venue_city')}")
    if data.get("leaderboard"):
        print(f"Leaderboard entries: {len(data['leaderboard'])}")
        for p in data["leaderboard"][:5]:
            print(f"  {p['pos_display']} {p['name']} ({p['score_display']})")
    if data.get("weather"):
        w = data["weather"]
        print(f"Weather: {w.get('temp_f')}°F, wind {w.get('wind_mph')}mph {w.get('wind_dir')}")
    if data.get("odds"):
        print(f"Odds entries: {len(data['odds'])}")

    print("\n=== Compressed output ===\n")
    output = await ch.get_output()
    print(output)
    print(f"\n(~{len(output.split())} words)")


if __name__ == "__main__":
    asyncio.run(main())
