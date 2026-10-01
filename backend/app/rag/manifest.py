"""Back-compat shim: system tag per file now lives in app/rag/sources.yaml (see app/rag/sources.py)."""

from __future__ import annotations

from app.rag.sources import load_override, source_info  # noqa: F401


def system_for(stem: str) -> str:
    return source_info(stem).system
