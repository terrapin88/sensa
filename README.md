# 🧠 sensa

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**Real-time environmental context for AI agents.**

Your AI agent doesn't know what time it is. It doesn't know if it's raining, what Bitcoin costs, or what just happened in the news. Sensa fixes that — injecting a compact, token-efficient snapshot of the real world into every prompt.

## Quick Install

```bash
pip install sensa
```

## Quickstart

```python
from sensa import SensaClient

client = SensaClient(channels=["time", "weather", "crypto", "news"], location="Austin, TX")
context = client.get_context_sync()
print(context)
```

**Example output:**
```
[SENSA — Tue Apr 7, 2026 3:15 PM CDT]
⏱ Session: 47m | Last call: 2m ago
🌤 Austin, TX: 78°F, partly cloudy, wind 8mph
📈 BTC: $94,230 (+2.1%) | ETH: $3,847 (+1.8%) | SOL: $142 (+0.5%)
📰 Fed signals rate hold | Tech earnings beat estimates | Oil prices steady
```

## Channels

| Channel   | Data                          | API              | Key Required |
|-----------|-------------------------------|------------------|--------------|
| `time`    | Date, time, session tracking  | stdlib           | No           |
| `weather` | Temp, conditions, wind        | wttr.in          | No           |
| `crypto`  | BTC, ETH, SOL prices + 24h % | CoinGecko        | No           |
| `news`    | Top 3 headlines               | RSS (BBC, AP)    | No           |

## Configuration

```python
client = SensaClient(
    channels=["time", "weather", "crypto"],
    location="Austin, TX",           # Used by weather channel
    timezone="America/Chicago",      # Timezone for time channel
    max_tokens=200,                  # Token budget for output
    api_keys={                       # Optional premium API keys
        "openweathermap": "your-key",
    },
    staleness_thresholds={           # Minutes before data is flagged stale
        "weather": 15,
        "crypto": 5,
        "news": 30,
    },
)
```

### Async Usage

```python
import asyncio
from sensa import SensaClient

async def main():
    client = SensaClient(channels=["time", "weather"])
    context = await client.get_context()
    print(context)

asyncio.run(main())
```

### Zero Config

Sensa works with zero configuration. Just `SensaClient()` gives you the time channel out of the box.

## How It Works

1. **Channels** fetch data from free public APIs (no keys needed for basic use)
2. **Compression** fits all channel output within your token budget using priority-based allocation
3. **Staleness detection** flags data that's too old, so your agent knows what to trust

## Contributing

Contributions welcome! Please open an issue or PR on GitHub.

1. Fork the repo
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT — see [LICENSE](LICENSE) for details.
