from typing import TypedDict, Annotated
import operator
from agents.orchestrator.contracts import (
    OnboardingInput, PriorKnowledge, OnboardingHandoff
)


class OnboardingState(TypedDict, total=False):
    # Input
    input: OnboardingInput

    # Node outputs (accumulated)
    prior_knowledge: PriorKnowledge
    extracted_fields: dict
    merged_record: dict
    conflicts: list
    completeness_pct: float
    missing_fields: list

    # Persistence
    brand_id: str
    events_logged: Annotated[list, operator.add]

    # Coordination
    messages_emitted: Annotated[list, operator.add]

    # Final handoff
    handoff: OnboardingHandoff

    # Telemetry (same pattern as other agents)
    tool_calls: Annotated[list, operator.add]
    errors: Annotated[list, operator.add]
