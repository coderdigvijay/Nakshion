"""Engine errors. Input errors carry a stable `.code` the API layer maps to a response."""

from __future__ import annotations


class AstroInputError(ValueError):
    """Bad birth input. `code` is one of:
    BIRTH_TIME_NONEXISTENT, DATE_OUT_OF_RANGE, INVALID_LOCATION, INVALID_TIMEZONE, INVALID_INPUT.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class EphemerisUnavailableError(RuntimeError):
    """Swiss Ephemeris data files missing or pyswisseph fell back to Moshier.

    Never caught inside the engine: a chart computed on Moshier must not be stored silently
    (astrology_accuracy_rules.md section 2, PITFALLS #12). Fail the readiness probe.
    """
