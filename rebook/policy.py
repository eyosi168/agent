"""Pure-Python policy checks (no LLM)."""

from datetime import datetime

from .data import NOW

CABIN_RANK = {"economy": 0, "premium_economy": 1, "business": 2, "first": 3}


def _check_rebook(solution: dict, booking: dict) -> tuple[bool, str]:
    flight = solution.get("flight")
    if not isinstance(flight, dict):
        return False, "proposed solution has no flight details"

    booked_cabin = str(booking.get("cabin_class", "")).lower()
    proposed_cabin = str(flight.get("cabin", "")).lower()
    if CABIN_RANK.get(proposed_cabin, -1) > CABIN_RANK.get(booked_cabin, -1):
        return False, (
            f"proposed cabin '{proposed_cabin}' is higher than booked cabin "
            f"'{booked_cabin}'; rule: same cabin class or lower"
        )

    try:
        departure = datetime.fromisoformat(flight.get("departure", ""))
    except ValueError:
        return False, "proposed flight has no valid departure time"

    hours_until_departure = (departure - NOW).total_seconds() / 3600
    if not 0 <= hours_until_departure <= 48:
        return False, (
            f"flight departs {hours_until_departure:.0f}h from now; "
            "rule: must depart within 48 hours"
        )

    connection = flight.get("connection_minutes")
    if connection is not None and connection < 60:
        return False, (
            f"connection time is {connection} minutes; "
            "rule: connection time must be at least 60 minutes"
        )

    return True, ""


def _check_refund(solution: dict, booking: dict) -> tuple[bool, str]:
    amount = solution.get("amount")
    if not isinstance(amount, (int, float)):
        return False, "proposed refund amount is missing or not a number"

    cause = booking.get("disruption", {}).get("cause")
    if cause == "airline":
        expected = booking.get("fare_price")
        if abs(amount - expected) < 0.01:
            return True, ""
        return False, f"airline cancelled: refund must be full fare ({expected}), got {amount}"

    fare_rules = solution.get("fare_rules") or {}
    if not fare_rules.get("refundable", False):
        expected = fare_rules.get("tax_amount", 0)
        if abs(amount - expected) < 0.01:
            return True, ""
        return False, (
            f"non-refundable fare chosen by passenger: refund limited to taxes "
            f"({expected}), got {amount}"
        )

    if amount <= 0:
        return False, "refundable fare: refund must be positive"
    return True, ""


def _check_compensation(solution: dict, booking: dict) -> tuple[bool, str]:
    amount = solution.get("amount")
    if not isinstance(amount, (int, float)):
        return False, "proposed compensation amount is missing or not a number"

    disruption = booking.get("disruption", {})
    if disruption.get("type") == "cancelled":
        expected = 400
    else:
        hours = disruption.get("delay_hours", 0)
        if hours < 3:
            expected = 0
        elif hours <= 6:
            expected = 200
        else:
            expected = 400

    if abs(amount - expected) < 0.01:
        return True, ""
    return False, f"compensation must be {expected} for this disruption, got {amount}"


def check_policy(solution: dict | None, booking: dict) -> tuple[bool, str]:
    """Apply the airline policy rules to a proposed solution."""
    if not solution or not solution.get("type"):
        return False, (
            "no solution was proposed (agent output was missing or not valid JSON)"
        )

    stype = solution["type"]
    if stype == "rebook":
        return _check_rebook(solution, booking)
    if stype == "refund":
        return _check_refund(solution, booking)
    if stype == "compensation":
        return _check_compensation(solution, booking)
    return False, f"unknown solution type '{stype}'"
