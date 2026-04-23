"""
OpenRouter LLM Client
Real LLM integration via OpenRouter API (OpenAI-compatible).
Used by composer, tone guard, and τ²-Bench harness.
"""

import json
import time
from typing import Optional
from openai import AsyncOpenAI

import config


def get_llm_client() -> AsyncOpenAI:
    """Get an async OpenRouter client."""
    return AsyncOpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
    )


async def chat_completion(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    response_format: Optional[dict] = None,
    trace_metadata: Optional[dict] = None,
) -> dict:
    """
    Run a chat completion via OpenRouter.

    Returns dict with:
        content: str
        model: str
        usage: {prompt_tokens, completion_tokens, total_tokens}
        latency_ms: int
        cost_usd: float (estimated)
    """
    client = get_llm_client()
    model = model or config.DEV_MODEL

    start = time.time()

    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    response = await client.chat.completions.create(**kwargs)

    latency_ms = int((time.time() - start) * 1000)

    usage = response.usage
    content = response.choices[0].message.content or ""

    # Estimate cost (OpenRouter pricing varies per model)
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    # Rough estimate: ~$0.50/M input, ~$1.50/M output for dev models
    cost_usd = (prompt_tokens * 0.5 + completion_tokens * 1.5) / 1_000_000

    result = {
        "content": content,
        "model": model,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "latency_ms": latency_ms,
        "cost_usd": round(cost_usd, 6),
    }

    # Log to Langfuse if available
    if trace_metadata:
        try:
            from agent.langfuse_wrapper import log_llm_call
            log_llm_call(result, trace_metadata)
        except ImportError:
            pass

    return result


async def chat_completion_json(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.3,
) -> dict:
    """Chat completion with JSON response parsing."""
    result = await chat_completion(
        messages=messages,
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    try:
        result["parsed"] = json.loads(result["content"])
    except json.JSONDecodeError:
        result["parsed"] = {}
    return result
