# Why Your Agent Doesn't Know What Time It Is

**I was building DraftKings lineups with my AI agent when it told me it was Monday. It was Tuesday.**

This is a story about a $0 bug that revealed a billion-dollar gap in AI infrastructure.

---

It was Masters week. I had my AI agent — Hermes, running on a long-lived session — helping me build optimal DraftKings golf lineups. We'd been going back and forth for a while: pulling player stats, analyzing course history at Augusta, optimizing salary cap allocations.

Then I asked it to factor in the current round schedule. It confidently told me it was Monday, April 6th. Practice rounds. No need to rush.

It was Tuesday, April 7th. The tournament was starting. My lineups were due.

The agent wasn't hallucinating in the traditional sense. It wasn't making up facts about golf. It had been given a timestamp when the session started — on Monday — and had been riding that single frozen moment in time ever since. Hours had passed. A day had turned. The agent had no idea.

I didn't lose money. But I easily could have. And that near-miss sent me down a rabbit hole that ended with me building an open-source library — because the problem isn't just my agent. It's *every* agent.

## The Problem: Temporal Blindness

Here's something most people building with LLMs don't think about until it bites them: **your agent has no idea what time it is.**

Not really. Not in any meaningful, ongoing sense.

When you start a session with Claude, GPT-4, or any other model, the system prompt typically includes a timestamp. Something like: `The current date is Monday, April 6, 2026.` That timestamp is set once. It never updates. If your session runs for 6 hours, or you pick up a conversation the next day, the model still thinks it's Monday morning.

This isn't a bug in any single model. It's a structural property of how LLMs work. They're stateless text-completion engines. They don't experience the passage of time. They process a context window and produce a response. The "current time" is just another string in the prompt — and if nobody updates that string, it rots.

**Even agents with tool access don't solve this.** Give your agent a web search tool, a weather API, a calendar integration. It still won't *spontaneously* check the time. Tools are reactive — the agent has to decide to use them. If the agent believes it's Monday (because the prompt says so), why would it question that? It doesn't feel the doubt. There's no internal clock ticking away, creating cognitive dissonance.

I call this **context drift** — the silent divergence between what an agent believes about the world and what's actually true. It's not hallucination (generating false information). It's something subtler and arguably more dangerous: **operating on stale truths with perfect confidence.**

