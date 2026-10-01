"""Ashtakoota (Guna Milan) matrices (spec section 7.2).

Varna, Tara, Graha Maitri, Bhakoot and Nadi are fully specified by the spec and implemented in
compatibility.py. Yoni, Vashya and Gana come from matrices, which differ between schools and
software. ALL THREE are transcribed from ONE named reference:

    Saravali / Maitreya 8 documentation, "Asta Koota" pages (CC BY-SA 4.0, last modified
    2017-10-30), retrieved 2026-10-01:
      https://saravali.github.io/astrology/koota_yoni.html
      https://saravali.github.io/astrology/koota_vashya.html
      https://saravali.github.io/astrology/koota_gana.html
    Matrix orientation in the source: rows = bride, columns = groom.

SCHOOL VARIANT, NOT YET FIXTURE-VERIFIED: the spec requires 30 Prokerala `kundli-matching`
golden pairs with 0 tolerance; none exist yet (no API key in this environment). If those
fixtures disagree, the fixture's provider convention wins and this file changes (minor bump).

Known deviation from the source: Saravali's Vashya sign list omits Sagittarius. The classical
half-sign split (1st half Sagittarius = Manava/human, 2nd half = Chatushpada/quadruped;
1st half Capricorn = Chatushpada, 2nd half = Jalachara) is used, as in e.g.
https://www.astrosaxena.com/asmh2 and https://freehoroscopesonline.in/vashyakoota.php .
"""

from __future__ import annotations

from typing import Final

SOURCE: Final = "Saravali/Maitreya 8 Asta Koota tables (rows=bride, cols=groom), CC BY-SA 4.0"
FIXTURE_VERIFIED: Final = False

YONIS: Final = (
    "Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat",
    "Cow", "Buffalo", "Tiger", "Deer", "Monkey", "Mongoose", "Lion",
)

# YONI_MATRIX[bride_yoni][groom_yoni]
YONI_MATRIX: Final = (
    (4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 3, 3, 2, 1),  # Horse
    (2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0),  # Elephant
    (2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1),  # Sheep
    (3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2),  # Serpent
    (2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1),  # Dog
    (2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1),  # Cat
    (2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2),  # Rat
    (1, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1),  # Cow
    (0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1),  # Buffalo
    (1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1),  # Tiger
    (1, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1),  # Deer
    (3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2),  # Monkey
    (2, 2, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2),  # Mongoose
    (1, 0, 1, 2, 1, 1, 2, 1, 2, 1, 1, 2, 2, 4),  # Lion
)

# Sworn-enemy pairs that the spec pins to 0 (asserted in tests).
YONI_ENEMIES: Final = (
    ("Horse", "Buffalo"), ("Elephant", "Lion"), ("Sheep", "Monkey"), ("Serpent", "Mongoose"),
    ("Dog", "Deer"), ("Cat", "Rat"), ("Cow", "Tiger"),
)

VASHYA_GROUPS: Final = ("Chatushpada", "Manava", "Jalachara", "Vanachara", "Keeta")
_C, _MA, _J, _V, _K = range(5)


def vashya_group(sign_idx: int, degree_in_sign: float) -> int:
    first_half = degree_in_sign < 15.0
    if sign_idx in (0, 1):
        return _C
    if sign_idx in (2, 5, 6, 10):
        return _MA
    if sign_idx in (3, 11):
        return _J
    if sign_idx == 4:
        return _V
    if sign_idx == 7:
        return _K
    if sign_idx == 8:
        return _MA if first_half else _C
    if sign_idx == 9:
        return _C if first_half else _J
    raise ValueError(sign_idx)


# VASHYA_MATRIX[bride_group][groom_group]
VASHYA_MATRIX: Final = (
    (2, 0, 0, 0.5, 0),    # Chatushpada (quadruped)
    (1, 2, 1, 0.5, 1),    # Manava (human)
    (0.5, 1, 2, 1, 1),    # Jalachara (water)
    (0, 0, 0, 2, 0),      # Vanachara (Leo)
    (1, 1, 1, 0, 2),      # Keeta (Scorpio)
)

GANAS: Final = ("Deva", "Manushya", "Rakshasa")
# GANA_MATRIX[bride_gana][groom_gana]
GANA_MATRIX: Final = (
    (6, 6, 0),  # Deva bride
    (5, 6, 0),  # Manushya bride
    (1, 0, 6),  # Rakshasa bride
)

# Varna rank by Moon rashi (spec 7.2): Brahmin 3 > Kshatriya 2 > Vaishya 1 > Shudra 0.
VARNA_RANK: Final = (2, 1, 0, 3, 2, 1, 0, 3, 2, 1, 0, 3)
VARNA_NAMES: Final = ("Shudra", "Vaishya", "Kshatriya", "Brahmin")
