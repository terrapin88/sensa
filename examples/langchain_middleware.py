"""
LangChain Integration
=====================

Shows how to integrate Sensa context into LangChain agents and chains.

Two patterns are demonstrated:
  1. A Runnable wrapper that injects context into every invocation
  2. A custom callback handler that refreshes context before each LLM call

pip install langchain langchain-openai sensa
"""

import asyncio
from typing import Any, Dict, List, Optional

from sensa import SensaClient


# ---------------------------------------------------------------------------
# Pattern 1: Runnable wrapper (recommended)
# ---------------------------------------------------------------------------

def runnable_wrapper_example():
    """
    Wrap a LangChain chain so that Sensa context is injected into
    the system message on every invocation.
    """
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.runnables import RunnableLambda, RunnablePassthrough
    from langchain_openai import ChatOpenAI

    sensa = SensaClient(api_key="your-sensa-api-key")
    llm = ChatOpenAI(model="gpt-4o", api_key="your-openai-api-key")

    # Base prompt with a placeholder for the live context
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful assistant.\n\n"
            "<current_environment>\n{sensa_context}\n</current_environment>\n\n"
            "Use the environment data above for any time-sensitive answers.",
        ),
        ("human", "{input}"),
    ])

    def inject_sensa_context(inputs: dict) -> dict:
        """Fetch fresh Sensa context and merge it into the chain inputs."""
        context = sensa.get_context()
        return {**inputs, "sensa_context": context}

    # Build the chain: inject context -> format prompt -> call LLM
    chain = RunnableLambda(inject_sensa_context) | prompt | llm

    # Every invocation now gets live context automatically
    response = chain.invoke({"input": "What's the weather like right now?"})
    print("=== Runnable Wrapper Response ===")
    print(response.content)


# ---------------------------------------------------------------------------
# Pattern 2: Callback handler (for existing chains you can't easily modify)
# ---------------------------------------------------------------------------

def callback_handler_example():
    """
    Use a LangChain callback to prepend Sensa context to the system
    message right before the LLM is called.  This works with any
    existing chain without changing its structure.
    """
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.messages import SystemMessage
    from langchain_openai import ChatOpenAI

    class SensaContextHandler(BaseCallbackHandler):
        """
        LangChain callback that injects real-time Sensa context into
        the first system message before every LLM call.
        """

        def __init__(self, sensa_client: SensaClient):
            self.sensa = sensa_client

        def on_llm_start(
            self,
            serialized: Dict[str, Any],
            prompts: List[str],
            **kwargs: Any,
        ) -> None:
            """
            Called before the LLM processes a request.
            We prepend Sensa context to the first prompt/system message.
            """
            context = self.sensa.get_context()
            context_block = (
                f"\n<current_environment>\n{context}\n</current_environment>\n"
            )
            # Prepend context to the first prompt string
            if prompts:
                prompts[0] = context_block + prompts[0]

        def on_chat_model_start(
            self,
            serialized: Dict[str, Any],
            messages: List[List[Any]],
            **kwargs: Any,
        ) -> None:
            """
            Called before a chat model processes messages.
            We inject Sensa context into the system message.
            """
            context = self.sensa.get_context()
            context_block = (
                f"\n<current_environment>\n{context}\n</current_environment>\n"
            )
            for message_list in messages:
                # Find existing system message and augment it
                for i, msg in enumerate(message_list):
                    if isinstance(msg, SystemMessage):
                        msg.content = msg.content + context_block
                        break
                else:
                    # No system message found — insert one at the start
                    message_list.insert(
                        0,
                        SystemMessage(content=context_block),
                    )

    # Usage: attach the handler to any LLM
    sensa = SensaClient(api_key="your-sensa-api-key")
    handler = SensaContextHandler(sensa)

    llm = ChatOpenAI(
        model="gpt-4o",
        api_key="your-openai-api-key",
        callbacks=[handler],
    )

    # Now any chain using this LLM gets Sensa context for free
    response = llm.invoke("What time is it and what's happening in the news?")
    print("=== Callback Handler Response ===")
    print(response.content)


# ---------------------------------------------------------------------------
# Pattern 3: Agent with tools + Sensa context
# ---------------------------------------------------------------------------

def agent_with_tools_example():
    """
    Full LangChain agent with tools, augmented by Sensa context.
    The agent can answer real-time questions without needing a
    dedicated "clock" or "weather" tool — Sensa provides that data
    in the system prompt.
    """
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_tool_calling_agent

    sensa = SensaClient(
        api_key="your-sensa-api-key",
        channels=["time", "weather", "crypto", "news"],
    )

    # Example tool — the agent still has tools for domain-specific actions
    @tool
    def calculate(expression: str) -> str:
        """Evaluate a math expression. Example: '2 + 2'"""
        try:
            return str(eval(expression))  # noqa: S307 — demo only
        except Exception as e:
            return f"Error: {e}"

    llm = ChatOpenAI(model="gpt-4o", api_key="your-openai-api-key")
    context = sensa.get_context()

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful assistant with access to tools.\n\n"
            "<current_environment>\n" + context + "\n</current_environment>\n\n"
            "Use the environment data for time, weather, prices, and news.\n"
            "Use tools for calculations and other actions.",
        ),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, [calculate], prompt)
    executor = AgentExecutor(agent=agent, tools=[calculate], verbose=True)

    result = executor.invoke({
        "input": "If BTC is at the price shown above, how much is 0.5 BTC in USD?"
    })
    print("=== Agent Response ===")
    print(result["output"])


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Uncomment the example you want to run:
    # runnable_wrapper_example()
    # callback_handler_example()
    # agent_with_tools_example()

    print("Uncomment one of the examples in __main__ to run it.")
    print("Make sure to set your API keys first.")
