"""Weather channel — temperature, conditions, wind via wttr.in."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import aiohttp

from sensa.channels.base import BaseChannel
from sensa.config import SensaConfig


class WeatherChannel(BaseChannel):
    """Current weather conditions using wttr.in (free, no API key).

    Falls back to OpenWeatherMap if an API key is provided in config.
    """

    name = "weather"
    emoji = "🌤"

    async def fetch(self) -> Dict[str, Any]:
        location = self.config.location or "New York"

        # Try OpenWeatherMap first if key is available
        owm_key = self.config.get_api_key("openweathermap")
        if owm_key:
            result = await self._fetch_owm(location, owm_key)
            if "error" not in result:
                return result

        # Default: wttr.in
        return await self._fetch_wttr(location)

    async def _fetch_wttr(self, location: str) -> Dict[str, Any]:
        """Fetch weather from wttr.in JSON API."""
        url = f"https://wttr.in/{location}?format=j1"
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=8)
            ) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return {"error": f"wttr.in HTTP {resp.status}"}
                    raw = await resp.json(content_type=None)

            current = raw.get("current_condition", [{}])[0]
            return {
                "location": location,
                "temp_f": current.get("temp_F", "?"),
                "temp_c": current.get("temp_C", "?"),
                "condition": current.get("weatherDesc", [{}])[0].get("value", "unknown"),
                "wind_mph": current.get("windspeedMiles", "?"),
                "humidity": current.get("humidity", "?"),
            }
        except Exception as exc:
            return {"error": str(exc)}

    async def _fetch_owm(self, location: str, api_key: str) -> Dict[str, Any]:
        """Fetch weather from OpenWeatherMap."""
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={location}&appid={api_key}&units=imperial"
        )
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=8)
            ) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return {"error": f"OWM HTTP {resp.status}"}
                    raw = await resp.json()

            main = raw.get("main", {})
            wind = raw.get("wind", {})
            weather = raw.get("weather", [{}])[0]
            return {
                "location": location,
                "temp_f": str(int(main.get("temp", 0))),
                "temp_c": str(int((main.get("temp", 32) - 32) * 5 / 9)),
                "condition": weather.get("description", "unknown"),
                "wind_mph": str(int(wind.get("speed", 0))),
                "humidity": str(main.get("humidity", "?")),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def compress(self, data: Dict[str, Any]) -> str:
        loc = data.get("location", "?")
        temp = data.get("temp_f", "?")
        cond = data.get("condition", "unknown").lower()
        wind = data.get("wind_mph", "?")
        return f"{self.emoji} {loc}: {temp}°F, {cond}, wind {wind}mph"
