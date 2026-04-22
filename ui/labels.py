"""User-facing label vocabulary.

Internal Python identifiers (module names, class names, DB columns,
blackboard message types) are NOT renamed. Only display strings.
"""

# Top-level navigation
LABEL_EXISTING_BUSINESS = "Your book of business"
LABEL_EXISTING_BUSINESS_SUB = "Service the brands you already represent"

LABEL_BRAND_SCOUT = "Brand Scout"
LABEL_BRAND_SCOUT_SUB = "Qualify new brands before you take a meeting"

# Agent display names (NOT module names)
LABEL_BRAND_SCOUT_AGENT = "Brand Scout"
LABEL_RETAILER_AGENT = "Retailer Agent"   # was "Retailer Pitcher"
LABEL_ADMIN_AGENT = "Admin Agent"          # was "Admin & Ops"

# Brand Scout scope statement (shown on its page)
LABEL_BRAND_SCOUT_SCOPE = (
    "Brand Scout has one job: qualify new brand requests and tell you whether "
    "they're worth a meeting. It doesn't pitch or run ops — those live in your "
    "book of business."
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
        "Schedule TPRs, generate promo sheets, and reconcile lift vs. baseline "
        "after each event. Rule of thumb: 4 TPRs/year max."
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
        "miss a window."
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
        "Pull deduction reports from distributors. Tag each one (slotting, MCB, "
        "freight, damage). Flag the ones worth disputing — and draft the dispute."
    ),
}
WORKFLOW_PO_PROCESSING = {
    "key": "po_processing",
    "label": "PO processing",
    "status": "coming_q4",
    "description": "Process incoming purchase orders end-to-end",
    "details": (
        "Parse POs from email or EDI. Check pricing against the brand's cost "
        "sheet. Confirm with the brand. Send back to the retailer."
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
