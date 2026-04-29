import json
from pathlib import Path

"""
Converts the mentor's 24 labeled outreach drafts (Style Guide v2)
into structured JSONL for pipeline integration.
"""

GOOD_DRAFTS = [
    {
        "task_id": "SG-GOOD-01",
        "segment": 1,
        "segment_alignment": "correct",
        "signal_type": "funding_event",
        "signal_confidence": "High",
        "subject": "Request: 15 minutes on your Q3 Python hiring",
        "body": "Hi Maya,\nYou closed your $14M Series A in February and your open Python engineering roles went from 2 to 7 in the last 60 days. The typical bottleneck for teams in that state is recruiting capacity, not budget.\nWe place dedicated Python and data engineers, managed by Tenacious, with a minimum three hours of synchronous overlap. We can plug a team in within 48 hours while you continue your full-time search.\nWould 15 minutes next week be useful? I'll bring two case studies from Series A SaaS clients who hit the same wall.\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 89,
        "why_works": "Names funding amount/date, exact role-count trend. Frames gap as pattern not failing. One ask. No 'bench'."
    },
    {
        "task_id": "SG-GOOD-02",
        "segment": 2,
        "segment_alignment": "correct",
        "signal_type": "layoffs",
        "signal_confidence": "High",
        "subject": "Context: lower-cost engineering capacity post-restructure",
        "body": "Hi Daniel,\nI saw the announcement that your team contracted by about 12% in March. Companies in your stage often need to maintain delivery output while reducing fully-loaded cost — that is the engagement pattern we run most often.\nTenacious places managed engineering teams under our project management. Senior engineers in Python, data, and ML start from $X,XXX/month, with a one-month minimum and two-week extension blocks. No long-term commitment.\nIf you are scoping the next twelve months of delivery capacity, I can share two short case studies from mid-market clients who replaced a portion of their delivery cost this way.\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 100,
        "why_works": "Acknowledges layoff respectfully as 'contraction'. Conditional language. Public pricing only."
    },
    {
        "task_id": "SG-GOOD-03",
        "segment": 3,
        "segment_alignment": "correct",
        "signal_type": "leadership_change",
        "signal_confidence": "High",
        "subject": "Context: a brief on offshore engineering models",
        "body": "Hi Priya,\nWelcome to your new role at Helix — I saw the announcement on the 14th. New engineering leaders typically reassess vendor and offshore mix in their first 90 days.\nI do not want to add to your inbox in week three of a new job. I will leave you with one thing: a one-page brief on the four offshore engagement models we see most often, with the trade-offs honestly laid out (including where each model fails).\nIf a 15-minute conversation in November would be useful, the calendar is at gettenacious.com/yabi. If not, no follow-up.\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 96,
        "why_works": "Names announcement date. Self-aware of inbox noise. Explicit opt-out."
    },
    {
        "task_id": "SG-GOOD-04",
        "segment": 4,
        "segment_alignment": "correct",
        "signal_type": "capability_gap",
        "signal_confidence": "High",
        "subject": "Question: your MLOps function in 2026",
        "body": "Hi Felix,\nThree companies adjacent to yours in the loyalty-platform space — A, B, and C — posted senior MLOps engineer roles in the last 90 days. Your team has not, at least not publicly. Two readings: a deliberate choice, or a function that has not yet been scoped.\nWe staff specialized squads (ML platform, agentic systems, data contracts) on fixed-scope project engagements, typically 3 to 4 months. Starter scopes from $XX,XXX. We do not pitch this where there is no real need.\nIf you have already scoped this and decided against it, I would genuinely be curious why — that is useful intelligence for us. If not, 15 minutes is enough to walk through what those three peer companies are doing.\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 117,
        "why_works": "Frames gap as 'two readings' not deficiency. Asks prospect's reasoning. Named peers."
    },
    {
        "task_id": "SG-GOOD-05",
        "segment": 1,
        "segment_alignment": "correct",
        "signal_type": "job_post_velocity",
        "signal_confidence": "Low",
        "subject": "Question: are your data engineering hires keeping up?",
        "body": "Hi Tom,\nTwo open data engineer roles on your careers page — I cannot tell from the outside whether that means hiring is keeping pace or whether the queue is longer than the postings suggest.\nWe place managed data and Python engineering teams, three-hour overlap with US time zones, one-month minimum. If the queue is longer than the posts, that is the pattern we solve most often.\nIf two roles is the actual demand and you are well-staffed to meet it, ignore this. If the real number is higher, a 15-minute conversation costs you nothing and gives me a chance to learn what you are seeing.\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 105,
        "why_works": "Honestly names what agent cannot tell. Conditional. Explicit out."
    },
    {
        "task_id": "SG-GOOD-06",
        "segment": 1,
        "segment_alignment": "correct",
        "signal_type": "funding_event",
        "signal_confidence": "Medium",
        "subject": "Resource: Series A engineering scale-up checklist",
        "body": "Hi Ana,\nYou closed your seed extension in October and your first three engineering hires are public on LinkedIn. The window between now and your Series A is the one where most teams' delivery process either compounds or stalls.\nI put together a one-page checklist of the seven decisions that determine which side a team lands on (when to introduce code review formality, when to write the first runbook, when offshore augmentation pays back, when it does not). Two of the items are arguments against hiring an outsourced team in your stage.\nWant me to send the PDF? No follow-up if you are not interested.\nBest,\nYabi\nResearch Partner, Tenacious Intelligence Corporation\ngettenacious.com",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 116,
        "why_works": "Pure value-add. Two items argue against Tenacious's own service. Lowest friction ask."
    },
    {
        "task_id": "SG-GOOD-07",
        "segment": 1,
        "segment_alignment": "correct",
        "signal_type": "warm_reply",
        "signal_confidence": "High",
        "subject": "Re: scope of the three-engineer engagement",
        "body": "Hi Camila,\nThanks for the reply and for the additional context on the December timeline.\nThree Python and one data engineer for a 6-month engagement is in our typical range. Our public-tier pricing for that mix starts from approximately $X,XXX/month per engineer at senior level, with a one-month minimum and two-week extension blocks thereafter.\nA specific quote depends on the exact stack, the timezone overlap requirement, and whether you want a Tenacious delivery lead embedded. The cleanest path is a 30-minute scoping call with our delivery lead, Arun. Here is his calendar: gettenacious.com/arun.\nIf the December start date is firm, I would suggest booking this week so we can confirm capacity availability.\nBest,\nYabi",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 130,
        "why_works": "Public bands only. Routes specific quote to human. Names dependencies."
    },
    {
        "task_id": "SG-GOOD-08",
        "segment": 2,
        "segment_alignment": "correct",
        "signal_type": "layoffs",
        "signal_confidence": "High",
        "subject": "New: layoffs.fyi data on your sub-sector this quarter",
        "body": "Hi Marcus,\nWhen we last spoke in August, you mentioned that the board had not yet pushed for cost rebalancing. Two new data points that may matter:\nFirst, the layoffs.fyi data shows your sub-sector (vertical SaaS for healthcare) had eleven announced contractions in the last 90 days, up from four in the prior quarter. Boards are reading the same data.\nSecond, three of those eleven companies are now using offshore-managed engineering teams within 60 days of restructure — that pattern is faster than it was a year ago.\nIf the conversation has reopened on your side, our managed engineering pricing has not changed. If not, no follow-up needed.\nBest,\nYabi",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 113,
        "why_works": "Re-engagement with new content. Two verifiable data points. No 'following up'."
    },
    {
        "task_id": "SG-GOOD-09",
        "segment": 1,
        "segment_alignment": "correct",
        "signal_type": "warm_reply",
        "signal_confidence": "High",
        "subject": "Re: scaling to 15 engineers in 30 days",
        "body": "Hi Will,\nThanks for the follow-up and for the trust to ask about the 15-engineer ramp. Honest answer: 15 engineers across a Go and infra-heavy stack within 30 days is at the edge of what our current capacity can deliver responsibly.\nWhat we can confirm now: 6 to 8 engineers in that stack, starting within 21 days, with a Tenacious delivery lead embedded. Going to 15 reliably requires a 60-day ramp window, with the back half of the team onboarding in weeks 5 and 6.\nIf the 30-day target is firm, I would rather refer you to a peer firm that fits the timeline than over-commit. Happy to introduce.\nBest,\nYabi",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 116,
        "why_works": "Refuses to over-commit. Offers partial + peer-firm referral. Earns long-term trust."
    },
    {
        "task_id": "SG-GOOD-10",
        "segment": 1,
        "segment_alignment": "correct",
        "signal_type": "funding_event",
        "signal_confidence": "High",
        "subject": "Question: standing up your first AI function",
        "body": "Hi Sophia,\nYou closed your $9M Series A in March, your team is ten engineers, and your public roles are all backend and product. No AI or ML postings yet — which is a normal place to be at your stage, not a gap.\nIf your roadmap has an AI feature in the next twelve months, the first hire is usually the wrong unit. A small dedicated squad (ML engineer plus data platform engineer plus a Tenacious delivery lead) for a 3-month scoped project is faster, cheaper, and lets you test whether AI is core enough to your roadmap to justify a full-time function.\nIf that is on your roadmap, 15 minutes to walk through what the first 90 days look like. If not, ignore this.\nBest,\nYabi",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 130,
        "why_works": "AI maturity 0-1: 'normal place to be, not a gap'. Conditional. Does not assume AI roadmap exists."
    },
    {
        "task_id": "SG-GOOD-11",
        "segment": 4,
        "segment_alignment": "correct",
        "signal_type": "warm_intro",
        "signal_confidence": "High",
        "subject": "Context: Arjun's recommendation",
        "body": "Hi Mei,\nArjun Krishnan suggested I reach out — he and I worked on the data platform redesign at his Series B in February, and he said your team is at a similar stage with the same Snowflake plus dbt plus Airflow combination he was working through.\nIf the equivalent rebuild is on your roadmap, I would be glad to share what we learned in his project, including the two architectural decisions that did not work and that Arjun would tell you about openly. Happy to send a one-page write-up or do 15 minutes — your call.\nIf this is not on your roadmap, no follow-up.\nBest,\nYabi",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 110,
        "why_works": "Names mutual connection and specific project. References decisions that did NOT work. Two options."
    },
    {
        "task_id": "SG-GOOD-12",
        "segment": 4,
        "segment_alignment": "correct",
        "signal_type": "warm_nurture",
        "signal_confidence": "Medium",
        "subject": "Quick thought after our call",
        "body": "Hi Kevin,\nAfter we spoke yesterday I went back and looked — three of the loyalty platforms you mentioned as competitors are now publicly using the same dbt-plus-Snowflake stack you are evaluating. Worth knowing as you scope the build.\nNo reply needed. I will follow up after your internal review next Thursday as agreed.\nBest,\nYabi",
        "verdict": "pass",
        "failure_categories": [],
        "tone_scores": {"direct": 5, "grounded": 5, "honest": 5, "professional": 5, "non_condescending": 5},
        "word_count": 47,
        "why_works": "Two-line micro-touch. One data point. 'No reply needed'. References agreed next-step date."
    }
]

