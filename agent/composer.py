"""
Signal-Grounded Email Composer — Policy-Aware
Composes outreach emails constrained by PolicyDecision.

Signal Usage Contract: only uses signals classified as assertable or question.
Competitor gap delivery follows gap_delivery_mode (direct/soft).
Contradiction framings injected when detected.
"""

import json
from typing import Optional

from agent.policy_engine import PolicyDecision
from agent.enrichment.pipeline import HiringSignalBrief
from agent.enrichment.competitor_gap import CompetitorGapBrief


class EmailDraft(object):
    """A composed email draft."""
    def __init__(self, subject: str, body: str, variant: str,
                 signals_used: list, policy_decision_id: str):
        self.subject = subject
        self.body = body
        self.variant = variant  # "signal_grounded" | "exploratory" | "abstention"
        self.signals_used = signals_used
        self.policy_decision_id = policy_decision_id


class EmailComposer:
    """
    Compose signal-grounded outreach emails.

    Flow: PolicyDecision + Brief → Draft → ToneGuard → Final

    Signal Usage Contract:
        Every signal referenced in the email MUST be in
        policy.assertable_signals OR policy.question_signals.
        Violation = blocked by tone guard.
    """

    def __init__(self, llm_client=None, style_guide: str = ""):
        self.llm_client = llm_client
        self.style_guide = style_guide

    async def compose(
        self,
        policy: PolicyDecision,
        brief: HiringSignalBrief,
        gap_brief: Optional[CompetitorGapBrief] = None,
        prospect_name: str = "",
        sender_name: str = "Tenacious Team",
    ) -> EmailDraft:
        """Compose an email constrained by the policy decision."""

        if policy.abstain:
            return self._compose_abstention(policy, brief, prospect_name)

        # Build signal sections
        signal_sections = self._build_signal_sections(policy, brief)
        gap_section = self._build_gap_section(policy, gap_brief) if policy.use_competitor_gap else ""
        contradiction_section = self._build_contradiction_section(policy)

        # Determine email variant
        variant = "signal_grounded"

        if self.llm_client:
            return await self._llm_compose(
                policy, brief, signal_sections, gap_section,
                contradiction_section, prospect_name, sender_name, variant
            )
        else:
            return self._template_compose(
                policy, brief, signal_sections, gap_section,
                contradiction_section, prospect_name, sender_name, variant
            )

    def _build_signal_sections(self, policy: PolicyDecision, brief: HiringSignalBrief) -> dict:
        """Build signal sections respecting the signal usage contract."""
        sections = {}

        for signal_name in policy.assertable_signals:
            data = getattr(brief, signal_name, None)
            if data is None:
                data = brief.model_dump().get(signal_name, {})
            sections[signal_name] = {"mode": "assert", "data": data}

        for signal_name in policy.question_signals:
            data = getattr(brief, signal_name, None)
            if data is None:
                data = brief.model_dump().get(signal_name, {})
            sections[signal_name] = {"mode": "question", "data": data}

        # SIGNAL USAGE CONTRACT: verify no omitted signals leak through
        for signal_name in policy.omit_signals:
            assert signal_name not in sections, \
                f"Signal usage contract violation: {signal_name} is omitted but in draft"

        return sections

    def _build_gap_section(self, policy: PolicyDecision, gap_brief: Optional[CompetitorGapBrief]) -> str:
        """Build competitor gap section with correct delivery mode."""
        if not gap_brief or not gap_brief.gaps:
            return ""

        top_gap = gap_brief.gaps[0]  # Most relevant gap

        if policy.gap_delivery_mode == "direct":
            return (
                f"Companies at your stage in {gap_brief.prospect_sector} are investing in "
                f"{top_gap.practice.lower()} — {top_gap.top_quartile_prevalence} of the "
                f"top quartile show public signal for this. We can help you close that gap."
            )
        else:  # "soft"
            return (
                f"Some companies at a similar stage are starting to invest in "
                f"{top_gap.practice.lower()} — not sure if that's relevant for you, "
                f"but worth comparing notes."
            )

    def _build_contradiction_section(self, policy: PolicyDecision) -> str:
        """Build contradiction framing if detected."""
        if not policy.contradictions:
            return ""
        # Use the first high-confidence contradiction
        return policy.contradictions[0].get("framing", "")

    def _compose_abstention(
        self, policy: PolicyDecision, brief: HiringSignalBrief, prospect_name: str
    ) -> EmailDraft:
        """Compose a strong abstention email (not generic)."""
        from agent.icp_classifier import ABSTENTION_TEMPLATE

        # Build best available hedged observation
        observations = []
        for signal_name in policy.question_signals:
            data = brief.model_dump().get(signal_name, {})
            if isinstance(data, dict) and data.get("event") or data.get("open_roles"):
                observations.append(signal_name)

        hedged = "you might be exploring some changes"
        if observations:
            hedged = "you might be thinking about scaling your team"

        body = ABSTENTION_TEMPLATE.format(
            company=prospect_name or brief.prospect_name,
            hedged_observation=hedged,
            relevant_capability="engineering capacity and delivery",
        )

        return EmailDraft(
            subject=f"Quick thought for {prospect_name or brief.prospect_name}",
            body=body,
            variant="abstention",
            signals_used=policy.question_signals[:2],
            policy_decision_id=policy.decision_id,
        )

    def _template_compose(
        self, policy, brief, signal_sections, gap_section,
        contradiction_section, prospect_name, sender_name, variant
    ) -> EmailDraft:
        """Template-based composition (no LLM needed)."""

        company = prospect_name or brief.prospect_name
        subject = f"Quick thought on scaling at {company}"

        # Build body from sections
        parts = [f"Hi,\n"]

        # Lead with contradiction if available (wow factor)
        if contradiction_section:
            parts.append(contradiction_section + "\n")

        # Add signal-grounded observations
        for signal_name, section in signal_sections.items():
            data = section["data"]
            mode = section["mode"]

            if signal_name == "funding" and isinstance(data, dict) and data.get("event"):
                if mode == "assert":
                    parts.append(f"I noticed {company} {data['event']}.")
                else:
                    parts.append(f"It looks like {company} may have recently raised — is that right?")

            elif signal_name == "job_velocity" and isinstance(data, dict):
                roles = data.get("open_roles", 0)
                if roles > 0:
                    if mode == "assert":
                        parts.append(f"You have {roles} open engineering roles right now.")
                    else:
                        parts.append(f"It looks like you might be in a hiring push?")

        # Add gap section
        if gap_section:
            parts.append("\n" + gap_section)

        # Call to action
        parts.append(
            "\nWould a 30-minute conversation be worth your time? "
            "Happy to share what we're seeing from teams in a similar position."
        )

        parts.append(f"\nBest,\n{sender_name}")

        body = "\n".join(parts)
        signals_used = list(signal_sections.keys())

        return EmailDraft(
            subject=subject,
            body=body,
            variant=variant,
            signals_used=signals_used,
            policy_decision_id=policy.decision_id,
        )

    async def _llm_compose(
        self, policy, brief, signal_sections, gap_section,
        contradiction_section, prospect_name, sender_name, variant
    ) -> EmailDraft:
        """LLM-based composition with policy constraints in prompt."""
        prompt = f"""Compose a cold outreach email for {prospect_name or brief.prospect_name}.

STYLE GUIDE: {self.style_guide}

TONE MODE: {policy.tone_mode}
- assertive: state facts confidently
- suggestive: use qualifying language ("it seems", "others in your space")
- exploratory: ask questions, don't assert

SIGNALS YOU MAY STATE AS FACT:
{json.dumps({k: v['data'] for k, v in signal_sections.items() if v['mode'] == 'assert'}, indent=2, default=str)}

SIGNALS YOU MUST PHRASE AS QUESTIONS:
{json.dumps({k: v['data'] for k, v in signal_sections.items() if v['mode'] == 'question'}, indent=2, default=str)}

{'CONTRADICTION TO LEAD WITH:' if contradiction_section else ''}
{contradiction_section}

{'COMPETITOR GAP INSIGHT (use this delivery mode: ' + policy.gap_delivery_mode + '):' if gap_section else ''}
{gap_section}

RULES:
- Do NOT mention signals not listed above
- Do NOT assert anything from the question-only list
- Keep under 150 words
- End with a specific CTA (30-minute call)
- Sign as {sender_name}
- Mark as draft
"""
        try:
            response = await self.llm_client.chat.completions.create(
                model="qwen/qwen3-235b-a22b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            body = response.choices[0].message.content
        except Exception:
            # Fallback to template
            return self._template_compose(
                policy, brief, signal_sections, gap_section,
                contradiction_section, prospect_name, sender_name, variant
            )

        return EmailDraft(
            subject=f"Quick thought on scaling at {prospect_name}",
            body=body,
            variant=variant,
            signals_used=list(signal_sections.keys()),
            policy_decision_id=policy.decision_id,
        )
