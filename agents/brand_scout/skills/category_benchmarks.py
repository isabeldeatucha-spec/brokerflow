"""
Category-specific benchmarks for the Brand Scout scoring node.

Injects category context into the scoring prompt so Claude applies
the right standards per product type instead of generic CPG norms.
"""
from typing import Any

CATEGORY_BENCHMARKS: dict[str, dict[str, Any]] = {
    "beverage_rtd": {
        "viable_srp_min": 3.50,
        "viable_srp_max": 8.00,
        "concern_below": 3.00,
        "typical_amazon_reviews_early": 50,
        "typical_amazon_reviews_established": 500,
        "typical_broker_sweet_spot_doors": "50-500",
        "key_retailers": ["Whole Foods", "Sprouts", "Target", "Erewhon", "Foxtrot"],
        "key_distributors": ["UNFI", "KeHE", "Haddon House"],
        "category_notes": "Velocity is king in beverages. Buyers want to see 2+ turns per week minimum. Refrigerated beverages need cold chain — adds cost. RTD coffee and functional beverages are hottest subcategories right now.",
        "broker_red_flags": ["single SKU", "no refrigerated distribution", "SRP below $3", "no Amazon presence for shelf-stable"],
        "broker_green_flags": ["subscription available", "functional claim", "clean label", "Whole Foods or Sprouts already"],
    },
    "snack_bar": {
        "viable_srp_min": 2.50,
        "viable_srp_max": 5.00,
        "concern_below": 2.00,
        "typical_amazon_reviews_early": 100,
        "typical_amazon_reviews_established": 1000,
        "typical_broker_sweet_spot_doors": "100-800",
        "key_retailers": ["Whole Foods", "Target", "Walmart", "Sprouts", "CVS", "Costco"],
        "key_distributors": ["UNFI", "KeHE", "DPI"],
        "category_notes": "Extremely crowded category. Differentiation is critical — protein bars, energy bars, and granola bars are distinct subcategories with different buyers. Costco placement is a major velocity signal.",
        "broker_red_flags": ["no protein or functional claim", "SRP above $4 without clear premium reason", "packaging not shelf-ready"],
        "broker_green_flags": ["Costco presence", "Subscribe & Save on Amazon", "clear dietary positioning (keto, vegan, paleo)"],
    },
    "condiment_sauce": {
        "viable_srp_min": 7.00,
        "viable_srp_max": 16.00,
        "concern_below": 5.00,
        "typical_amazon_reviews_early": 50,
        "typical_amazon_reviews_established": 300,
        "typical_broker_sweet_spot_doors": "20-300",
        "key_retailers": ["Whole Foods", "Williams Sonoma", "Sur La Table", "Erewhon", "Sprouts"],
        "key_distributors": ["UNFI", "KeHE", "Specialty Food Association members"],
        "category_notes": "Premium condiments have strong margin profiles. Gifting channel is significant. Founder story matters more here than in snacks. Viral social moment (like Graza) can compress the distribution timeline dramatically.",
        "broker_red_flags": ["SRP below $6", "no clear usage occasion", "commodity ingredients without differentiation"],
        "broker_green_flags": ["viral social moment", "chef endorsement", "unique format or packaging", "clean ingredient list"],
    },
    "frozen_food": {
        "viable_srp_min": 6.00,
        "viable_srp_max": 14.00,
        "concern_below": 5.00,
        "typical_amazon_reviews_early": 20,
        "typical_amazon_reviews_established": 200,
        "typical_broker_sweet_spot_doors": "50-400",
        "key_retailers": ["Whole Foods", "Target", "Sprouts", "Trader Joes", "Kroger"],
        "key_distributors": ["UNFI", "KeHE", "Dot Foods"],
        "category_notes": "Cold chain adds significant cost. Freezer placement is limited and competitive. Strong velocity proof required before major chain expansion. Trader Joe's is a major validation signal but exclusive.",
        "broker_red_flags": ["no cold chain infrastructure", "SRP below $5", "limited shelf life"],
        "broker_green_flags": ["Trader Joes presence", "ethnic cuisine with mainstream crossover", "meal kit validation"],
    },
    "supplement_functional": {
        "viable_srp_min": 20.00,
        "viable_srp_max": 65.00,
        "concern_below": 15.00,
        "typical_amazon_reviews_early": 100,
        "typical_amazon_reviews_established": 2000,
        "typical_broker_sweet_spot_doors": "20-200",
        "key_retailers": ["Whole Foods", "Sprouts", "The Vitamin Shoppe", "GNC", "Target"],
        "key_distributors": ["UNFI", "KeHE", "Nutraceutix"],
        "category_notes": "Amazon is primary channel for supplements — Amazon review count is more important here than any other category. Clinical claims require substantiation. FTC scrutiny is high. Subscription model is standard.",
        "broker_red_flags": ["unsubstantiated health claims", "no Amazon presence", "SRP below $20"],
        "broker_green_flags": ["clinical study cited", "Subscribe & Save", "500+ Amazon reviews", "NSF or USP certified"],
    },
    "olive_oil_cooking_oil": {
        "viable_srp_min": 12.00,
        "viable_srp_max": 35.00,
        "concern_below": 8.00,
        "typical_amazon_reviews_early": 50,
        "typical_amazon_reviews_established": 500,
        "typical_broker_sweet_spot_doors": "20-300",
        "key_retailers": ["Whole Foods", "Williams Sonoma", "Erewhon", "Sprouts", "Target"],
        "key_distributors": ["UNFI", "KeHE", "specialty importers"],
        "category_notes": "Premium olive oil is a high-margin, high-story category. Origin, polyphenol content, and harvest date matter to buyers. Packaging innovation (like Graza squeeze bottle) can redefine category. DTC + gift channel are strong entry points.",
        "broker_red_flags": ["commodity positioning", "SRP below $10", "no origin story"],
        "broker_green_flags": ["single origin", "squeeze bottle or innovative format", "polyphenol content cited", "chef partnerships"],
    },
    "dairy_alternative": {
        "viable_srp_min": 5.00,
        "viable_srp_max": 12.00,
        "concern_below": 4.00,
        "typical_amazon_reviews_early": 30,
        "typical_amazon_reviews_established": 300,
        "typical_broker_sweet_spot_doors": "50-500",
        "key_retailers": ["Whole Foods", "Sprouts", "Target", "Kroger", "Trader Joes"],
        "key_distributors": ["UNFI", "KeHE"],
        "category_notes": "Oat milk has peaked. Greek-style and probiotic dairy alternatives are growing. Cold chain required. Refrigerated category has better velocity than shelf-stable alternatives. Sourmilk (fermented oat milk) fits here.",
        "broker_red_flags": ["oat milk without differentiation", "no cold chain", "SRP above $10 without functional premium"],
        "broker_green_flags": ["probiotic or fermentation story", "barista line", "foodservice validation"],
    },
    "meat_snack_protein": {
        "viable_srp_min": 2.00,
        "viable_srp_max": 5.00,
        "concern_below": 1.50,
        "typical_amazon_reviews_early": 200,
        "typical_amazon_reviews_established": 2000,
        "typical_broker_sweet_spot_doors": "500-5000",
        "key_retailers": ["Whole Foods", "Target", "Walmart", "Costco", "Sprouts", "CVS", "7-Eleven"],
        "key_distributors": ["UNFI", "KeHE", "McLane"],
        "category_notes": "High velocity category. Costco placement is a major signal. Grass-fed and clean label positioning drives premium pricing. Keto and paleo tailwinds strong. Amazon reviews matter more here than most categories.",
        "broker_red_flags": ["single flavor", "no certifications", "SRP below $1.50", "no Amazon presence"],
        "broker_green_flags": ["Costco presence", "grass-fed or clean label", "Subscribe & Save", "keto/paleo certified"],
    },
    "unknown": {
        "viable_srp_min": 6.00,
        "viable_srp_max": 20.00,
        "concern_below": 4.00,
        "typical_amazon_reviews_early": 50,
        "typical_amazon_reviews_established": 500,
        "typical_broker_sweet_spot_doors": "20-300",
        "key_retailers": ["Whole Foods", "Sprouts", "Target"],
        "key_distributors": ["UNFI", "KeHE"],
        "category_notes": "Category not detected — applying general CPG benchmarks.",
        "broker_red_flags": ["no clear differentiation", "SRP below $5"],
        "broker_green_flags": ["strong social presence", "clear functional claim"],
    },
}


