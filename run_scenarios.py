"""Runs all 4 scenarios + the follow-up message. Single command:
    python run_scenarios.py
"""

import io
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from langgraph.types import Command

from rebook import build_graph, default_checkpointer

AUTO_APPROVAL = "approve"  # auto-answer for the supervisor interrupt (bonus)

SCENARIOS = [
    {
        "id": 1,
        "name": "Cancelled flight, must arrive by noon",
        "thread_id": "scenario-1",
        "input": {
            "request_id": "R-7702",
            "booking_ref": "XK9L2P",
            "messages": [
                (
                    "user",
                    "My flight to Dubai was cancelled. I need to be there by tomorrow noon.",
                )
            ],
        },
        "followup": ("user", "Actually, can I get a refund instead?"),
    },
    {
        "id": 2,
        "name": "6-hour delay, asks about compensation",
        "thread_id": "scenario-2",
        "input": {
            "request_id": "R-7703",
            "booking_ref": "YQ7T3M",
            "messages": [("user", "My flight is delayed 6 hours. Am I entitled to anything?")],
        },
    },
    {
        "id": 3,
        "name": "Only business-class seats available",
        "thread_id": "scenario-3",
        "input": {
            "request_id": "R-7704",
            "booking_ref": "MB4R8K",
            "messages": [
                (
                    "user",
                    "My flight to Tokyo was cancelled and every option you have is business class.",
                )
            ],
        },
    },
    {
        "id": 4,
        "name": "Complaint asking for a manager",
        "thread_id": "scenario-4",
        "input": {
            "request_id": "R-7705",
            "booking_ref": "PK2W9C",
            "messages": [
                (
                    "user",
                    "This is the third time you've cancelled on me. I want to speak to a manager.",
                )
            ],
        },
    },
]


def run_turn(app, payload, config) -> tuple[list[str], str]:
    """Invoke the graph, collecting the node path; auto-resume interrupts."""
    path: list[str] = []
    stream = app.stream(payload, config, stream_mode="updates")
    while True:
        for update in stream:
            if "__interrupt__" in update:
                stream.close()
                print("    [interrupt] supervisor approval required -> auto-approving")
                path.append("supervisor(interrupt)")
                stream = app.stream(
                    Command(resume=AUTO_APPROVAL), config, stream_mode="updates"
                )
                break
            path.extend(update.keys())
        else:
            break
    state = app.get_state(config).values
    return path, state.get("final_response", "<no response>")


def main() -> None:
    # Fresh checkpoint DB each run so results are reproducible.
    import os

    if os.path.exists("checkpoints.db"):
        os.remove("checkpoints.db")

    app = build_graph(checkpointer=default_checkpointer())
    config = {"recursion_limit": 50}

    for scenario in SCENARIOS:
        cfg = {**config, "configurable": {"thread_id": scenario["thread_id"]}}
        print("=" * 78)
        print(f"Scenario {scenario['id']}: {scenario['name']}")
        print(f"Input: {scenario['input']['messages'][0][1]}")
        print("-" * 78)

        path, reply = run_turn(app, scenario["input"], cfg)
        print(f"Path: {' -> '.join(path)}")
        print(f"Final response:\n{reply}")

        if scenario.get("followup"):
            _, role_text = scenario["followup"]
            print("-" * 78)
            print(f"Follow-up (same thread_id): {role_text}")
            path, reply = run_turn(app, {"messages": [scenario["followup"]]}, cfg)
            print(f"Path: {' -> '.join(path)}")
            print(f"Final response:\n{reply}")
        print()

    mermaid = app.get_graph().draw_mermaid()
    with open("docs/graph.mermaid", "w", encoding="utf-8") as f:
        f.write(mermaid)
    print("Graph diagram saved to docs/graph.mermaid")


if __name__ == "__main__":
    main()
