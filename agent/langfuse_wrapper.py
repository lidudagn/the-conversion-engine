"""
Langfuse Observability Wrapper
Per-trace cost attribution for every LLM call and enrichment cycle.
Compatible with Langfuse SDK v4.x.
"""

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
        if not config.LANGFUSE_PUBLIC_KEY or not config.LANGFUSE_SECRET_KEY:
            return None
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
    """Create a Langfuse span (trace). Returns span or None."""
    lf = get_langfuse()
    if not lf:
        return None
    try:
        span = lf.start_observation(name=name, metadata=metadata or {})
        return span
    except Exception as e:
        print(f"Warning: Could not create trace: {e}")
        return None


def log_llm_call(result: dict, metadata: dict) -> None:
    """Log an LLM call to Langfuse with cost attribution."""
    lf = get_langfuse()
    if not lf:
        return
    try:
        usage = result.get("usage", {})
        span = lf.start_observation(
            name=metadata.get("generation_name", "chat_completion"),
            as_type="generation",
            input=metadata.get("input", ""),
            output=result.get("content", ""),
            model=result.get("model", "unknown"),
            usage_details={
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0),
            },
            cost_details={"total": result.get("cost_usd", 0)},
            metadata={
                **metadata,
                "latency_ms": result.get("latency_ms", 0),
            },
        )
        span.end()
    except Exception as e:
        print(f"Warning: Langfuse LLM logging failed: {e}")


def log_enrichment_trace(prospect_name: str, brief_data: dict, latency_ms: int) -> Optional[str]:
    """Log an enrichment pipeline run to Langfuse. Returns trace context string."""
    lf = get_langfuse()
    if not lf:
        return None
    try:
        icp_segment = None
        ai_score = None
        if isinstance(brief_data, dict):
            seg = brief_data.get("icp_segment", {})
            icp_segment = seg.get("primary") if isinstance(seg, dict) else None
            ai = brief_data.get("ai_maturity", {})
            ai_score = ai.get("score") if isinstance(ai, dict) else None

        span = lf.start_observation(
            name="enrichment_pipeline",
            as_type="span",
            input={"prospect": prospect_name},
            output={"icp_segment": icp_segment, "ai_maturity_score": ai_score},
            metadata={
                "latency_ms": latency_ms,
                "timestamp": datetime.now().isoformat(),
            },
        )
        span.end()
        return str(id(span))
    except Exception as e:
        print(f"Warning: Langfuse enrichment trace failed: {e}")
        return None


def log_outreach_trace(
    prospect_name: str,
    policy_decision_id: str,
    variant: str,
    tone_score: float,
    email_sent: bool,
    cost_usd: float,
    latency_ms: int,
) -> Optional[str]:
    """Log a complete outreach cycle to Langfuse."""
    lf = get_langfuse()
    if not lf:
        return None
    try:
        span = lf.start_observation(
            name="outreach_cycle",
            as_type="span",
            input={"prospect": prospect_name, "variant": variant},
            output={"email_sent": email_sent, "tone_score": tone_score},
            metadata={
                "policy_decision_id": policy_decision_id,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "timestamp": datetime.now().isoformat(),
            },
        )
        span.end()
        return str(id(span))
    except Exception as e:
        print(f"Warning: Langfuse outreach trace failed: {e}")
        return None


def flush() -> None:
    """Flush pending Langfuse events."""
    lf = get_langfuse()
    if lf:
        try:
            lf.flush()
        except Exception:
            pass