def detect_category(brand_name: str, signals: dict) -> str:
    """Detect product category from scraped signals. Returns a CATEGORY_BENCHMARKS key."""
    text = (str(signals) + " " + brand_name).lower()
    if any(w in text for w in ["meat stick", "beef stick", "jerky", "meat snack", "chomps", "epic bar", "grass-fed beef", "protein stick"]):
        return "meat_snack_protein"
    if any(w in text for w in ["olive oil", "cooking oil", "evoo"]):
        return "olive_oil_cooking_oil"
    if any(w in text for w in ["sauce", "condiment", "hot sauce", "dressing", "salsa", "vinegar", "ketchup", "mustard"]):
        return "condiment_sauce"
    if any(w in text for w in ["supplement", "vitamin", "adaptogen", "mushroom powder", "nootropic"]):
        return "supplement_functional"
    # beverage check before dairy to prevent "coconut water" matching dairy
    if any(w in text for w in ["coconut water", "vita coco", "energy drink", "beverage", "drink", "rtd", "juice", "coffee", "tea", "soda", "sparkling", "kombucha", "kefir water"]):
        return "beverage_rtd"
    # dairy check after beverage
    if any(w in text for w in ["milk", "dairy", "yogurt", "kefir", "oat milk", "almond milk", "sourmilk", "fermented milk"]):
        return "dairy_alternative"
    if any(w in text for w in ["bar", "granola bar", "protein bar", "snack bar", "energy bar", "cereal bar"]):
        return "snack_bar"
    if any(w in text for w in ["water", "coconut"]):
        return "beverage_rtd"
    if any(w in text for w in ["frozen", "freeze-dried", "ice cream", "popsicle", "frozen meal"]):
        return "frozen_food"
    return "unknown"


def get_benchmark(category: str) -> dict:
    """Return benchmark dict for the given category key."""
    return CATEGORY_BENCHMARKS.get(category, CATEGORY_BENCHMARKS["unknown"])
