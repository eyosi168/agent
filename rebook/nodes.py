"""Node functions. Each node updates only its own state fields."""

import json
import re

from langchain_core.messages import SystemMessage
from langgraph.types import interrupt

from . import prompts
from .llm import get_llm
from .policy import check_policy
from .tools import get_booking, get_fare_rules, search_flights


def _parse_json(content: str) -> dict:
    """Extract a JSON object from LLM output, tolerating code fences.

    Never raises: an unparseable reply becomes a dict the policy checker
    rejects, feeding the retry loop instead of crashing the graph.
    """
    text = content.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return {"type": "", "raw": content[:500]}


def intake(state: dict) -> dict:
    """Load the booking once; reuse it on follow-up messages.

    Also clears per-turn fields so a new passenger message starts a fresh
    policy cycle (the checkpointer keeps the booking and history).
    """
    booking = state.get("booking")
    ref = state.get("booking_ref")
    if booking is None and ref:
        booking = get_booking.invoke({"booking_ref": ref})
    return {
        "booking": booking or {},
        "proposed_solution": {},
        "policy_check": {},
        "retry_count": 0,
        "escalated": False,
        "escalation_note": "",
        "approved": False,
        "final_response": "",
    }


def classifier(state: dict) -> dict:
    """Structured-output extraction of intent + constraints."""
    llm = get_llm()
    structured = llm.with_structured_output(
        {
            "title": "RequestClassification",
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["rebook", "refund", "compensation", "complaint"],
                },
                "constraints": {"type": "object"},
            },
            "required": ["intent", "constraints"],
        },
        method="function_calling",
    )
    history = "\n".join(
        f"{m.type}: {m.content}" for m in state.get("messages", []) if hasattr(m, "type")
    )
    result = structured.invoke(
        [
            SystemMessage(prompts.CLASSIFIER_SYSTEM),
            f"Conversation so far:\n{history}",
        ]
    )
    return {"intent": result["intent"], "constraints": result.get("constraints", {})}


def rebooking_agent(state: dict) -> dict:
    """LLM with tools bound; loops with ToolNode until it proposes a flight."""
    llm = get_llm().bind_tools([get_booking, search_flights])
    response = llm.invoke(
        [SystemMessage(prompts.rebooking_system(state)), *state.get("messages", [])]
    )
    update: dict = {"messages": [response]}
    if not response.tool_calls:
        update["proposed_solution"] = _parse_json(response.content)
    return update


def refund_agent(state: dict) -> dict:
    """Reads booking + fare rules, proposes a refund amount."""
    fare_rules = get_fare_rules.invoke(
        {"fare_type": (state.get("booking") or {}).get("fare_type", "")}
    )
    working = {**state, "fare_rules": fare_rules}
    llm = get_llm()
    response = llm.invoke(
        [SystemMessage(prompts.refund_system(working)), *state.get("messages", [])]
    )
    return {"messages": [response], "fare_rules": fare_rules, "proposed_solution": _parse_json(response.content)}


def compensation_agent(state: dict) -> dict:
    """Reads booking + delay length, proposes a compensation amount."""
    llm = get_llm()
    response = llm.invoke(
        [
            SystemMessage(prompts.compensation_system(state)),
            *state.get("messages", []),
        ]
    )
    return {"messages": [response], "proposed_solution": _parse_json(response.content)}


def policy_checker(state: dict) -> dict:
    """Plain Python: validates the proposed solution against airline rules."""
    passed, reason = check_policy(state.get("proposed_solution"), state.get("booking") or {})
    retry_count = state.get("retry_count", 0) + (0 if passed else 1)
    return {
        "policy_check": {"passed": passed, "reason": reason},
        "retry_count": retry_count,
    }


def supervisor(state: dict) -> dict:
    """Human-in-the-loop approval for refunds/compensation over $300."""
    solution = state.get("proposed_solution") or {}
    amount = solution.get("amount") or 0
    decision = interrupt(
        {
            "action": "approve_payout",
            "type": solution.get("type"),
            "amount": amount,
            "passenger": (state.get("booking") or {}).get("passenger"),
            "question": f"Payout of ${amount:.2f} exceeds $300. Approve?",
        }
    )
    approved = str(decision).strip().lower() in {"approve", "approved", "yes", "true"}
    return {"approved": approved}


def escalation_agent(state: dict) -> dict:
    """Writes the handover note for a human agent."""
    llm = get_llm()
    note = llm.invoke(
        [
            SystemMessage(prompts.ESCALATION_SYSTEM),
            prompts.escalation_context(state),
        ]
    ).content
    return {"escalated": True, "escalation_note": note}


def final_response_agent(state: dict) -> dict:
    """Writes the passenger-facing reply."""
    llm = get_llm()
    reply = llm.invoke(
        [SystemMessage(prompts.FINAL_SYSTEM), prompts.final_context(state)]
    ).content
    return {"final_response": reply, "messages": [("assistant", reply)]}
