"""
Prefill vs Decode Latency Demo — Week 12 Day 1

Demonstrates the computational asymmetry between prefill (processing input)
and decode (generating output) in LLM inference.

Test A: Vary prompt length, fix output length → shows superlinear prefill scaling
Test B: Fix prompt length, vary output length → shows linear decode scaling
"""

import asyncio
import time
import json
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

MODEL = "openai/gpt-4o-mini"  # Avoid rate limits


async def measure_call(prompt_text: str, max_tokens: int, label: str) -> dict:
    """Measure a single LLM call with streaming to separate TTFT from decode."""
    messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": "Summarize the key point in exactly the requested number of sentences."}
    ]

    # Streaming call to separate time-to-first-token (prefill) from decode
    start = time.perf_counter()
    first_token_time = None
    token_count = 0
    full_content = ""

    stream = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.3,
        stream=True,
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            if first_token_time is None:
                first_token_time = time.perf_counter()
            token_count += 1
            full_content += chunk.choices[0].delta.content

    end = time.perf_counter()

    ttft = (first_token_time - start) if first_token_time else 0
    total = end - start
    decode_time = total - ttft
    tokens_per_sec = token_count / decode_time if decode_time > 0 else 0

    result = {
        "label": label,
        "prompt_tokens_approx": len(prompt_text.split()),  # rough word count
        "max_tokens": max_tokens,
        "output_tokens": token_count,
        "ttft_ms": round(ttft * 1000),
        "decode_ms": round(decode_time * 1000),
        "total_ms": round(total * 1000),
        "decode_tok_per_sec": round(tokens_per_sec, 1),
    }

    print(f"  {label}: TTFT={result['ttft_ms']}ms | Decode={result['decode_ms']}ms | "
          f"Total={result['total_ms']}ms | Output={token_count} tokens | "
          f"Rate={tokens_per_sec:.1f} tok/s")

    return result


def build_padding(target_words: int) -> str:
    """Build a realistic system prompt of approximately target_words length."""
    base = (
        "You are a senior B2B sales consultant for Tenacious Consulting. "
        "Your role is to analyze prospect hiring signals and craft grounded, "
        "evidence-based outreach. Never overclaim. Never use aggressive language. "
        "Always ground assertions in the hiring signal brief provided. "
    )
    # Pad with realistic enrichment brief content
    padding_block = (
        "The prospect's Crunchbase profile shows a Series B round of $24M "
        "closed 4 months ago. Job post velocity over the past 60 days indicates "
        "12 new engineering roles, 3 of which mention data infrastructure. "
        "Layoffs.fyi shows no recent layoffs. Leadership change detected: new "
        "CTO appointed 2 months ago from a cloud-native background. AI maturity "
        "score: 1 (experimentation phase). Competitor gap analysis shows the "
        "prospect is in the bottom quartile for MLOps tooling adoption in their "
        "sector. The company operates in fintech with 200-500 employees. "
    )
    result = base
    while len(result.split()) < target_words:
        result += padding_block
    return result


async def run_demo():
    results = []

    print("=" * 70)
    print("TEST A: Vary prompt length, fix output (50 tokens)")
    print("  Shows: prefill scaling (should be superlinear)")
    print("=" * 70)

    for prompt_words in [100, 500, 1000, 2000]:
        prompt = build_padding(prompt_words)
        r = await measure_call(prompt, max_tokens=50, label=f"A-{prompt_words}w-prompt")
        results.append(r)
        await asyncio.sleep(1)  # Rate limit courtesy

    print()
    print("=" * 70)
    print("TEST B: Fix prompt (500 words), vary output length")
    print("  Shows: decode scaling (should be ~linear)")
    print("=" * 70)

    prompt = build_padding(500)
    for max_tok in [25, 50, 100, 200]:
        r = await measure_call(prompt, max_tokens=max_tok, label=f"B-{max_tok}-max-out")
        results.append(r)
        await asyncio.sleep(1)

    # Summary table
    print()
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Label':<20} {'TTFT(ms)':>10} {'Decode(ms)':>12} {'Total(ms)':>10} {'Out Tok':>8} {'Tok/s':>8}")
    print("-" * 70)
    for r in results:
        print(f"{r['label']:<20} {r['ttft_ms']:>10} {r['decode_ms']:>12} {r['total_ms']:>10} "
              f"{r['output_tokens']:>8} {r['decode_tok_per_sec']:>8}")

    # Save results
    out_path = "week12/pair_day_1/demo_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    return results


if __name__ == "__main__":
    asyncio.run(run_demo())
