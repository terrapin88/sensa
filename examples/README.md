# Sensa Examples

Runnable examples demonstrating how to use the Sensa Python SDK to give AI agents real-time environmental awareness.

## Examples

| File | Description |
|------|-------------|
| **basic_usage.py** | Getting started — sync/async usage, custom channel config, and simple prompt injection |
| **hermes_integration.py** | Injecting Sensa context into OpenAI and Anthropic API calls; multi-turn context refresh |
| **langchain_middleware.py** | LangChain integration via Runnable wrappers, callback handlers, and tool-calling agents |
| **trading_agent.py** | Crypto trading agent with BTC/ETH/SOL monitoring and staleness detection |
| **custom_channel.py** | Extending Sensa with custom data channels (PagerDuty incidents, GitHub PRs) |

## Quick Start

```bash
pip install sensa
```

Run any example:

```bash
# Staleness detection demo (no API keys needed)
python trading_agent.py

# Custom channel demo (no API keys needed)
python custom_channel.py

# Full examples (set your API keys first)
python basic_usage.py
python hermes_integration.py
python langchain_middleware.py
```

## What is Sensa Context?

LLMs have a training-data cutoff and no built-in access to real-time information.  Without grounding data, they hallucinate today's date, current prices, and weather conditions.

Sensa fetches a live environment snapshot — time, weather, crypto prices, news headlines — and formats it for injection into system prompts.  The model gets accurate grounding data on every call, with staleness detection to ensure nothing is outdated.

```python
from sensa import SensaClient

client = SensaClient(api_key="...")
context = client.get_context()

# context is a string like:
#   Current time: 2026-04-07T16:45:00Z (Tuesday)
#   Weather in San Francisco: 62F, partly cloudy
#   BTC: $84,210 (+2.3% 24h) | ETH: $1,812 (-0.4% 24h)
#   Top headline: "Fed holds rates steady amid inflation concerns"
```

Prepend this to your system prompt and the model always knows what's happening right now.
