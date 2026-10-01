from __future__ import annotations

import unicodedata
from datetime import time
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer


class InModel(BaseModel):
    """Request bodies: whitelist only (mass-assignment guard)."""

    model_config = ConfigDict(extra="forbid")  # strip explicitly per field (passwords keep whitespace)


class OutModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageOut(OutModel):
    message: str


def _no_control_chars(v: str) -> str:
    if any(unicodedata.category(ch) == "Cc" for ch in v):
        raise ValueError("Name contains invalid characters.")
    return v


def _hhmm(v: time | None) -> str | None:
    return None if v is None else v.strftime("%H:%M")


HHMMTime = Annotated[time | None, PlainSerializer(_hhmm, return_type=str | None)]


def _to_float(v: object) -> object:
    return float(v) if v is not None and not isinstance(v, (int, float)) else v


Number = Annotated[float, BeforeValidator(_to_float)]
CleanName = Annotated[str, BeforeValidator(lambda v: v.strip() if isinstance(v, str) else v)]
