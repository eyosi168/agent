from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages

Intent = Literal["rebook", "refund", "compensation", "complaint"]


class RebookingState(TypedDict, total=False):
    """Shared state for every node in the graph."""

    request_id: str
    booking_ref: str

    # Conversation history; appended to by every node that speaks.
    messages: Annotated[list[Any], add_messages]

    # Classifier output.
    intent: Intent
    constraints: dict[str, Any]

    # Loaded booking record (intake / follow-up reuse).
    booking: dict[str, Any]

    # Specialist output.
    proposed_solution: dict[str, Any]

    # Refund agent's fare-rule lookup (visible in state).
    fare_rules: dict[str, Any]

    # Policy checker output: {"passed": bool, "reason": str, "checked_at": str}.
    policy_check: dict[str, Any]

    # Retry counter for the policy cycle (guaranteed termination).
    retry_count: int

    # Escalation status.
    escalated: bool
    escalation_note: str

    # Supervisor (human-in-the-loop) decision for payouts over $300.
    approved: bool

    # Final passenger-facing reply.
    final_response: str
