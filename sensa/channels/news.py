"""News channel — top headlines from RSS feeds."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import aiohttp

from sensa.channels.base import BaseChannel
from sensa.config import SensaConfig

# Free RSS feeds that don't require API keys
DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.npr.org/1001/rss.xml",
]


class NewsChannel(BaseChannel):
    """Top headlines from public RSS feeds.

    Parses RSS XML directly to avoid hard dependency on feedparser
    at runtime, but will use feedparser if available for robustness.
    """

    name = "news"
    emoji = "📰"

    def _get_feeds(self) -> List[str]:
        return self.config.news_feeds or DEFAULT_FEEDS

    async def fetch(self) -> Dict[str, Any]:
        feeds = self._get_feeds()
        headlines: List[str] = []

        for feed_url in feeds:
            if len(headlines) >= 3:
                break
            fetched = await self._fetch_feed(feed_url)
            for h in fetched:
                if h not in headlines:
                    headlines.append(h)
                    if len(headlines) >= 3:
                        break

        if not headlines:
            return {"error": "no headlines available"}

        return {"headlines": headlines[:3]}

    async def _fetch_feed(self, url: str) -> List[str]:
        """Fetch and parse a single RSS feed, returning headline strings."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=8)
            ) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return []
                    text = await resp.text()

            # Try feedparser first
            try:
                import feedparser  # type: ignore
                parsed = feedparser.parse(text)
                return [
                    entry.get("title", "").strip()
                    for entry in parsed.entries[:5]
                    if entry.get("title")
                ]
            except ImportError:
                pass

            # Fallback: raw XML parsing
            return self._parse_rss_xml(text)
        except Exception:
            return []

    @staticmethod
    def _parse_rss_xml(xml_text: str) -> List[str]:
        """Parse RSS XML and extract item titles."""
        try:
            root = ET.fromstring(xml_text)
            titles: List[str] = []
            # Standard RSS 2.0: channel/item/title
            for item in root.iter("item"):
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    titles.append(title_el.text.strip())
                    if len(titles) >= 5:
                        break
            return titles
        except ET.ParseError:
            return []

    def compress(self, data: Dict[str, Any]) -> str:
        headlines = data.get("headlines", [])
        if not headlines:
            return f"{self.emoji} news: unavailable"

        # Shorten headlines if too long
        short = []
        for h in headlines[:3]:
            if len(h) > 60:
                h = h[:57] + "…"
            short.append(h)

        return f"{self.emoji} " + " | ".join(short)
