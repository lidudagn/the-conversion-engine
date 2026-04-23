"""
Langfuse Observability Wrapper
Per-trace cost attribution for every LLM call.
"""

import os
import json
from datetime import datetime
from typing import Optional

import config

_langfuse = None


def get_langfuse():
    """Get or create Langfuse client singleton."""
    global _langfuse
    if _langfuse is not None:
        return _langfuse

    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            public_key=config.LANGFUSE_PUBLIC_KEY,
            secret_key=config.LANGFUSE_SECRET_KEY,
            host=config.LANGFUSE_HOST,
        )
        return _langfuse
    except Exception as e:
        print(f"Warning: Langfuse not available: {e}")
        return None


def create_trace(name: str, metadata: Optional[dict] = None) -> Optional[object]:
    """Create a new Langfuse trace."""
    lf = get_langfuse()
    if not lf:
        return None
    try:
        trace = lf.trace(
            name=name,
            metadata=metadata or {},
        )
        return trace
    except Exception as e:
        print(f"Warning: Could not create trace: {e}")
        return None


def log_llm_call(result: dict, metadata: dict):
    """Log an LLM call to Langfuse with cost attribution."""
    lf = get_langfuse()
    if not lf:
        return

    try:
        trace = lf.trace(
            name=metadata.get("trace_name", "llm_call"),
            metadata=metadata,
        )

        trace.generation(
            name=metadata.get("generation_name", "chat_completion"),
            model=result.get("model", "unknown"),
            input=metadata.get("input", ""),
            output=result.get("content", ""),
            usage={
                "input": result["usage"]["prompt_tokens"],
                "output": result["usage"]["completion_tokens"],
                "total": result["usage"]["total_tokens"],
                "unit": "TOKENS",
            },
            metadata={
                "latency_ms": result.get("latency_ms", 0),
                "cost_usd": result.get("cost_usd", 0),
            },
        )
    except Exception as e:
        print(f"Warning: Langfuse logging failed: {e}")


def log_enrichment_trace(prospect_name: str, brief_data: dict, latency_ms: int):
    """Log an enrichment pipeline run to Langfuse."""
    lf = get_langfuse()
    if not lf:
        return

    try:
        trace = lf.trace(
            name="enrichment_pipeline",
            metadata={
                "prospect": prospect_name,
                "latency_ms": latency_ms,
                "signals_found": len([k for k, v in brief_data.items()
                                     if isinstance(v, dict) and v.get("confidence") == "high"]),
            },
        )
        trace.event(
            name="enrichment_complete",
            metadata=brief_data,
        )
    except Exception as e:
        print(f"Warning: Langfuse enrichment trace failed: {e}")


def log_outreach_trace(
    prospect_name: str,
    policy_decision_id: str,
    variant: str,
    tone_score: float,
    email_sent: bool,
    cost_usd: float,
    latency_ms: int,
):
    """Log a complete outreach cycle to Langfuse."""
    lf = get_langfuse()
    if not lf:
        return

    try:
        trace = lf.trace(
            name="outreach_cycle",
            metadata={
                "prospect": prospect_name,
                "policy_decision_id": policy_decision_id,
                "variant": variant,
                "tone_score": tone_score,
                "email_sent": email_sent,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
            },
        )
    except Exception as e:
        print(f"Warning: Langfuse outreach trace failed: {e}")


def flush():
    """Flush pending Langfuse events."""
    lf = get_langfuse()
    if lf:
        try:
            lf.flush()
        except Exception:
            pass
