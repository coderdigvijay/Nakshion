"""Signs and bodies (spec sections 2.1, 2.2)."""

from __future__ import annotations

from typing import Final

SIGNS: Final = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)
RASHIS: Final = (
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena",
)
ELEMENTS: Final = ("fire", "earth", "air", "water") * 3
MODALITIES: Final = ("cardinal", "fixed", "mutable") * 4
# Traditional lords (Scorpio = Mars; Pluto is never used for lordship).
SIGN_LORDS: Final = (
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
)

# English key -> Vedic name (spec 2.2).
VEDIC_NAMES: Final = {
    "Sun": "Surya", "Moon": "Chandra", "Mercury": "Budha", "Venus": "Shukra", "Mars": "Mangala",
    "Jupiter": "Guru", "Saturn": "Shani", "Uranus": "Uranus", "Neptune": "Neptune",
    "Pluto": "Pluto", "Rahu": "Rahu", "Ketu": "Ketu",
}

CLASSICAL: Final = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
OUTER: Final = ("Uranus", "Neptune", "Pluto")
WESTERN_PLANETS: Final = (
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
)
# Vedic list order as in the spec section 9 example.
VEDIC_ORDER: Final = CLASSICAL + ("Rahu", "Ketu") + OUTER


def sign_index(name: str) -> int:
    """Accepts a Western sign or a rashi name, case-insensitive."""
    key = name.strip().lower()
    for table in (SIGNS, RASHIS):
        for i, s in enumerate(table):
            if s.lower() == key:
                return i
    raise ValueError(f"unknown sign: {name!r}")
