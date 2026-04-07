"""Built-in Sensa channels."""

from sensa.channels.base import BaseChannel
from sensa.channels.time_channel import TimeChannel
from sensa.channels.weather import WeatherChannel
from sensa.channels.crypto import CryptoChannel
from sensa.channels.news import NewsChannel
from sensa.channels.sports import SportsChannel

# Registry mapping channel names to classes
CHANNEL_REGISTRY = {
    "time": TimeChannel,
    "weather": WeatherChannel,
    "crypto": CryptoChannel,
    "news": NewsChannel,
    "sports": SportsChannel,
}

__all__ = [
    "BaseChannel",
    "TimeChannel",
    "WeatherChannel",
    "CryptoChannel",
    "NewsChannel",
    "SportsChannel",
    "CHANNEL_REGISTRY",
]
