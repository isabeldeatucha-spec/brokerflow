"""
Test brands for Experiment 1: Memory Strategy A vs B.

Two brands were chosen to represent different stages of the broker funnel:

1. Chomps — established meat snack brand.
   Strong Amazon presence (40k+ reviews), national retail distribution
   (Whole Foods, Target, Costco), significant Faire presence.
   Expected verdict: established (score ≥ 70).
   Why: tests how each strategy handles a *data-rich* brand where signals
   are plentiful and reflection should quickly decide no follow-up needed.

2. Fishwife — premium tinned seafood brand.
   Strong DTC and social presence, solid press coverage, but smaller door
   count than Chomps and a niche category.
   Expected verdict: broker_ready (score 45–69).
   Why: tests how each strategy handles a *data-sparse* brand where some
   signals may be missing and reflection is more likely to request follow-up.
"""

TEST_BRANDS = [
    {
        "brand_name":       "Chomps",
        "website_url":      "https://chomps.com",
        "description":      "Grass-fed beef sticks. 40k+ Amazon reviews, national distribution.",
        "expected_verdict": "established",
    },
    {
        "brand_name":       "Fishwife",
        "website_url":      "https://eatfishwife.com",
        "description":      "Premium tinned seafood. Strong DTC + press, growing natural retail.",
        "expected_verdict": "broker_ready",
    },
]
