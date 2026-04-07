"""Sports channel — golf leaderboards, venue weather, and odds for DFS/betting."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import aiohttp

from sensa.channels.base import BaseChannel
from sensa.config import SensaConfig


# ESPN public API base
_ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/golf"

# Wind direction degrees to compass
_WIND_DIR = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def _deg_to_compass(deg: float) -> str:
    idx = int((deg + 11.25) / 22.5) % 16
    return _WIND_DIR[idx]


def _shorten_name(full_name: str) -> str:
    """'Scottie Scheffler' -> 'S. Scheffler'"""
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {parts[-1]}"
    return full_name


def _format_score(score: int) -> str:
    if score == 0:
        return "E"
    return f"{score:+d}" if score else "E"


class SportsChannel(BaseChannel):
    """Golf tournament data for DFS and sports betting context.

    Uses ESPN public APIs (no key), wttr.in for venue weather,
    and optionally the-odds-api.com for betting lines.
    """

    name = "sports"
    emoji = "📊"

    # Simple in-memory cache
    _cache: Dict[str, Any] = {}
    _cache_ts: Dict[str, float] = {}
    _CACHE_TTL = 60  # seconds

    def __init__(self, config: SensaConfig) -> None:
        super().__init__(config)
        self.sport = getattr(config, "sport", "golf")
        self.tournament = getattr(config, "tournament", "pga")
        self.include_weather = getattr(config, "include_weather", True)
        self.include_odds = getattr(config, "include_odds", True)
        self.top_n = getattr(config, "top_n_leaderboard", 5)
        self.odds_api_key = config.get_api_key("odds") or ""

    def _cached(self, key: str) -> Optional[Any]:
        ts = self._cache_ts.get(key)
        if ts and (time.time() - ts) < self._CACHE_TTL:
            return self._cache.get(key)
        return None

    def _set_cache(self, key: str, val: Any) -> None:
        self._cache[key] = val
        self._cache_ts[key] = time.time()

    async def _http_get_json(self, url: str, timeout: int = 10) -> Optional[Dict]:
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None
                    return await resp.json(content_type=None)
        except Exception:
            return None

    # ── ESPN data ─────────────────────────────────────────────

    async def _fetch_scoreboard(self) -> Optional[Dict]:
        cached = self._cached("scoreboard")
        if cached is not None:
            return cached
        url = f"{_ESPN_BASE}/{self.tournament}/scoreboard"
        data = await self._http_get_json(url)
        if data:
            self._set_cache("scoreboard", data)
        return data

    async def _fetch_leaderboard(self) -> Optional[Dict]:
        cached = self._cached("leaderboard")
        if cached is not None:
            return cached
        url = f"{_ESPN_BASE}/{self.tournament}/leaderboard"
        data = await self._http_get_json(url)
        if data:
            self._set_cache("leaderboard", data)
        return data

    def _parse_tournament_info(self, scoreboard: Dict) -> Dict[str, Any]:
        """Extract tournament name, status, round, dates from scoreboard."""
        events = scoreboard.get("events", [])
        if not events:
            return {}
        ev = events[0]
        name = ev.get("name", ev.get("shortName", "Tournament"))
        status_obj = ev.get("status", {})
        status_type = status_obj.get("type", {})
        state = status_type.get("state", "pre")  # pre, in, post
        detail = status_type.get("detail", "")

        # Venue / location
        competitions = ev.get("competitions", [])
        venue_name = ""
        venue_city = ""
        if competitions:
            venue_obj = competitions[0].get("venue", {})
            venue_name = venue_obj.get("fullName", "")
            addr = venue_obj.get("address", {})
            city = addr.get("city", "")
            st = addr.get("state", "")
            venue_city = f"{city}, {st}" if city else ""

        # Dates
        start_date = ev.get("date", "")

        return {
            "name": name,
            "state": state,
            "detail": detail,
            "venue_name": venue_name,
            "venue_city": venue_city,
            "start_date": start_date,
        }

    def _parse_leaderboard(self, lb_data: Dict) -> List[Dict[str, Any]]:
        """Extract top players from leaderboard response."""
        players = []
        # ESPN leaderboard nests under events[0].competitions[0].competitors
        events = lb_data.get("events", [])
        if not events:
            return players

        competitions = events[0].get("competitions", [])
        if not competitions:
            return players

        competitors = competitions[0].get("competitors", [])
        for c in competitors:
            athlete = c.get("athlete", {})
            name = athlete.get("displayName", "Unknown")
            score_str = c.get("score", "0")
            try:
                score = int(score_str)
            except (ValueError, TypeError):
                score = 0
            status = c.get("status", {}).get("type", {}).get("name", "")
            pos = c.get("sortOrder", 99)
            pos_display = c.get("status", {}).get("displayValue", str(pos))
            linescores = c.get("linescores", [])
            thru = ""
            if linescores:
                last = linescores[-1]
                thru = last.get("displayValue", "")

            players.append({
                "name": name,
                "short_name": _shorten_name(name),
                "score": score,
                "score_display": _format_score(score),
                "position": pos,
                "pos_display": pos_display,
                "status": status,
                "thru": thru,
            })

        # Sort by position/score
        players.sort(key=lambda p: p["position"])
        return players

    # ── Weather ────────────────────────────────────────────────

    async def _fetch_venue_weather(self, location: str) -> Optional[Dict[str, Any]]:
        if not location:
            return None
        url = f"https://wttr.in/{location}?format=j1"
        raw = await self._http_get_json(url, timeout=8)
        if not raw:
            return None
        try:
            current = raw.get("current_condition", [{}])[0]
            wind_dir_deg = current.get("winddirDegree", "0")
            try:
                compass = _deg_to_compass(float(wind_dir_deg))
            except (ValueError, TypeError):
                compass = current.get("winddir16Point", "")

            result = {
                "temp_f": current.get("temp_F", "?"),
                "condition": current.get("weatherDesc", [{}])[0].get("value", ""),
                "wind_mph": current.get("windspeedMiles", "?"),
                "wind_dir": compass,
                "humidity": current.get("humidity", "?"),
            }

            # Forecast for next day
            weather_list = raw.get("weather", [])
            if len(weather_list) > 1:
                tmrw = weather_list[1]
                result["forecast_high_f"] = tmrw.get("maxtempF", "?")
                hourly = tmrw.get("hourly", [])
                rain_chances = [int(h.get("chanceofrain", 0)) for h in hourly if h.get("chanceofrain")]
                if rain_chances:
                    result["forecast_rain_pct"] = max(rain_chances)
            return result
        except Exception:
            return None

    # ── Odds ──────────────────────────────────────────────────

    async def _fetch_odds(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch golf outright odds from the-odds-api.com (requires key)."""
        if not self.odds_api_key:
            return None
        url = (
            f"https://api.the-odds-api.com/v4/sports/golf_pga_championship/odds/"
            f"?apiKey={self.odds_api_key}&regions=us&markets=outrights&oddsFormat=american"
        )
        raw = await self._http_get_json(url, timeout=10)
        if not raw or not isinstance(raw, list) or not raw:
            return None
        try:
            bookmakers = raw[0].get("bookmakers", [])
            if not bookmakers:
                return None
            markets = bookmakers[0].get("markets", [])
            if not markets:
                return None
            outcomes = markets[0].get("outcomes", [])
            odds_list = []
            for o in outcomes[:10]:
                odds_list.append({
                    "name": _shorten_name(o.get("name", "")),
                    "price": o.get("price", 0),
                })
            return odds_list
        except Exception:
            return None

    # ── Main fetch ────────────────────────────────────────────

    async def fetch(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        # 1. ESPN scoreboard + leaderboard
        scoreboard = await self._fetch_scoreboard()
        if scoreboard:
            result["tournament"] = self._parse_tournament_info(scoreboard)
        else:
            result["tournament"] = {}

        lb_data = await self._fetch_leaderboard()
        if lb_data:
            result["leaderboard"] = self._parse_leaderboard(lb_data)
        else:
            result["leaderboard"] = []

        # 2. Venue weather
        if self.include_weather:
            venue_city = result.get("tournament", {}).get("venue_city", "")
            t_name = result.get("tournament", {}).get("name", "").lower()
            # Known venue mappings for majors
            if not venue_city and "masters" in t_name:
                venue_city = "Augusta, GA"
            elif not venue_city and "pga championship" in t_name:
                venue_city = ""  # varies yearly
            elif not venue_city and "u.s. open" in t_name:
                venue_city = ""
            location = venue_city or "Augusta, GA"
            weather = await self._fetch_venue_weather(location)
            if weather:
                weather["location"] = location
                result["weather"] = weather

        # 3. Odds
        if self.include_odds:
            odds = await self._fetch_odds()
            if odds:
                result["odds"] = odds

        # If we got nothing at all, signal error
        if not result.get("tournament") and not result.get("leaderboard"):
            result["error"] = "no ESPN data"

        return result

    # ── Compress ──────────────────────────────────────────────

    def compress(self, data: Dict[str, Any]) -> str:
        lines: List[str] = []
        tourney = data.get("tournament", {})
        leaders = data.get("leaderboard", [])
        weather = data.get("weather")
        odds = data.get("odds")

        # Tournament header
        t_name = tourney.get("name", "PGA Tour")
        state = tourney.get("state", "pre")
        detail = tourney.get("detail", "")

        if state == "pre":
            lines.append(f"📊 {t_name} | {detail}" if detail else f"📊 {t_name}")
        elif state == "in":
            lines.append(f"📊 {t_name} - {detail}")
        else:
            lines.append(f"📊 {t_name} (Final)")

        # Leaderboard
        if leaders:
            top = leaders[: self.top_n]
            parts = []
            for i, p in enumerate(top):
                if i == 0:
                    parts.append(f"Leader: {p['short_name']} {p['score_display']}")
                else:
                    parts.append(f"{p['short_name']} {p['score_display']}")
            lines.append("🏌 " + " | ".join(parts))

            # Withdrawals / cuts
            wds = [p for p in leaders if p.get("status") == "WD"]
            if wds:
                wd_names = ", ".join(p["short_name"] for p in wds[:3])
                lines.append(f"⚠ WD: {wd_names}")
        elif state == "pre" and tourney:
            lines.append("🏌 Field TBD")

        # Weather
        if weather:
            loc = weather.get("location", "")
            temp = weather.get("temp_f", "?")
            wind = weather.get("wind_mph", "?")
            wind_dir = weather.get("wind_dir", "")
            w_line = f"🌤 {loc}: {temp}°F, wind {wind}mph {wind_dir}"
            # Add forecast if pre-tournament
            if state == "pre" and weather.get("forecast_high_f"):
                rain = weather.get("forecast_rain_pct", 0)
                w_line += f" | Forecast: {weather['forecast_high_f']}°F, {rain}% rain"
            lines.append(w_line)

        # Odds
        if odds:
            top_odds = odds[:3]
            parts = [f"{o['name']} {o['price']:+d}" for o in top_odds]
            lines.append("📉 Odds: " + " | ".join(parts))

        return "\n".join(lines)
