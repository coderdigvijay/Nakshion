"""YAML front-matter for knowledge-base files (title, tradition, system, tier, language, sources, confidence,
school_notes). Ingestion reads it so a new file needs no manual entry in sources.yaml; a malformed block warns and
the file is still indexed with defaults. `sources` (raw URLs) is counted, never stored in chunk meta or shown."""

from __future__ import annotations

import logging
import re

import yaml

log = logging.getLogger("nakshion.rag")
_FM = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def split_front_matter(text: str, name: str = "") -> tuple[dict, str]:
    """-> (front-matter dict, body without the block). Never raises."""
    m = _FM.match(text)
    if not m:
        return {}, text
    try:
        data = yaml.safe_load(m.group(1)) or {}
        if not isinstance(data, dict):
            raise ValueError("front-matter is not a mapping")
    except Exception as exc:  # noqa: BLE001 - warn, keep indexing the body
        log.warning("bad front-matter in %s: %s", name or "?", type(exc).__name__)
        data = {}
    return data, text[m.end():]
