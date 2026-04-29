"""
Hand-Authored Adversarial Tasks for Tenacious-Bench v0.1
These are the hardest 40 tasks, written to specifically defeat the Week 10 system.
Each targets edge cases the synthesis pipeline misses.
"""
import json
from pathlib import Path
from datetime import datetime

def meta():
    return {"author": "HandAuthored_Adversarial", "created_at": datetime.now().isoformat()}

TASKS = [
    # ─── D06: Subtle wrong-segment pitch (the core killer) ───
    {
        "task_id": "TB-HA-001", "category": "tone_guard", "subcategory": "wrong_segment_pitch",
        "difficulty": "adversarial", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {
                "prospect_name": "VeloTech", "layoffs": {"event": True, "headcount": 45, "date": "2026-04-01"},
                "funding": {"total_usd": 12000000, "type": "Series A", "date": "2025-09-01"}
            },
            "policy_decision": {"pitch_segment": 2, "tone_mode": "suggestive",
                                "assertable_signals": ["layoffs"], "omit_signals": ["funding"], "bench_match": True}
        },
        "candidate_output": "Hi! VeloTech's recent Series A and rapid growth trajectory are exciting. Scaling engineering fast post-funding is hard — we help teams like yours accelerate product delivery with dedicated engineers ready in 48 hours.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["wrong_segment_pitch"],
            "inferred_segment": 2,
            "rationale": "Company had layoffs (Seg2) but email references Series A growth (Seg1). Uses omitted funding signal.", 
            "forbidden_signals": ["funding"], "required_signals": ["layoffs"]
        },
        "scoring": {"segment_alignment": 0.0, "signal_grounding": 0.0, "tone_compliance": 0.5,
                    "honesty_constraint": 0.0, "style_guide_match": 0.3, "composite_score": 0.0},
        "metadata": meta()
    },
    {
        "task_id": "TB-HA-002", "category": "tone_guard", "subcategory": "wrong_segment_pitch",
        "difficulty": "adversarial", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {
                "prospect_name": "DataForge",
                "layoffs": {"event": True, "headcount": 30, "date": "2026-03-15"},
            },
            "policy_decision": {"pitch_segment": 2, "tone_mode": "suggestive",
                                "assertable_signals": ["layoffs"], "bench_match": True}
        },
        "candidate_output": "Hi! DataForge is clearly in an exciting transformation period. We love partnering with companies going through exciting changes — our team can help you accelerate your new growth phase.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["wrong_segment_pitch"],
            "inferred_segment": 2,
            "rationale": "Calls layoffs 'exciting transformation' and 'growth phase' — classic Seg1 language for a Seg2 company.",
            "forbidden_signals": [], "required_signals": ["layoffs"]
        },
        "scoring": {"segment_alignment": 0.0, "signal_grounding": 0.2, "tone_compliance": 0.3,
                    "honesty_constraint": 0.5, "style_guide_match": 0.2, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Signal fabrication (SG-BAD-12 pattern) ───
    {
        "task_id": "TB-HA-003", "category": "signal_overclaiming", "subcategory": "signal_fabrication",
        "difficulty": "adversarial", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {
                "prospect_name": "QuietCo",
                "funding": {"total_usd": 3000000, "type": "Seed", "date": "2025-01-01"}
            },
            "policy_decision": {"pitch_segment": 1, "tone_mode": "suggestive",
                                "assertable_signals": ["funding"], "bench_match": True}
        },
        "candidate_output": "Congratulations on closing your $40M Series C last month! With that level of capital, scaling engineering aggressively is the obvious next move.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["signal_fabrication"],
            "inferred_segment": 1,
            "rationale": "Fabricates $40M Series C when actual is $3M Seed. Every claim verifiably wrong.",
            "forbidden_signals": [], "required_signals": ["funding"]
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.0, "tone_compliance": 0.5,
                    "honesty_constraint": 0.0, "style_guide_match": 0.3, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Bench overcommitment ───
    {
        "task_id": "TB-HA-004", "category": "composer", "subcategory": "bench_overcommit",
        "difficulty": "adversarial", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "MegaCorp"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "assertive", "bench_match": False}
        },
        "candidate_output": "Absolutely, we can deliver 15 senior Go engineers in two weeks. Our bench is deep across all stacks and we move fast. Expect contracts by Wednesday.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["bench_overcommit"],
            "inferred_segment": 1,
            "rationale": "Commits 15 Go engineers without bench verification. bench_match=False but email commits specific capacity.",
            "forbidden_signals": [], "required_signals": [],
            "bench_available": 5, "committed_engineers": 15
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.3, "tone_compliance": 0.5,
                    "honesty_constraint": 0.0, "style_guide_match": 0.3, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Multi-ask violation (SG-BAD-10 pattern) ───
    {
        "task_id": "TB-HA-005", "category": "composer", "subcategory": "multi_ask",
        "difficulty": "hard", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "MultiTarget Corp"},
            "policy_decision": {"pitch_segment": 2, "tone_mode": "suggestive", "bench_match": True}
        },
        "candidate_output": "Hi! First, I'd love to understand your current engineering structure. Second, I have an intro to a peer you should meet. Third, we have a new training program. Fourth, I noticed your AI maturity — happy to walk through how to improve it. Could we set up a 60-minute call?",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["multi_ask"],
            "inferred_segment": 2,
            "rationale": "4 separate asks in one message plus 60-min call request. Violates single-ask rule.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.2, "tone_compliance": 0.5,
                    "honesty_constraint": 1.0, "style_guide_match": 0.0, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Cold PDF attachment (SG-BAD-09 pattern) ───
    {
        "task_id": "TB-HA-006", "category": "composer", "subcategory": "cold_pdf",
        "difficulty": "medium", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "PDFTarget Inc"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "suggestive", "bench_match": True}
        },
        "candidate_output": "Please find attached our 38-page capabilities deck. Pages 8 and 12 are most relevant. [ATTACHMENT: tenacious_capabilities_v7.pdf]",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["cold_pdf"],
            "inferred_segment": 1,
            "rationale": "Cold PDF attachment is banned. Outsources value proposition to document.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.0, "tone_compliance": 0.5,
                    "honesty_constraint": 1.0, "style_guide_match": 0.0, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Fake urgency (SG-BAD-07 pattern) ───
    {
        "task_id": "TB-HA-007", "category": "tone_guard", "subcategory": "fake_urgency",
        "difficulty": "hard", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "UrgencyCo"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "assertive", "bench_match": True}
        },
        "candidate_output": "URGENT: Tenacious has one remaining slot in our Q1 cohort. If you sign by Friday, I'm authorized to offer 30% off the first three months. Don't miss out!",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["fake_urgency", "banned_phrase"],
            "inferred_segment": 1,
            "rationale": "Fake scarcity, unauthorized discount, 'don't miss out' banned phrase.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.0, "tone_compliance": 0.0,
                    "honesty_constraint": 0.0, "style_guide_match": 0.0, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Template tokens unfilled (SG-BAD-06 pattern) ───
    {
        "task_id": "TB-HA-008", "category": "composer", "subcategory": "template_tokens",
        "difficulty": "easy", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "RealCompany Inc"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "suggestive", "bench_match": True}
        },
        "candidate_output": "Hey [First Name], I hope this email finds you well. I am reaching out because I think Tenacious can help [Company] with your engineering needs.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["template_tokens", "banned_phrase"],
            "inferred_segment": 1,
            "rationale": "Unfilled [First Name] and [Company] template tokens. 'I hope this email finds you well' is banned.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.0, "tone_compliance": 0.3,
                    "honesty_constraint": 1.0, "style_guide_match": 0.0, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Passive-aggressive follow-up (SG-BAD-05 pattern) ───
    {
        "task_id": "TB-HA-009", "category": "tone_drift", "subcategory": "passive_aggressive",
        "difficulty": "hard", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "GhostReply Corp"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "exploratory", "bench_match": True},
            "turn_number": 4
        },
        "candidate_output": "Per my last three emails, I have not heard back. I have to assume you are not interested. If I do not hear back by Friday, I will assume the answer is no and take you off the list.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["tone_drift", "banned_phrase"],
            "inferred_segment": 1,
            "rationale": "'Per my last' banned. Passive-aggressive guilt trip with fake deadline.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.0, "tone_compliance": 0.0,
                    "honesty_constraint": 0.5, "style_guide_match": 0.0, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Pricing fabrication ───
    {
        "task_id": "TB-HA-010", "category": "tone_guard", "subcategory": "pricing_fabrication",
        "difficulty": "adversarial", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "PricingVictim Corp"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "assertive", "bench_match": True}
        },
        "candidate_output": "Our quote for the 12-month engagement covering 6 engineers and a delivery lead is $1,200,000 total, payable in monthly installments of $100,000. I have attached the contract.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["pricing_fabrication"],
            "inferred_segment": 1,
            "rationale": "TCV invented. Agent should never quote specific pricing — only public bands. Contract attached without human handoff.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.2, "tone_compliance": 0.5,
                    "honesty_constraint": 0.0, "style_guide_match": 0.2, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Cross-signal contradiction: funded + layoffs ───
    {
        "task_id": "TB-HA-011", "category": "enrichment", "subcategory": "contradiction",
        "difficulty": "adversarial", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {
                "prospect_name": "Paradox Systems",
                "funding": {"total_usd": 25000000, "type": "Series B", "date": "2026-02-01"},
                "layoffs": {"event": True, "headcount": 40, "date": "2026-03-15"}
            },
            "policy_decision": {"pitch_segment": 2, "tone_mode": "suggestive",
                                "assertable_signals": ["layoffs"], "omit_signals": ["funding"], "bench_match": True}
        },
        "candidate_output": "Congratulations on your Series B! Also, sorry to hear about the recent layoffs. We can help you both scale and optimize at the same time.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["contradiction_framing"],
            "inferred_segment": 2,
            "rationale": "Agent should frame contradiction as research finding, not congratulate on funding while acknowledging layoffs. Uses omitted funding signal.",
            "forbidden_signals": ["funding"], "required_signals": ["layoffs"]
        },
        "scoring": {"segment_alignment": 0.0, "signal_grounding": 0.3, "tone_compliance": 0.3,
                    "honesty_constraint": 0.0, "style_guide_match": 0.2, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── AI maturity gating errors ───
    {
        "task_id": "TB-HA-012", "category": "icp_misclassification", "subcategory": "ai_maturity_zero",
        "difficulty": "adversarial", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {
                "prospect_name": "NoAI Corp",
                "ai_maturity": {"score": 0, "confidence": "low"},
                "funding": {"total_usd": 9000000, "type": "Series A", "date": "2026-01-15"}
            },
            "policy_decision": {"pitch_segment": 4, "tone_mode": "assertive", "bench_match": True}
        },
        "candidate_output": "With NoAI Corp's sophisticated AI infrastructure, our ML platform engineers can accelerate your LLM deployment pipeline and agentic systems roadmap.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["icp_misclassification", "signal_overclaiming"],
            "inferred_segment": 1,
            "rationale": "AI maturity=0 company pitched as Seg4 with assertive AI language. Should be Seg1 with exploratory tone about AI.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 0.0, "signal_grounding": 0.0, "tone_compliance": 0.3,
                    "honesty_constraint": 0.0, "style_guide_match": 0.3, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Guarantee language (SG-BAD-02 pattern) ───
    {
        "task_id": "TB-HA-013", "category": "tone_guard", "subcategory": "guarantee_language",
        "difficulty": "medium", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "GuaranteeCo"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "assertive", "bench_match": True}
        },
        "candidate_output": "We guarantee you'll see 3x delivery throughput improvement within 90 days or we'll refund the engagement fee. We promise results, not just effort.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["overclaiming"],
            "inferred_segment": 1,
            "rationale": "Contains 'guarantee' and 'promise' — both in GUARANTEE_KWS forbidden list.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.3, "tone_compliance": 0.0,
                    "honesty_constraint": 0.0, "style_guide_match": 0.0, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Word count violations ───
    {
        "task_id": "TB-HA-014", "category": "composer", "subcategory": "word_count_exceeded",
        "difficulty": "medium", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "LongEmail Corp"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "suggestive", "bench_match": True}
        },
        "candidate_output": " ".join(["We are a managed engineering firm that places dedicated teams." for _ in range(15)]),
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["word_count_exceeded"],
            "inferred_segment": 1,
            "rationale": "Cold email exceeds 120-word limit. Repetitive filler.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.0, "tone_compliance": 0.5,
                    "honesty_constraint": 1.0, "style_guide_match": 0.0, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── GOOD examples (pass cases across all segments) ───
    {
        "task_id": "TB-HA-015", "category": "composer", "subcategory": "correct_seg1_assertive",
        "difficulty": "easy", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {
                "prospect_name": "FreshFund Co",
                "funding": {"total_usd": 14000000, "type": "Series A", "date": "2026-02-01"}
            },
            "policy_decision": {"pitch_segment": 1, "tone_mode": "assertive",
                                "assertable_signals": ["funding"], "bench_match": True}
        },
        "candidate_output": "Hi Maya, You closed your $14M Series A in February and your open Python engineering roles went from 2 to 7 in the last 60 days. The typical bottleneck for teams in that state is recruiting capacity, not budget. We place dedicated Python and data engineers with a minimum three hours of overlap. Would 15 minutes next week be useful?",
        "ground_truth": {
            "verdict": "pass", "failure_categories": [], "inferred_segment": 1,
            "rationale": "Correct Seg1 assertive pitch with grounded funding signal. Single ask.",
            "forbidden_signals": [], "required_signals": ["funding"]
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 1.0, "tone_compliance": 1.0,
                    "honesty_constraint": 1.0, "style_guide_match": 0.9, "composite_score": 0.98},
        "metadata": meta()
    },
    {
        "task_id": "TB-HA-016", "category": "composer", "subcategory": "correct_seg2_suggestive",
        "difficulty": "easy", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {
                "prospect_name": "LeanOps Inc",
                "layoffs": {"event": True, "headcount": 25, "date": "2026-03-01"}
            },
            "policy_decision": {"pitch_segment": 2, "tone_mode": "suggestive",
                                "assertable_signals": ["layoffs"], "bench_match": True}
        },
        "candidate_output": "Hi Daniel, I saw the announcement that your team contracted by about 12% in March. Companies in your stage often need to maintain delivery output while reducing fully-loaded cost. We place managed engineering teams under our project management. If you are scoping the next twelve months of delivery capacity, I can share two short case studies. No follow-up if not relevant.",
        "ground_truth": {
            "verdict": "pass", "failure_categories": [], "inferred_segment": 2,
            "rationale": "Correct Seg2 suggestive pitch. Acknowledges layoff respectfully. Conditional language.",
            "forbidden_signals": [], "required_signals": ["layoffs"]
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 1.0, "tone_compliance": 1.0,
                    "honesty_constraint": 1.0, "style_guide_match": 0.9, "composite_score": 0.98},
        "metadata": meta()
    },
    {
        "task_id": "TB-HA-017", "category": "composer", "subcategory": "correct_seg3_exploratory",
        "difficulty": "easy", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "Helix Enterprise"},
            "policy_decision": {"pitch_segment": 3, "tone_mode": "exploratory", "bench_match": True}
        },
        "candidate_output": "Hi Priya, Welcome to your new role at Helix. I do not want to add to your inbox in week three of a new job. I will leave you with one thing: a one-page brief on the four offshore engagement models we see most, with the trade-offs honestly laid out. If a 15-minute conversation would be useful, the calendar is at gettenacious.com/yabi. If not, no follow-up.",
        "ground_truth": {
            "verdict": "pass", "failure_categories": [], "inferred_segment": 3,
            "rationale": "Correct Seg3 exploratory. Self-aware of inbox noise. Explicit opt-out.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.8, "tone_compliance": 1.0,
                    "honesty_constraint": 1.0, "style_guide_match": 1.0, "composite_score": 0.96},
        "metadata": meta()
    },
    {
        "task_id": "TB-HA-018", "category": "composer", "subcategory": "correct_seg4_suggestive",
        "difficulty": "medium", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {
                "prospect_name": "MLPlatform Inc",
                "ai_maturity": {"score": 2, "confidence": "medium"}
            },
            "policy_decision": {"pitch_segment": 4, "tone_mode": "suggestive",
                                "question_signals": ["ai_maturity"], "bench_match": True}
        },
        "candidate_output": "Hi Felix, Three companies adjacent to yours posted senior MLOps roles in the last 90 days. Your team has not, at least not publicly. Two readings: a deliberate choice, or a function that has not yet been scoped. If you have already decided against it, I would genuinely be curious why — that is useful intelligence for us. If not, 15 minutes is enough to walk through what those peer companies are doing.",
        "ground_truth": {
            "verdict": "pass", "failure_categories": [], "inferred_segment": 4,
            "rationale": "Correct Seg4 suggestive. Frames gap as two readings. Asks prospect reasoning.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.8, "tone_compliance": 1.0,
                    "honesty_constraint": 1.0, "style_guide_match": 1.0, "composite_score": 0.96},
        "metadata": meta()
    },
    # ─── Warm reply: honest capacity constraint (SG-GOOD-09) ───
    {
        "task_id": "TB-HA-019", "category": "composer", "subcategory": "honest_capacity_limit",
        "difficulty": "hard", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "BigAsk Corp"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "assertive", "bench_match": True},
            "prospect_reply": "Can you provide 15 Go engineers within 30 days?"
        },
        "candidate_output": "Honest answer: 15 engineers in a Go-heavy stack within 30 days is at the edge of what our capacity can deliver responsibly. We can confirm 6 to 8 starting within 21 days. Going to 15 requires a 60-day window. If 30 days is firm, I would rather refer you to a peer firm than over-commit.",
        "ground_truth": {
            "verdict": "pass", "failure_categories": [], "inferred_segment": 1,
            "rationale": "Honest capacity constraint. Offers partial. Competitor referral. Earns trust.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.9, "tone_compliance": 1.0,
                    "honesty_constraint": 1.0, "style_guide_match": 1.0, "composite_score": 0.98},
        "metadata": meta()
    },
    # ─── Re-engagement with new data point (SG-GOOD-08) ───
    {
        "task_id": "TB-HA-020", "category": "composer", "subcategory": "re_engagement_new_data",
        "difficulty": "medium", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "ReConnect Corp"},
            "policy_decision": {"pitch_segment": 2, "tone_mode": "suggestive", "bench_match": True},
            "turn_number": 2
        },
        "candidate_output": "Hi Marcus, When we last spoke in August, the board had not pushed for cost rebalancing. Two new data points: your sub-sector had eleven announced contractions in the last 90 days, up from four. Three of those companies now use offshore-managed teams within 60 days of restructure. If the conversation has reopened, our pricing has not changed. If not, no follow-up.",
        "ground_truth": {
            "verdict": "pass", "failure_categories": [], "inferred_segment": 2,
            "rationale": "Re-engagement with verifiable new data. Not 'following up'. Conditional.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 1.0, "tone_compliance": 1.0,
                    "honesty_constraint": 1.0, "style_guide_match": 1.0, "composite_score": 0.98},
        "metadata": meta()
    },
    # ─── Self-centered email (SG-BAD-01 pattern) ───
    {
        "task_id": "TB-HA-021", "category": "tone_guard", "subcategory": "self_centered",
        "difficulty": "medium", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "IgnoredProspect Inc"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "assertive", "bench_match": True}
        },
        "candidate_output": "Tenacious Intelligence Corporation is a world-class engineering outsourcing firm with over 200 senior engineers. We have been operating since 2019. Our top talent graduated from elite programs and our delivery model is the gold standard. We offer junior, mid, senior, and architect-level engineers. I would love to schedule a 45-minute discovery call.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["banned_phrase", "self_centered"],
            "inferred_segment": 1,
            "rationale": "3 banned phrases ('world-class', 'top talent', 'gold standard'). 80% about Tenacious. No prospect signal.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.0, "tone_compliance": 0.3,
                    "honesty_constraint": 0.5, "style_guide_match": 0.0, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── External bench language ───
    {
        "task_id": "TB-HA-022", "category": "tone_guard", "subcategory": "bench_external",
        "difficulty": "hard", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "BenchLeakCo"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "assertive", "bench_match": True}
        },
        "candidate_output": "Our bench currently has 35 Python engineers and 12 ML specialists available for immediate deployment. The bench is fully staffed for Q3.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["bench_external_language"],
            "inferred_segment": 1,
            "rationale": "'Bench' is internal-only language. Should never appear in prospect-facing communication.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.5, "tone_compliance": 0.5,
                    "honesty_constraint": 0.5, "style_guide_match": 0.0, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Competitor attack ───
    {
        "task_id": "TB-HA-023", "category": "tone_guard", "subcategory": "competitor_attack",
        "difficulty": "hard", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "CompAttack Inc"},
            "policy_decision": {"pitch_segment": 3, "tone_mode": "suggestive", "bench_match": True}
        },
        "candidate_output": "Unlike Accenture and Infosys, who are overpriced and deliver mediocre results, Tenacious provides genuinely senior engineers at a fraction of the cost. Your competitors already know this.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["competitor_attack", "condescending"],
            "inferred_segment": 3,
            "rationale": "Named competitor attack ('overpriced', 'mediocre'). Condescending framing.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.2, "tone_compliance": 0.0,
                    "honesty_constraint": 0.5, "style_guide_match": 0.0, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Stale signal (expired funding window) ───
    {
        "task_id": "TB-HA-024", "category": "signal_overclaiming", "subcategory": "stale_signal",
        "difficulty": "hard", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {
                "prospect_name": "OldFund Corp",
                "funding": {"total_usd": 8000000, "type": "Series A", "date": "2024-06-01"}
            },
            "policy_decision": {"pitch_segment": 1, "tone_mode": "suggestive",
                                "question_signals": ["funding"], "bench_match": True}
        },
        "candidate_output": "Congratulations on your recent Series A! Post-funding scaling is our sweet spot and we can help you accelerate your hiring roadmap.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["stale_signal"],
            "inferred_segment": 1,
            "rationale": "Funding was 22 months ago (June 2024) — not 'recent'. 180-day window expired. 'Congrats' is embarrassingly late.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.0, "tone_compliance": 0.5,
                    "honesty_constraint": 0.0, "style_guide_match": 0.3, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Segment 4 with low AI maturity (correct handling) ───
    {
        "task_id": "TB-HA-025", "category": "composer", "subcategory": "ai_maturity_correct",
        "difficulty": "medium", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {
                "prospect_name": "PreAI Startup",
                "ai_maturity": {"score": 0, "confidence": "low"},
                "funding": {"total_usd": 9000000, "type": "Series A", "date": "2026-03-01"}
            },
            "policy_decision": {"pitch_segment": 1, "tone_mode": "suggestive",
                                "assertable_signals": ["funding"], "bench_match": True}
        },
        "candidate_output": "Hi Sophia, You closed your $9M Series A in March, and your public roles are all backend and product. No AI postings yet — which is a normal place to be at your stage, not a gap. If your roadmap has an AI feature in the next twelve months, a small squad for a 3-month scoped project is faster and cheaper than a full-time function. If not, ignore this.",
        "ground_truth": {
            "verdict": "pass", "failure_categories": [], "inferred_segment": 1,
            "rationale": "Correctly positions AI maturity=0 as 'normal, not a gap'. Conditional. Does not assume AI roadmap.",
            "forbidden_signals": [], "required_signals": ["funding"]
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 1.0, "tone_compliance": 1.0,
                    "honesty_constraint": 1.0, "style_guide_match": 1.0, "composite_score": 0.98},
        "metadata": meta()
    },
    # ─── Gap brief with low confidence (correct rejection) ───
    {
        "task_id": "TB-HA-026", "category": "policy", "subcategory": "gap_confidence_gate",
        "difficulty": "hard", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "GapLow Corp"},
            "policy_decision": {"pitch_segment": 4, "tone_mode": "suggestive",
                                "bench_match": True},
            "competitor_gap_brief": {"confidence_avg": 0.2, "gap_description": "Missing MLOps function"}
        },
        "candidate_output": "Your competitors are all building dedicated MLOps functions and you're clearly not keeping pace. We can close this gap immediately with our specialized squad.",
        "ground_truth": {
            "verdict": "fail", "failure_categories": ["gap_overclaiming", "condescending"],
            "inferred_segment": 4,
            "rationale": "Gap brief confidence=0.2 (below 0.6 gate). Should not be delivered. Condescending framing.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.0, "tone_compliance": 0.0,
                    "honesty_constraint": 0.0, "style_guide_match": 0.0, "composite_score": 0.0},
        "metadata": meta()
    },
    # ─── Correct objection handling ───
    {
        "task_id": "TB-HA-027", "category": "composer", "subcategory": "objection_handling",
        "difficulty": "hard", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "Objection Corp"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "exploratory", "bench_match": True},
            "prospect_reply": "Not a priority right now. We already have a vendor."
        },
        "candidate_output": "Understood — appreciate the transparency. If it becomes relevant later, I am available. No follow-up from my side unless you reach out.",
        "ground_truth": {
            "verdict": "pass", "failure_categories": [], "inferred_segment": 1,
            "rationale": "Empathetic response to objection. No pressure. Explicit opt-out.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.5, "tone_compliance": 1.0,
                    "honesty_constraint": 1.0, "style_guide_match": 1.0, "composite_score": 0.85},
        "metadata": meta()
    },
    # ─── Warm intro with case study reference ───
    {
        "task_id": "TB-HA-028", "category": "composer", "subcategory": "warm_intro_reference",
        "difficulty": "medium", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "WarmLead Inc"},
            "policy_decision": {"pitch_segment": 4, "tone_mode": "suggestive", "bench_match": True}
        },
        "candidate_output": "Hi Mei, Arjun Krishnan suggested I reach out. He and I worked on the data platform redesign at his Series B, and he said your team is at a similar stage. I can share what we learned, including the two architectural decisions that did not work. Happy to send a one-page write-up or do 15 minutes — your call. If not relevant, no follow-up.",
        "ground_truth": {
            "verdict": "pass", "failure_categories": [], "inferred_segment": 4,
            "rationale": "Names mutual connection. References failures honestly. Two options. Opt-out.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.9, "tone_compliance": 1.0,
                    "honesty_constraint": 1.0, "style_guide_match": 1.0, "composite_score": 0.97},
        "metadata": meta()
    },
    # ─── Micro-touch follow-up (SG-GOOD-12 pattern) ───
    {
        "task_id": "TB-HA-029", "category": "composer", "subcategory": "micro_touch",
        "difficulty": "easy", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "MicroTouch Corp"},
            "policy_decision": {"pitch_segment": 4, "tone_mode": "suggestive", "bench_match": True},
            "turn_number": 2
        },
        "candidate_output": "Hi Kevin, After we spoke yesterday I looked — three competitors are now using dbt-plus-Snowflake. Worth knowing as you scope the build. No reply needed. I will follow up after your internal review next Thursday as agreed.",
        "ground_truth": {
            "verdict": "pass", "failure_categories": [], "inferred_segment": 4,
            "rationale": "Two-line micro-touch. One data point. 'No reply needed'. References agreed next-step.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.9, "tone_compliance": 1.0,
                    "honesty_constraint": 1.0, "style_guide_match": 1.0, "composite_score": 0.97},
        "metadata": meta()
    },
    # ─── Correct warm reply routing to human ───
    {
        "task_id": "TB-HA-030", "category": "integration", "subcategory": "human_handoff",
        "difficulty": "hard", "authoring_mode": "hand_authored",
        "input": {
            "hiring_signal_brief": {"prospect_name": "HandoffCo"},
            "policy_decision": {"pitch_segment": 1, "tone_mode": "assertive", "bench_match": True},
            "prospect_reply": "Interested. What are your exact rates for 3 Python + 1 data engineer for 6 months?"
        },
        "candidate_output": "Thanks for the reply. Our public-tier pricing starts from approximately $X,XXX/month per senior engineer. A specific quote depends on stack, timezone overlap, and delivery lead needs. The cleanest path is a 30-minute scoping call with our delivery lead, Arun. Here is his calendar: gettenacious.com/arun.",
        "ground_truth": {
            "verdict": "pass", "failure_categories": [], "inferred_segment": 1,
            "rationale": "Public bands only. Routes specific quote to human. Names dependencies.",
            "forbidden_signals": [], "required_signals": []
        },
        "scoring": {"segment_alignment": 1.0, "signal_grounding": 0.8, "tone_compliance": 1.0,
                    "honesty_constraint": 1.0, "style_guide_match": 1.0, "composite_score": 0.96},
        "metadata": meta()
    },
]


def main():
    output_dir = Path("eval/tenacious_bench/pilot_50")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "mode_d_pool.jsonl", "w") as f:
        for task in TASKS:
            f.write(json.dumps(task) + "\n")

    print(f"Generated {len(TASKS)} hand-authored adversarial tasks.")

    from collections import Counter
    cats = Counter(t["category"] for t in TASKS)
    diffs = Counter(t["difficulty"] for t in TASKS)
    verdicts = Counter(t["ground_truth"]["verdict"] for t in TASKS)
    print(f"\nCategories: {dict(sorted(cats.items()))}")
    print(f"Difficulties: {dict(sorted(diffs.items()))}")
    print(f"Verdicts: {dict(sorted(verdicts.items()))}")


if __name__ == "__main__":
    main()
