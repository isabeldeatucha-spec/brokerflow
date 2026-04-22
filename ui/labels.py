"""User-facing label vocabulary.

Internal Python identifiers (module names, class names, DB columns,
blackboard message types) are NOT renamed. Only display strings.
"""

# Top-level navigation
LABEL_EXISTING_BUSINESS = "Existing business"
LABEL_EXISTING_BUSINESS_SUB = "Pitch, manage, and operate the brands you represent"

LABEL_BRAND_SCOUT = "Brand Scout"
LABEL_BRAND_SCOUT_SUB = "Score new prospects for broker readiness"

# Agent display names (NOT module names)
LABEL_BRAND_SCOUT_AGENT = "Brand Scout"
LABEL_RETAILER_AGENT = "Retailer Agent"   # was "Retailer Pitcher"
LABEL_ADMIN_AGENT = "Admin Agent"          # was "Admin & Ops"

# Brand Scout scope statement (shown on its page)
LABEL_BRAND_SCOUT_SCOPE = (
    "Brand Scout has one job: evaluate prospects and tell you whether they're "
    "broker-ready. It doesn't pitch, fill forms, or manage operations — those "
    "live in your Existing business workspace."
)

# Retailer Agent workflows
WORKFLOW_PITCHING = {
    "key": "pitching",
    "label": "Pitching",
    "status": "active",
    "description": "Draft retailer-specific pitches for brands you represent",
}
WORKFLOW_PROMOS = {
    "key": "promos",
    "label": "Promos",
    "status": "coming_q3",
    "description": "Coordinate price promotions across retailers and distributors",
    "details": (
        "Schedule and track promotional pricing windows. Auto-generate "
        "promo sell sheets. Reconcile lift vs. baseline post-event."
    ),
}
WORKFLOW_CATEGORY_REVIEWS = {
    "key": "category_reviews",
    "label": "Category reviews",
    "status": "coming_q3",
    "description": "Monitor when retailers open category review windows",
    "details": (
        "Track each retailer's category review calendar. Surface the next "
        "open window per category. Pre-stage pitch materials so you never "
        "miss a deadline."
    ),
}
RETAILER_AGENT_WORKFLOWS = [
    WORKFLOW_PITCHING, WORKFLOW_PROMOS, WORKFLOW_CATEGORY_REVIEWS,
]

# Admin Agent workflows
WORKFLOW_NEW_ITEM_FORMS = {
    "key": "new_item_forms",
    "label": "New item forms",
    "status": "active",
    "description": "Auto-fill retailer new item setup forms from canonical brand data",
}
WORKFLOW_DEDUCTIONS = {
    "key": "deductions",
    "label": "Deductions",
    "status": "coming_q3",
    "description": "Track and dispute distributor deductions",
    "details": (
        "Ingest distributor deduction reports. Categorize each deduction "
        "(slotting, MCB, freight, damage). Flag disputes worth pursuing. "
        "Generate dispute letters."
    ),
}
WORKFLOW_PO_PROCESSING = {
    "key": "po_processing",
    "label": "PO processing",
    "status": "coming_q4",
    "description": "Process incoming purchase orders end-to-end",
    "details": (
        "Parse incoming PO PDFs/EDI. Validate against brand pricing. "
        "Confirm with brand. Submit confirmation back to retailer."
    ),
}
WORKFLOW_DEMO_SPEND = {
    "key": "demo_spend",
    "label": "Demo spend",
    "status": "coming_q4",
    "description": "Reconcile demo spend against retailer reports",
    "details": (
        "Track demo schedule, demo cost per event, sales lift attribution, "
        "and retailer-reported demo charges. Reconcile discrepancies."
    ),
}
ADMIN_AGENT_WORKFLOWS = [
    WORKFLOW_NEW_ITEM_FORMS, WORKFLOW_DEDUCTIONS,
    WORKFLOW_PO_PROCESSING, WORKFLOW_DEMO_SPEND,
]

# Status pill labels
STATUS_PILL_LABELS = {
    "active": "Active",
    "coming_q2": "Coming Q2",
    "coming_q3": "Coming Q3",
    "coming_q4": "Coming Q4",
}

# Internal agent name → display name (for activity feed)
AGENT_DISPLAY_NAMES = {
    "brand_scout": "Brand Scout",
    "brand_onboarding": "Onboarding",
    "freshness_watchdog": "Watchdog",
    "retailer_pitcher": "Retailer Agent",
    "retailer_matcher": "Retailer Agent",
    "admin_ops": "Admin Agent",
}
