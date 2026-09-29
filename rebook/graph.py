"""StateGraph assembly: nodes, conditional edges, retry cycle, checkpointer."""

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .nodes import (
    classifier,
    compensation_agent,
    escalation_agent,
    final_response_agent,
    intake,
    policy_checker,
    refund_agent,
    rebooking_agent,
    supervisor,
)
from .state import RebookingState
from .tools import ALL_TOOLS

# Which specialist proposed the current solution (for the retry cycle).
PROPOSER_BY_TYPE = {
    "rebook": "rebooking_agent",
    "refund": "refund_agent",
    "compensation": "compensation_agent",
}


def route_intent(state: dict) -> str:
    """Classifier router: complaints go straight to escalation."""
    return {
        "rebook": "rebooking_agent",
        "refund": "refund_agent",
        "compensation": "compensation_agent",
        "complaint": "escalation_agent",
    }[state["intent"]]


def route_policy(state: dict) -> str:
    """Policy router: pass -> approval or final; fail -> retry the same agent
    up to 2 retries, then escalation; supervisor rejects -> escalation."""
    check = state.get("policy_check") or {}
    if check.get("passed"):
        solution = state.get("proposed_solution") or {}
        needs_approval = (
            solution.get("type") in {"refund", "compensation"}
            and (solution.get("amount") or 0) > 300
        )
        return "supervisor" if needs_approval else "final_response_agent"
    if state.get("retry_count", 0) >= 3:
        return "escalation_agent"
    stype = (state.get("proposed_solution") or {}).get("type")
    return PROPOSER_BY_TYPE.get(stype, "rebooking_agent")


def route_supervisor(state: dict) -> str:
    """Approved payout -> final reply; rejected -> escalation."""
    return "final_response_agent" if state.get("approved") else "escalation_agent"


def build_graph(checkpointer=None) -> StateGraph:
    graph = StateGraph(RebookingState)

    graph.add_node("intake", intake)
    graph.add_node("classifier", classifier)
    graph.add_node("rebooking_agent", rebooking_agent)
    graph.add_node("refund_agent", refund_agent)
    graph.add_node("compensation_agent", compensation_agent)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.add_node("policy_checker", policy_checker)
    graph.add_node("supervisor", supervisor)
    graph.add_node("escalation_agent", escalation_agent)
    graph.add_node("final_response_agent", final_response_agent)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "classifier")

    # Conditional edge 1: intent routing.
    graph.add_conditional_edges(
        "classifier",
        route_intent,
        ["rebooking_agent", "refund_agent", "compensation_agent", "escalation_agent"],
    )

    # Tool-calling loop: agent -> ToolNode -> agent, until no tool calls.
    graph.add_conditional_edges(
        "rebooking_agent",
        tools_condition,
        {"tools": "tools", "__end__": "policy_checker"},
    )
    graph.add_edge("tools", "rebooking_agent")

    graph.add_edge("refund_agent", "policy_checker")
    graph.add_edge("compensation_agent", "policy_checker")

    # Conditional edge 2: policy pass/fail with the retry cycle back to the agent.
    graph.add_conditional_edges(
        "policy_checker",
        route_policy,
        ["rebooking_agent", "refund_agent", "compensation_agent", "supervisor", "final_response_agent", "escalation_agent"],
    )

    # Conditional edge 3: supervisor approval.
    graph.add_conditional_edges(
        "supervisor", route_supervisor, ["final_response_agent", "escalation_agent"]
    )

    graph.add_edge("escalation_agent", "final_response_agent")
    graph.add_edge("final_response_agent", END)

    return graph.compile(checkpointer=checkpointer)


def default_checkpointer(db_path: str = "checkpoints.db"):
    """SQLite checkpointer: threads survive restarts (bonus item)."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return SqliteSaver(conn)
