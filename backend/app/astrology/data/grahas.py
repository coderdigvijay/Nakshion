"""Vedic dignities, natural relationships, combustion orbs, dasha years (spec 2.4-2.6, 5.2)."""

from __future__ import annotations

from typing import Final, NamedTuple


class Dignity(NamedTuple):
    exalt_sign: int
    debil_sign: int
    mooltrikona: tuple[int, float, float] | None  # (sign, from_deg, to_deg)
    own: tuple[int, ...]


# Sign indices: Aries 0 ... Pisces 11.
DIGNITIES: Final = {
    "Sun": Dignity(0, 6, (4, 0.0, 20.0), (4,)),
    "Moon": Dignity(1, 7, (1, 3.0, 30.0), (3,)),
    "Mars": Dignity(9, 3, (0, 0.0, 12.0), (0, 7)),
    "Mercury": Dignity(5, 11, (5, 15.0, 20.0), (2, 5)),
    "Jupiter": Dignity(3, 9, (8, 0.0, 10.0), (8, 11)),
    "Venus": Dignity(11, 5, (6, 0.0, 15.0), (1, 6)),
    "Saturn": Dignity(6, 0, (10, 0.0, 20.0), (9, 10)),
    # Node school is configurable; spec default Taurus/Scorpio.
    "Rahu": Dignity(1, 7, None, ()),
    "Ketu": Dignity(7, 1, None, ()),
}

# Naisargika relationships (spec 2.5): planet -> (friends, neutrals, enemies)
RELATIONSHIPS: Final = {
    "Sun": ({"Moon", "Mars", "Jupiter"}, {"Mercury"}, {"Venus", "Saturn"}),
    "Moon": ({"Sun", "Mercury"}, {"Mars", "Jupiter", "Venus", "Saturn"}, set()),
    "Mars": ({"Sun", "Moon", "Jupiter"}, {"Venus", "Saturn"}, {"Mercury"}),
    "Mercury": ({"Sun", "Venus"}, {"Mars", "Jupiter", "Saturn"}, {"Moon"}),
    "Jupiter": ({"Sun", "Moon", "Mars"}, {"Saturn"}, {"Mercury", "Venus"}),
    "Venus": ({"Mercury", "Saturn"}, {"Mars", "Jupiter"}, {"Sun", "Moon"}),
    "Saturn": ({"Mercury", "Venus"}, {"Jupiter"}, {"Sun", "Moon", "Mars"}),
}
# Rahu uses Saturn's row, Ketu uses Mars's row (spec 2.5, configurable).
NODE_RELATIONSHIP_ROW: Final = {"Rahu": "Saturn", "Ketu": "Mars"}

# Combustion orbs in degrees from the Sun: (direct, retrograde). Spec 2.6.
COMBUSTION_ORBS: Final = {
    "Moon": (12.0, 12.0), "Mars": (17.0, 17.0), "Mercury": (14.0, 12.0),
    "Jupiter": (11.0, 11.0), "Venus": (10.0, 8.0), "Saturn": (15.0, 15.0),
}

# Vimshottari (spec 5.2). Order and years; total 120.
DASHA_ORDER: Final = ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury")
DASHA_YEARS: Final = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}
DASHA_YEAR_DAYS: Final = 365.25

NATURAL_BENEFICS: Final = frozenset({"Jupiter", "Venus", "Mercury"})  # + waxing Moon
NATURAL_MALEFICS: Final = frozenset({"Sun", "Mars", "Saturn"})       # + waning Moon

# Graha drishti (spec 5.5): special aspects counted inclusively from the planet's sign.
DRISHTI: Final = {
    "Sun": (7,), "Moon": (7,), "Mercury": (7,), "Venus": (7,),
    "Mars": (4, 7, 8), "Jupiter": (5, 7, 9), "Saturn": (3, 7, 10),
}
NODE_ASPECTS: Final = "none"  # | "5_7_9" (school-dependent)
