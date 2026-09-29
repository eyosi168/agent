"""Mock tools returning fixed fake data."""

from langchain_core.tools import tool

from .data import BOOKINGS, FARE_RULES, FLIGHTS


@tool
def get_booking(booking_ref: str) -> dict:
    """Look up a passenger booking by booking reference.

    Returns passenger name, route, cabin class, fare type, fare price and
    disruption details (delay or cancellation).
    """
    return BOOKINGS.get(booking_ref, {"error": f"booking {booking_ref} not found"})


@tool
def search_flights(origin: str, destination: str, date: str) -> dict:
    """Search available flights on a route for a given date (YYYY-MM-DD).

    Returns a list of flights with departure/arrival times, available cabins,
    stops and connection time in minutes.
    """
    key = (origin.upper(), destination.upper())
    flights = FLIGHTS.get(key, [])
    return {
        "origin": origin.upper(),
        "destination": destination.upper(),
        "date": date,
        "flights": flights,
        "note": "All times are local; connection_minutes is null for direct flights.",
    }


@tool
def get_fare_rules(fare_type: str) -> dict:
    """Look up refund rules for a fare type.

    Returns whether the fare is refundable and the tax amount.
    """
    return FARE_RULES.get(fare_type, {"error": f"fare type {fare_type} not found"})


ALL_TOOLS = [get_booking, search_flights, get_fare_rules]
