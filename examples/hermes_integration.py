"""
Hermes / AI Agent Integration
==============================

Shows how to inject Sensa's real-time context into system prompts for
popular LLM APIs (OpenAI and Anthropic).

WHY THIS MATTERS:
-----------------
LLMs have a training-data cutoff and no access to live information.
Without Sensa, agents often hallucinate today's date, current prices,
or weather conditions.  Sensa replaces stale, baked-in timestamps with
a live environment snapshot fetched at call time — so the model always
has accurate grounding data.

This is especially critical for:
  - Agents that answer "what time is it?" or "what's the weather?"
  - Trading bots that need real-time price feeds
  - Customer-support agents that must know current system status
"""

import asyncio
from sensa import SensaClient

# ---------------------------------------------------------------------------
# Shared: build a system prompt with live context
# ---------------------------------------------------------------------------

AGENT_PERSONA = """\
You are Hermes, an intelligent AI assistant created by Nous Research.
You are helpful, knowledgeable, and direct."""

def build_system_prompt(sensa_context: str) -> str:
    """
    Combine the agent's persona with live environment context.

    The <current_environment> block gives the model grounding data it
    can cite when answering time-sensitive questions.  This replaces
    stale timestamps that would otherwise be hallucinated.
    """
    return f"""{AGENT_PERSONA}

<current_environment>
{sensa_context}
</current_environment>

Use the real-time environment data above when answering questions about
the current date, time, weather, crypto prices, or news headlines.
Never fabricate this information — rely on what is provided."""


# ---------------------------------------------------------------------------
# Example 1: OpenAI Chat Completions
# ---------------------------------------------------------------------------

async def openai_example():
    """
    Inject Sensa context into an OpenAI chat completion request.

    pip install openai sensa
    """
    from openai import AsyncOpenAI

    # 1. Fetch live context
    sensa = SensaClient(
        api_key="your-sensa-api-key",
        channels=["time", "weather", "crypto", "news"],
    )
    context = await sensa.aget_context()

    # 2. Build the system prompt with live data
    system_prompt = build_system_prompt(context)

    # 3. Call OpenAI as usual — the model now has real-time grounding
    openai = AsyncOpenAI(api_key="your-openai-api-key")
    response = await openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "What's the current BTC price and weather in NYC?"},
        ],
    )

    print("=== OpenAI Response ===")
    print(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Example 2: Anthropic Messages API
# ---------------------------------------------------------------------------

async def anthropic_example():
    """
    Inject Sensa context into an Anthropic Messages request.

    pip install anthropic sensa
    """
    from anthropic import AsyncAnthropic

    # 1. Fetch live context
    sensa = SensaClient(
        api_key="your-sensa-api-key",
        channels=["time", "weather", "crypto", "news"],
    )
    context = await sensa.aget_context()

    # 2. Build system prompt with live data
    system_prompt = build_system_prompt(context)

    # 3. Call Anthropic — system prompt carries the real-time context
    anthropic = AsyncAnthropic(api_key="your-anthropic-api-key")
    response = await anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": "What's the current BTC price and weather in NYC?"},
        ],
    )

    print("=== Anthropic Response ===")
    print(response.content[0].text)


# ---------------------------------------------------------------------------
# Example 3: Refresh context on every turn (multi-turn conversation)
# ---------------------------------------------------------------------------

async def multi_turn_example():
    """
    For long-running conversations, refresh context each turn so the
    model never operates on stale data.
    """
    from openai import AsyncOpenAI

    sensa = SensaClient(api_key="your-sensa-api-key")
    openai = AsyncOpenAI(api_key="your-openai-api-key")

    conversation = []
    user_messages = [
        "What time is it right now?",
        "How about the weather — is it raining?",
        "Give me a BTC price check.",
    ]

    for user_msg in user_messages:
        # Refresh context every turn — this is cheap and keeps data fresh.
        # Without this, an agent in a 30-minute conversation would still
        # reference the context from the first message.
        context = await sensa.aget_context()
        system_prompt = build_system_prompt(context)

        conversation.append({"role": "user", "content": user_msg})

        response = await openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                *conversation,
            ],
        )

        assistant_msg = response.choices[0].message.content
        conversation.append({"role": "assistant", "content": assistant_msg})

        print(f"User: {user_msg}")
        print(f"Assistant: {assistant_msg}\n")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Uncomment the example you want to run:
    # asyncio.run(openai_example())
    # asyncio.run(anthropic_example())
    # asyncio.run(multi_turn_example())

    print("Uncomment one of the examples in __main__ to run it.")
    print("Make sure to set your API keys first.")