The academic literature backs this up. Research on temporal reasoning in LLMs (see work from [Thoppilan et al.](https://arxiv.org/abs/2201.11903) and [Dhingra et al.](https://arxiv.org/abs/2204.14211)) consistently shows that models struggle with time-dependent reasoning, particularly when temporal context isn't explicitly refreshed. They confuse tenses, misorder events, and — critically — can't distinguish between "what was true when training ended" and "what is true right now."

Andrej Karpathy recently reframed prompt engineering as **"context engineering"** — the art of curating the right information in the model's context window at the right time. I think he's exactly right, and temporal awareness is the most fundamental piece of context we're failing to engineer. Before an agent can reason about *anything* in the real world, it needs to know *when* it is in the real world.

## How the Industry (Doesn't) Handle This

The AI infrastructure ecosystem is booming. Billions in funding. Hundreds of startups. And yet, almost nobody is working on this specific problem. Here's the landscape as I see it:

**Camp 1: Bigger context windows.** Google's Gemini now supports 2 million tokens. Anthropic keeps pushing Claude's window larger. The theory: stuff more information in, and the model will figure it out. But a larger window doesn't solve freshness. You can fit an entire encyclopedia in the context and the model still won't know it's raining outside.

**Camp 2: Tool use and function calling.** MCP (Model Context Protocol), OpenAI function calling, tool-use frameworks — these let agents *do* things. Search the web. Call APIs. Check the weather. But they're fundamentally reactive. The agent must decide to reach for a tool. If its existing context feels sufficient (even if stale), it won't. You're relying on the model to know what it doesn't know, which is precisely the metacognitive skill LLMs lack.

**Memory companies** like Mem0, Zep, and Letta are building persistence layers — letting agents remember past conversations and user preferences. This is valuable work, but it's backward-looking. Memory tells you what *was*. It doesn't tell you what *is*.

**Tool platforms** like Composio and Toolhouse aggregate APIs and give agents the ability to take actions. Also valuable. But again, action-oriented, not ambient. They're the arms and legs, not the senses.

**The gap:** Nobody is building the **perception layer** — the ambient, always-current awareness that sits between memory (the past) and tools (actions). The thing that tells an agent, without being asked, "it's 5 PM on Tuesday, it's 74°F and sunny, Bitcoin just moved 2%, and here's what's happening in the news."

Humans have this. We glance at clocks, feel the weather, overhear headlines. It's not something we consciously decide to do — it's ambient. Our agents need the equivalent.

## Introducing Sensa

**Sensa** is a lightweight Python library that gives AI agents ambient world awareness. One function call. Fresh context. Every time.

```
pip install sensa
```

```python
from sensa import get_context

context = get_context()
print(context)
```

Output:

```
[SENSA — Tue Apr 7, 2026 5:00 PM CDT]
⏱ Session: <1m | Last call: <1m
🌤 Austin, TX: 74°F, sunny, wind 9mph
📈 BTC: $69,905 (+0.6%) | ETH: $2,145 (+0.2%) | SOL: $82.90 (+1.7%)
📰 Iranians form human chains... | Wireless Festival cancelled...
```

That's it. That block of text — roughly **87 tokens** — gives your agent a real-time snapshot of the world. Inject it into any system prompt, and your agent suddenly knows:

- **When** it is (date, time, timezone, session duration, time since last interaction)
- **What the weather is** (temperature, conditions, wind — geolocated automatically)
- **What markets are doing** (BTC, ETH, SOL with price and 24h change)
- **What's happening** (top headlines, compressed)

Four channels. All optional. All configurable. Zero API keys required for basic usage.

The session tracking is particularly useful. That `Session: <1m | Last call: <1m` line lets the agent know if it's in a rapid-fire conversation or if the user disappeared for 3 hours and just came back. That's context that fundamentally changes how an agent should respond.

## Integration Patterns

**Pattern 1: Basic injection (5 lines)**

```python
from sensa import get_context

def build_system_prompt():
    base = "You are a helpful assistant."
    world = get_context()
    return f"{base}\n\n{world}"
```

**Pattern 2: OpenAI / Anthropic system prompts**

```python
from openai import OpenAI
from sensa import get_context

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": f"You are a helpful assistant.\n\n{get_context()}"
        },
        {
            "role": "user",
            "content": "Should I go for a run right now?"
        }
    ]
)
# The model now knows it's 74°F and sunny — it can actually answer this.
```

**Pattern 3: Custom channels**

```python
from sensa import Sensa, Channel

class PortfolioChannel(Channel):
    name = "portfolio"
    default_enabled = True

    def render(self, config):
        # Pull from your own data source
        positions = get_my_positions()
        total = sum(p.value for p in positions)
        return f"💼 Portfolio: ${total:,.0f} | {len(positions)} positions"

sensa = Sensa(channels=["time", "weather", PortfolioChannel()])
context = sensa.get_context()
```

The channel system is designed to be extended. Each channel is a self-contained unit that knows how to fetch and render one slice of world state. Compose them however you want.

## Design Philosophy

A few deliberate choices worth calling out:

**Token efficiency matters.** When you're injecting context into every API call, every token counts. Sensa's full output is ~87 tokens. That's less than most system prompts. We obsessed over compression — abbreviations, symbols, information density — so you're getting maximum awareness per token.

**Zero config by default, full control when you want it.** `get_context()` works out of the box. But you can configure channels, set locations manually, choose which crypto to track, set staleness thresholds, all of it.

**Ambient, not reactive.** Sensa isn't a tool the agent calls. It's context the agent *always has*. This is the key philosophical difference. You don't want your agent to decide to check the time. You want it to already know.

**Open source, MIT licensed.** This is infrastructure. It should be free and forkable.

## What's Next

Sensa ships today with four channels: time, weather, crypto, and news. Here's where we're headed:

- **More channels:** Sports scores and schedules (imagine: your agent knows the Masters leaderboard). Calendar awareness. Infrastructure status (is AWS us-east-1 having issues?). Market hours and trading sessions. Astronomical data (sunrise/sunset). Air quality.
- **Framework middleware:** Native integrations with LangChain, CrewAI, AutoGen, and other agent frameworks. Sensa as automatic middleware that injects context without you wiring it up manually.
- **Channel marketplace:** A registry where anyone can publish and share context channels. Build a channel for your domain, publish it, let others `pip install` it and add it to their Sensa config.
- **Staleness detection:** Smarter tracking of when context is getting old and should be refreshed. Adaptive refresh rates based on how time-sensitive a conversation is.

## The Bigger Picture

We're in the early days of a massive shift. AI agents are moving from chatbots to autonomous systems that manage money, schedule surgeries, control infrastructure, and make real-world decisions. The stakes are going up exponentially.

And right now, most of these agents don't know what day it is.

That's not a cute limitation. It's a structural failure in the stack. Memory systems, tool frameworks, evaluation harnesses — all critical, all getting funded and built. But the perception layer — ambient, real-time awareness of the present moment — has been overlooked.

Sensa is a small library solving one piece of this. But the idea is bigger than any single package: **agents need senses, not just skills.**

## Get Started

```
pip install sensa
```

**GitHub:** [github.com/terrapin88/sensa](https://github.com/terrapin88/sensa)

Star the repo. Open issues. Tell us what channels you want. Build your own and contribute them back.

If you've been bitten by an agent that didn't know the time, the weather, or what's happening in the world — you know why this matters.

**Your agents deserve to know what's happening right now.**

---

*Sensa is open source and MIT licensed. Built in Austin, TX on a Tuesday that my agent thought was a Monday.*
