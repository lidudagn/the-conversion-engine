"""
Plan-Execute-Verify (PEV) Agent for τ²-Bench
Addresses the primary failure mode: multi-step write operation sequencing.

Two variants:
  pev_v1  — Verify-only: adds read-before-write and per-step confirmation
  pev_v2  — Full PEV: adds explicit UNDERSTAND/PLAN/EXECUTE/VERIFY/CONFIRM cycle

Registered with tau2 registry as "pev_v1" and "pev_v2".
Both use the same SYSTEM_PROMPT template as LLMAgent, only AGENT_INSTRUCTION differs.
This means the only independent variable across V0/V1/V2 is instruction content.

Prompt-length note (limitation documented in method.md):
  V0  original: ~60 tokens
  V1  verify-only: ~100 tokens (+40)
  V2  full PEV:  ~210 tokens (+150)
Length difference is a named confound; not controlled by padding because
padding would introduce instruction-density confound instead (see method.md §4.2).
"""

import sys
from pathlib import Path

TAU2_SRC = Path(__file__).parent / "tau2-bench" / "src"
if str(TAU2_SRC) not in sys.path:
    sys.path.insert(0, str(TAU2_SRC))

from tau2.agent.llm_agent import LLMAgent, SYSTEM_PROMPT  # noqa: E402


# ─── Variant instructions ─────────────────────────────────────────────────────

_V0_INSTRUCTION = """You are a customer service agent that helps the user according to the \
<policy> provided below.
In each turn you can either:
- Send a message to the user.
- Make a tool call.
You cannot do both at the same time.

Try to be helpful and always follow the policy. Always make sure you generate valid JSON only."""


_V1_INSTRUCTION = """You are a customer service agent that helps the user according to the \
<policy> provided below.
In each turn you can either:
- Send a message to the user.
- Make a tool call.
You cannot do both at the same time.

IMPORTANT — Before modifying any order or account:
1. Always look up the current state first using the appropriate read tool \
(get_order_details, get_user_details, get_product_details).
2. After each change, confirm the tool call returned the expected result before \
proceeding or responding to the customer.
3. Only tell the customer an operation is complete after you have confirmed it succeeded.

Try to be helpful and always follow the policy. Always make sure you generate valid JSON only."""


_V2_INSTRUCTION = """You are a customer service agent that helps the user according to the \
<policy> provided below.
In each turn you can either:
- Send a message to the user.
- Make a tool call.
You cannot do both at the same time.

For every request that requires changing order or account state, follow this cycle:

UNDERSTAND — Identify exactly what the customer wants changed \
(specific item IDs, quantities, payment methods).

VERIFY — Use read tools to confirm the current state BEFORE making any changes. \
Call get_order_details, get_product_details, or get_user_details as needed.

PLAN — Identify the exact sequence of write tool calls required. \
For multi-step operations (exchange + cancel, multiple items), list each step.

EXECUTE — Follow your plan step by step. Complete one operation before starting the next.

CONFIRM — After each tool call, check the result. If a step fails, stop and explain \
the specific problem to the customer instead of skipping ahead.

Only tell the customer the full operation is complete after you have confirmed every step.

Try to be helpful and always follow the policy. Always make sure you generate valid JSON only."""


_V3_INSTRUCTION = """You are a customer service agent that helps the user according to the \
<policy> provided below.
In each turn you can either:
- Send a message to the user.
- Make a tool call.
You cannot do both at the same time.

IMPORTANT — When handling order or account changes:
1. Always look up the current state first (get_order_details, get_user_details, \
get_product_details) before making any change.
2. When the customer has approved an action, execute it immediately using the tool. \
Do NOT ask the customer again to confirm — just call the tool.
3. After each tool call, check the result yourself. If it succeeded, tell the customer. \
If it failed, explain the specific problem.
4. For multi-step operations, complete each step fully before starting the next.

Try to be helpful and always follow the policy. Always make sure you generate valid JSON only."""


# ─── Agent classes ─────────────────────────────────────────────────────────────

class PEVV1Agent(LLMAgent):
    """Verify-only variant: adds read-before-write + per-step confirmation."""

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(
            domain_policy=self.domain_policy,
            agent_instruction=_V1_INSTRUCTION,
        )


class PEVV2Agent(LLMAgent):
    """Full PEV variant: adds UNDERSTAND/VERIFY/PLAN/EXECUTE/CONFIRM cycle."""

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(
            domain_policy=self.domain_policy,
            agent_instruction=_V2_INSTRUCTION,
        )


class PEVV3Agent(LLMAgent):
    """Execute-first variant: fixes confirmation anti-pattern from V1/V2."""

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(
            domain_policy=self.domain_policy,
            agent_instruction=_V3_INSTRUCTION,
        )


# ─── Factory functions ─────────────────────────────────────────────────────────

def create_pev_v1_agent(tools, domain_policy, **kwargs):
    return PEVV1Agent(
        tools=tools,
        domain_policy=domain_policy,
        llm=kwargs.get("llm"),
        llm_args=kwargs.get("llm_args"),
    )


def create_pev_v2_agent(tools, domain_policy, **kwargs):
    return PEVV2Agent(
        tools=tools,
        domain_policy=domain_policy,
        llm=kwargs.get("llm"),
        llm_args=kwargs.get("llm_args"),
    )


def create_pev_v3_agent(tools, domain_policy, **kwargs):
    return PEVV3Agent(
        tools=tools,
        domain_policy=domain_policy,
        llm=kwargs.get("llm"),
        llm_args=kwargs.get("llm_args"),
    )


def register_pev_agents():
    """Register PEV variants with the tau2 registry. Safe to call multiple times."""
    from tau2.registry import registry
    existing = registry.get_agents()
    if "pev_v1" not in existing:
        registry.register_agent_factory(create_pev_v1_agent, "pev_v1")
    if "pev_v2" not in existing:
        registry.register_agent_factory(create_pev_v2_agent, "pev_v2")
    if "pev_v3" not in existing:
        registry.register_agent_factory(create_pev_v3_agent, "pev_v3")


# ─── Instruction metadata ──────────────────────────────────────────────────────

VARIANT_META = {
    "V0": {
        "agent_name": "llm_agent",
        "instruction": _V0_INSTRUCTION,
        "approx_tokens": 60,
        "description": "Baseline — original AGENT_INSTRUCTION, no sequencing guidance",
    },
    "V3": {
        "agent_name": "pev_v3",
        "instruction": _V3_INSTRUCTION,
        "approx_tokens": 95,
        "description": "Execute-first — fixes confirmation anti-pattern; execute on approval, verify internally",
    },
    "V1": {
        "agent_name": "pev_v1",
        "instruction": _V1_INSTRUCTION,
        "approx_tokens": 100,
        "description": "Verify-only — adds read-before-write + per-step confirmation",
    },
    "V2": {
        "agent_name": "pev_v2",
        "instruction": _V2_INSTRUCTION,
        "approx_tokens": 210,
        "description": "Full PEV — adds UNDERSTAND/VERIFY/PLAN/EXECUTE/CONFIRM cycle",
    },
}
