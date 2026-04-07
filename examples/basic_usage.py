"""
Basic Sensa Usage
=================

Demonstrates the core workflow:
1. Initialize SensaClient with an API key
2. Fetch real-time context (time, weather, news, crypto prices, etc.)
3. Print the context string ready for injection into an AI prompt

Shows sync, async, and custom channel configuration patterns.
"""

import asyncio
from sensa import SensaClient


# ---------------------------------------------------------------------------
# 1. Minimal example – synchronous one-liner
# ---------------------------------------------------------------------------

def sync_example():
    """Get context synchronously (blocks the thread)."""
    client = SensaClient(api_key="your-sensa-api-key")

    # get_context() returns a plain string summarizing the current environment
    context = client.get_context()
    print("=== Sync Context ===")
    print(context)
    # Example output:
    #   Current time: 2026-04-07T16:45:00Z (Tuesday)
    #   Weather in San Francisco: 62°F, partly cloudy
    #   BTC: $84,210 (+2.3% 24h) | ETH: $1,812 (-0.4% 24h)
    #   Top headline: "Fed holds rates steady amid inflation concerns"


# ---------------------------------------------------------------------------
# 2. Async example – recommended for production
# ---------------------------------------------------------------------------

async def async_example():
    """Get context with async/await (non-blocking, ideal for agents)."""
    client = SensaClient(api_key="your-sensa-api-key")

    context = await client.aget_context()
    print("=== Async Context ===")
    print(context)


# ---------------------------------------------------------------------------
# 3. Custom channel configuration
# ---------------------------------------------------------------------------

async def custom_channels_example():
    """
    By default SensaClient fetches all available channels.
    You can enable only the ones your agent cares about, and configure
    each channel individually.
    """
    client = SensaClient(
        api_key="your-sensa-api-key",
        # Only fetch these channels (skips the rest for speed & cost)
        channels=["time", "weather", "crypto"],
        # Per-channel configuration overrides
        channel_config={
            "weather": {
                "location": "New York, NY",
                "units": "imperial",        # or "metric"
            },
            "crypto": {
                "symbols": ["BTC", "ETH", "SOL"],
                "include_24h_change": True,
            },
        },
        # How many seconds before cached data is considered stale
        staleness_threshold=120,
    )

    context = await client.aget_context()
    print("=== Custom Channels Context ===")
    print(context)

    # You can also fetch a single channel's data as structured dict
    crypto_data = await client.aget_channel("crypto")
    print("\nStructured crypto data:")
    for coin in crypto_data.get("prices", []):
        print(f"  {coin['symbol']}: ${coin['price']:,.2f}")


# ---------------------------------------------------------------------------
# 4. Using context in a prompt
# ---------------------------------------------------------------------------

def prompt_injection_example():
    """Show the simplest way to prepend context to a system prompt."""
    client = SensaClient(api_key="your-sensa-api-key")
    context = client.get_context()

    system_prompt = f"""You are a helpful assistant.

<current_environment>
{context}
</current_environment>

Use the environment data above when answering time-sensitive questions.
Do not hallucinate dates, prices, or weather — rely on the data provided."""

    print("=== System Prompt with Sensa Context ===")
    print(system_prompt)


# ---------------------------------------------------------------------------
# Run all examples
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("--- Sync Example ---")
    sync_example()

    print("\n--- Async Example ---")
    asyncio.run(async_example())

    print("\n--- Custom Channels ---")
    asyncio.run(custom_channels_example())

    print("\n--- Prompt Injection ---")
    prompt_injection_example()