BAD_DRAFTS = [
    {
        "task_id": "SG-BAD-01",
        "segment": 0,
        "segment_alignment": "no_segment",
        "signal_type": "none",
        "signal_confidence": "None",
        "subject": "Tenacious — World-Class Engineering Talent",
        "body": "Dear Maya,\nTenacious Intelligence Corporation is a world-class engineering outsourcing firm with over 200 senior engineers across Python, Go, data, ML, and infrastructure. We have been operating since 2019 and have served clients across North America and Europe. Our top talent is graduated from elite programs and our delivery model is the gold standard in the industry.\nWe offer junior, mid, senior, and architect-level engineers, fractional CTO services, project consulting on AI systems, data platforms, and specialized infrastructure, training engagements, and strategic AI workshops. Our pricing is highly competitive and we offer flexible engagement models.\nI would love to schedule a 45-minute discovery call to learn about your business, your goals, your pain points, your budget, and your roadmap so we can determine the best way to partner.\nBest regards,\nYabi",
        "verdict": "fail",
        "failure_categories": ["banned_phrase", "no_signal_grounding", "word_count_exceeded", "self_centered"],
        "tone_scores": {"direct": 2, "grounded": 1, "honest": 2, "professional": 1, "non_condescending": 3},
        "word_count": 152,
        "why_fails": "3 banned phrases ('world-class', 'top talent', 'gold standard'). 80% about Tenacious. No signal. 152 words."
    },
    {
        "task_id": "SG-BAD-02",
        "segment": 1,
        "segment_alignment": "incorrect",
        "signal_type": "job_post_velocity",
        "signal_confidence": "Low",
        "subject": "Quick chat: your aggressive hiring",
        "body": "Hi Tom,\nI see you are scaling aggressively — your engineering team is clearly growing fast and you must be feeling the pain of recruiting velocity right now. Companies in your stage always hit a wall around month four after a Series A.\nWe solve this exact problem. Tenacious places top talent in 48 hours and we will skyrocket your delivery throughput.\nQuick question — do you have 15 minutes this week?\nBest,\nYabi",
        "verdict": "fail",
        "failure_categories": ["D06_weak_signal_assertion", "banned_phrase", "honest_failure"],
        "tone_scores": {"direct": 3, "grounded": 1, "honest": 1, "professional": 2, "non_condescending": 4},
        "word_count": 72,
        "why_fails": "Asserts 'scaling aggressively' on 2 open roles (weak signal). 'top talent', 'skyrocket', 'Quick chat' banned."
    },
    {
        "task_id": "SG-BAD-03",
        "segment": 1,
        "segment_alignment": "incorrect",
        "signal_type": "warm_reply",
        "signal_confidence": "High",
        "subject": "Re: 12 senior Go engineers in two weeks",
        "body": "Hi Will,\nAbsolutely, we can deliver 12 senior Go engineers in two weeks. Our bench is deep across all stacks and we move fast.\nI will have our team kick off scoping immediately. Expect contracts by Wednesday and engineers in your Slack by next Friday.\nBest,\nYabi",
        "verdict": "fail",
        "failure_categories": ["bench_overcommit", "bench_external_language", "honest_failure"],
        "tone_scores": {"direct": 4, "grounded": 2, "honest": 1, "professional": 2, "non_condescending": 5},
        "word_count": 48,
        "why_fails": "Commits 12 Go engineers not in bench_summary.json. Uses 'bench' externally. Skips human handoff."
    },
    {
        "task_id": "SG-BAD-04",
        "segment": 4,
        "segment_alignment": "correct",
        "signal_type": "capability_gap",
        "signal_confidence": "High",
        "subject": "Your AI maturity is behind the curve",
        "body": "Hi Felix,\nI will be direct: your AI maturity score is a 1, while your top competitors are a 3. You are falling behind in a market where AI is no longer optional, and your leadership has not yet made the strategic moves that the loyalty-platform sector demands in 2026.\nTenacious can stand up your missing MLOps function and close the gap before your next board meeting. Our agentic systems and ML platform engineers are world-class.\nLet's get on a call this week to discuss how we can help you catch up.\nBest,\nYabi",
        "verdict": "fail",
        "failure_categories": ["condescending", "banned_phrase", "non_condescending_failure"],
        "tone_scores": {"direct": 4, "grounded": 3, "honest": 3, "professional": 2, "non_condescending": 1},
        "word_count": 102,
        "why_fails": "Subject is condescending. 'falling behind', 'catch up', 'world-class'. Frames prospect as failing."
    },
    {
        "task_id": "SG-BAD-05",
        "segment": 1,
        "segment_alignment": "no_segment",
        "signal_type": "re_engagement",
        "signal_confidence": "None",
        "subject": "Per my last three emails",
        "body": "Hi Ana,\nI have sent you three emails over the last two weeks and have not heard back. I have to assume you are not interested in growing your engineering capacity, which is fine — but I would appreciate a one-line reply to confirm so I can take you off the list.\nIf I do not hear back by Friday, I will assume the answer is no.\nBest,\nYabi",
        "verdict": "fail",
        "failure_categories": ["banned_phrase", "passive_aggressive", "guilt_trip", "non_condescending_failure"],
        "tone_scores": {"direct": 3, "grounded": 1, "honest": 2, "professional": 3, "non_condescending": 1},
        "word_count": 65,
        "why_fails": "'Per my last emails' banned. Passive-aggressive guilt trip. Fake deadline."
    },
    {
        "task_id": "SG-BAD-06",
        "segment": 0,
        "segment_alignment": "no_segment",
        "signal_type": "none",
        "signal_confidence": "None",
        "subject": "Hey [First Name], scaling your engineering team?",
        "body": "Hey [First Name],\nI hope this email finds you well. I am reaching out because I think Tenacious can help [Company] with all of your engineering and AI needs in 2026.\nWe work with companies like yours to deliver world-class talent at affordable prices. Our team has experience across many industries and stacks, and we can help you scale, restructure, or build new capabilities depending on what you need.\nWould you be open to a quick chat next week to explore how we can synergize and add value to your ecosystem?\nBest,\nYabi",
        "verdict": "fail",
        "failure_categories": ["template_tokens", "banned_phrase", "no_signal_grounding", "all_markers_fail"],
        "tone_scores": {"direct": 2, "grounded": 1, "honest": 1, "professional": 1, "non_condescending": 3},
        "word_count": 92,
        "why_fails": "Unfilled [First Name]/[Company]. 5 banned phrases. Zero signal. Fails every tone marker."
    },
    {
        "task_id": "SG-BAD-07",
        "segment": 0,
        "segment_alignment": "no_segment",
        "signal_type": "none",
        "signal_confidence": "None",
        "subject": "URGENT: Last open slot for Q1 — 30% off if you sign this week",
        "body": "Hi Kevin,\nTenacious has one remaining slot in our Q1 cohort for managed engineering teams. Because of strong demand, this slot will not be available after Friday.\nIf you sign a contract by end of day Friday, I am authorized to offer 30% off the first three months. After that, the slot goes to the next company on the waitlist.\nDo not miss out on this — book a call here: gettenacious.com/yabi.\nBest,\nYabi",
        "verdict": "fail",
        "failure_categories": ["fake_urgency", "pricing_fabrication", "banned_phrase"],
        "tone_scores": {"direct": 3, "grounded": 1, "honest": 1, "professional": 2, "non_condescending": 3},
        "word_count": 79,
        "why_fails": "Fake scarcity. 30% discount not in pricing_sheet. 'Don't miss out' banned. URGENT subject."
    },
    {
        "task_id": "SG-BAD-08",
        "segment": 4,
        "segment_alignment": "incorrect",
        "signal_type": "capability_gap",
        "signal_confidence": "Low",
        "subject": "Question: your agentic systems roadmap",
        "body": "Hi Sophia,\nI am curious how you are thinking about your agentic-systems roadmap for 2026. Most peer companies in your stage are now scoping LLM-orchestrated workflows and dedicated MLOps functions to support production agent deployments.\nWe staff specialized capability-gap squads — agentic systems, ML platform, data contracts — typically 3 to 4 months. Starter scope from $XX,XXX. We have done this for several Series A and B SaaS companies in the last year.\nWant to set up a 30-minute scoping conversation?\nBest,\nYabi",
        "verdict": "fail",
        "failure_categories": ["D06_wrong_segment", "grounded_failure", "ai_maturity_gating_violation"],
        "tone_scores": {"direct": 4, "grounded": 2, "honest": 2, "professional": 4, "non_condescending": 4},
        "word_count": 96,
        "why_fails": "Pitches Seg4 to AI maturity 0-1. Assumes agentic roadmap. Should use GOOD #10 framing."
    },
    {
        "task_id": "SG-BAD-09",
        "segment": 2,
        "segment_alignment": "no_segment",
        "signal_type": "re_engagement",
        "signal_confidence": "None",
        "subject": "Tenacious capabilities deck — review pages 8 and 12",
        "body": "Hi Marcus,\nPlease find attached our 38-page capabilities deck.\nPages 8 and 12 are the most relevant to your sub-sector. Let me know your thoughts and we can schedule a call to discuss our partnership opportunity.\nLooking forward to your reply.\nBest,\nYabi\n[ATTACHMENT: tenacious_capabilities_v7.pdf — 12.4 MB]",
        "verdict": "fail",
        "failure_categories": ["cold_pdf_attachment", "no_signal_grounding", "direct_failure"],
        "tone_scores": {"direct": 2, "grounded": 1, "honest": 3, "professional": 3, "non_condescending": 4},
        "word_count": 42,
        "why_fails": "Cold PDF attachment (banned). No signal. Outsources value to PDF."
    },
    {
        "task_id": "SG-BAD-10",
        "segment": 2,
        "segment_alignment": "correct",
        "signal_type": "layoffs",
        "signal_confidence": "High",
        "subject": "A few questions and ideas for [Company]",
        "body": "Hi Daniel,\nI had a few thoughts I wanted to share. First, I would love to understand your current engineering structure and which stacks you are using. Second, I have an introduction to a peer of yours at a similar mid-market platform that I think you should meet. Third, we have a new training program for engineering leaders that might be relevant. Fourth, I noticed your AI maturity is around a 2 — happy to walk through how to move it to a 3.\nCould we set up a 60-minute call next week to discuss all four of these? I will also send our pricing sheet, our case studies, and our training brochure separately.\nBest,\nYabi",
        "verdict": "fail",
        "failure_categories": ["multiple_asks", "direct_failure", "condescending"],
        "tone_scores": {"direct": 1, "grounded": 2, "honest": 3, "professional": 3, "non_condescending": 2},
        "word_count": 121,
        "why_fails": "4 asks in one message. 60-min call. 3 additional emails promised. Word count exceeded for cold."
    },
    {
        "task_id": "SG-BAD-11",
        "segment": 1,
        "segment_alignment": "correct",
        "signal_type": "warm_reply",
        "signal_confidence": "High",
        "subject": "Quote: $1.2M for the 12-month engagement",
        "body": "Hi Camila,\nThanks for the call yesterday. As discussed, our quote for the 12-month engagement covering 6 engineers, a delivery lead, and a fractional architect is $1,200,000 total, payable in monthly installments of $100,000.\nI have attached the contract. Please sign and return by Friday so we can begin onboarding on the 1st.\nBest,\nYabi",
        "verdict": "fail",
        "failure_categories": ["pricing_fabrication", "contract_overreach", "honest_failure"],
        "tone_scores": {"direct": 4, "grounded": 2, "honest": 1, "professional": 3, "non_condescending": 5},
        "word_count": 67,
        "why_fails": "TCV invented. Contract attached (human-only). Hard deadline. Skips route-to-human."
    },
    {
        "task_id": "SG-BAD-12",
        "segment": 1,
        "segment_alignment": "incorrect",
        "signal_type": "funding_event",
        "signal_confidence": "Fabricated",
        "subject": "Re: your $40M Series C",
        "body": "Hi Priya,\nCongratulations on closing your $40M Series C last month — exciting moment for the team. With that level of capital, scaling engineering aggressively is the obvious next move.\nWe can plug a 15-engineer team into your stack within 30 days at our standard rates. Junior engineers from $X,XXX/month.\nWant to set up a 15-minute call to discuss?\nBest,\nYabi",
        "verdict": "fail",
        "failure_categories": ["signal_fabrication", "bench_overcommit", "honest_failure", "highest_cost_failure"],
        "tone_scores": {"direct": 4, "grounded": 1, "honest": 1, "professional": 4, "non_condescending": 4},
        "word_count": 60,
        "why_fails": "Series C and $40M fabricated (actual: Series A, $9M). 15 engineers not in bench. Every claim verifiably wrong."
    }
]


def main():
    out_path = Path("eval/tenacious_bench/style_guide_examples.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_drafts = []
    for d in GOOD_DRAFTS + BAD_DRAFTS:
        d["source"] = "mentor_style_guide_v2"
        d["difficulty"] = "reference"
        all_drafts.append(d)

    with open(out_path, "w") as f:
        for draft in all_drafts:
            f.write(json.dumps(draft) + "\n")

    print(f"SUCCESS: Converted {len(all_drafts)} expert-labeled drafts to {out_path}")
    print(f"  GOOD: {len(GOOD_DRAFTS)}")
    print(f"  BAD:  {len(BAD_DRAFTS)}")


if __name__ == "__main__":
    main()
