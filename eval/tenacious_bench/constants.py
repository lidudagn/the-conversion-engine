"""
Taxonomy and Scoring Constants for Tenacious-Bench.
"""

# Segment Taxonomy
SEGMENTS = {
    1: "Early-Stage/Growth (Scaling fast, Series A/B, product delivery)",
    2: "Restructuring/Efficiency (Cost control, layoffs, velocity with freeze)",
    3: "Enterprise Scaling (Legacy migration, security, specialized expertise)",
    4: "AI/ML Maturity (LLM infrastructure, data pipelines, R&D to Prod)",
}

# Fatal Failure Keywords (Drafting check)
GUARANTEE_KWS = [
    "guarantee", "100% success", "zero risk", "promise", "definitively will",
    "without exception", "#1 ranked", "best in the world"
]

# Tone Markers for Style Guide Match
TONE_MARKERS = [
    "concise",           # No filler/fluff
    "grounded",          # Evidence-based claims
    "no_hype",           # Absence of superlatives
    "clear_cta",         # Single specific next step
    "honest_framing",    # Segment-appropriate pitch
]

# Scoring Weights
WEIGHTS = {
    "segment_alignment": 0.30,
    "signal_grounding":  0.25,
    "tone_compliance":   0.20,
    "honesty_constraint": 0.15,
    "style_guide_match":  0.10,
}

PASS_THRESHOLD = 0.70
