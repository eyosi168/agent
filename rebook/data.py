"""Deterministic mock data. Same input always produces the same result."""

from datetime import datetime

# Fixed reference clock so the 48-hour rebooking rule is deterministic.
NOW = datetime(2026, 10, 15, 8, 0)
NOW_ISO = NOW.isoformat()

BOOKINGS: dict[str, dict] = {
    "XK9L2P": {
        "booking_ref": "XK9L2P",
        "passenger": "Amira Hassan",
        "origin": "LHR",
        "destination": "DXB",
        "cabin_class": "economy",
        "fare_type": "standard_economy",
        "fare_price": 640.0,
        "currency": "USD",
        "flight_number": "BA112",
        "disruption": {
            "type": "cancelled",
            "cause": "airline",
            "scheduled_departure": "2026-10-15T14:30",
            "delay_hours": 0,
        },
    },
    "YQ7T3M": {
        "booking_ref": "YQ7T3M",
        "passenger": "Daniel Ortiz",
        "origin": "JFK",
        "destination": "LAX",
        "cabin_class": "economy",
        "fare_type": "flex_economy",
        "fare_price": 412.5,
        "currency": "USD",
        "flight_number": "AA318",
        "disruption": {
            "type": "delayed",
            "cause": "airline",
            "scheduled_departure": "2026-10-15T16:00",
            "delay_hours": 6,
        },
    },
    "MB4R8K": {
        "booking_ref": "MB4R8K",
        "passenger": "Yuki Tanaka",
        "origin": "LHR",
        "destination": "HND",
        "cabin_class": "economy",
        "fare_type": "standard_economy",
        "fare_price": 890.0,
        "currency": "USD",
        "flight_number": "JL042",
        "disruption": {
            "type": "cancelled",
            "cause": "airline",
            "scheduled_departure": "2026-10-15T20:00",
            "delay_hours": 0,
        },
    },
    "PK2W9C": {
        "booking_ref": "PK2W9C",
        "passenger": "Robert Klein",
        "origin": "FRA",
        "destination": "JFK",
        "cabin_class": "economy",
        "fare_type": "standard_economy",
        "fare_price": 520.0,
        "currency": "USD",
        "flight_number": "LH402",
        "disruption": {
            "type": "cancelled",
            "cause": "airline",
            "scheduled_departure": "2026-10-14T11:00",
            "delay_hours": 0,
        },
    },
}

FARE_RULES: dict[str, dict] = {
    "standard_economy": {"refundable": False, "tax_amount": 96.0},
    "flex_economy": {"refundable": True, "tax_amount": 118.5},
}

# (origin, destination) -> list of flights.
# LHR->DXB (scenario 1): one policy-clean economy option, plus traps
#   (late arrival, 45-minute connection, business-class-only).
# LHR->HND (scenario 3): every option is business-class-only, so the
#   policy check can never pass and the retry loop is exercised.
FLIGHTS: dict[tuple[str, str], list[dict]] = {
    ("LHR", "DXB"): [
        {
            "flight_number": "EK005",
            "origin": "LHR",
            "destination": "DXB",
            "departure": "2026-10-15T21:00",
            "arrival": "2026-10-16T06:30",
            "cabins_available": ["economy", "business"],
            "stops": 0,
            "connection_minutes": None,
            "price": 580.0,
        },
        {
            "flight_number": "BA118",
            "origin": "LHR",
            "destination": "DXB",
            "departure": "2026-10-16T08:00",
            "arrival": "2026-10-16T17:00",
            "cabins_available": ["economy", "business"],
            "stops": 0,
            "connection_minutes": None,
            "price": 605.0,
        },
        {
            "flight_number": "EK091",
            "origin": "LHR",
            "destination": "DXB",
            "departure": "2026-10-16T02:00",
            "arrival": "2026-10-16T14:00",
            "cabins_available": ["economy"],
            "stops": 1,
            "connection_minutes": 45,
            "price": 512.0,
        },
        {
            "flight_number": "EY998",
            "origin": "LHR",
            "destination": "DXB",
            "departure": "2026-10-16T05:00",
            "arrival": "2026-10-16T13:00",
            "cabins_available": ["business"],
            "stops": 0,
            "connection_minutes": None,
            "price": 1450.0,
        },
    ],
    ("LHR", "HND"): [
        {
            "flight_number": "JL044",
            "origin": "LHR",
            "destination": "HND",
            "departure": "2026-10-16T10:00",
            "arrival": "2026-10-17T06:00",
            "cabins_available": ["business"],
            "stops": 0,
            "connection_minutes": None,
            "price": 4260.0,
        },
        {
            "flight_number": "NH212",
            "origin": "LHR",
            "destination": "HND",
            "departure": "2026-10-16T13:30",
            "arrival": "2026-10-17T09:45",
            "cabins_available": ["business"],
            "stops": 1,
            "connection_minutes": 90,
            "price": 3980.0,
        },
    ],
}
