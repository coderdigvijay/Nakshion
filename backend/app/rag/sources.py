"""Per-file provenance (app/rag/sources.yaml). One source of truth for system tag, display title,
authority tier, licence status and the exclusion list. A knowledge_base/_manifest.yaml, if present,
still overrides the system tag (spec §6.1)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

log = logging.getLogger("nakshion.rag")
_FILE = Path(__file__).with_name("sources.yaml")
VALID_SYSTEMS = {"vedic", "western", "both", "excluded"}


@dataclass(frozen=True)
class SourceInfo:
    stem: str
    title: str
    system: str = "both"
    tradition: str = "both"
    tier: int = 1
    licence: str = "own_written"
    language: str = "en"
    author: str | None = None
    attribute_author: bool = False
    review: bool = False
    exclude_headings: tuple[str, ...] = field(default_factory=tuple)
    confidence: str = "medium"           # high | medium | low (front-matter); low => hedge in answers
    schools_differ: bool = False         # front-matter school_notes present => "traditions differ" phrasing
    school_note: str = ""                # first sentence of school_notes (short; shown to the model, never to users)
    source_count: int = 0                # number of cited sources (URLs themselves are never stored)
    max_merge: int = 0                   # entry grouping: merge at most N adjacent small sections (0 = default)

    def display_title(self) -> str:
        """What a citation chip shows. Never a living/in-copyright author's name."""
        return self.title

    def exclude(self, heading_path: str) -> bool:
        return any(re.search(p, heading_path, re.I) for p in self.exclude_headings)

    def meta(self) -> dict:
        return {"source_title": self.display_title(), "tradition": self.tradition, "tier": self.tier,
                "licence": self.licence, "language": self.language, "review": self.review,
                "confidence": self.confidence, "schools_differ": self.schools_differ,
                **({"school_note": self.school_note} if self.school_note else {}),
                **({"source_count": self.source_count} if self.source_count else {}),
                **({"author": self.author} if self.attribute_author and self.author else {})}


@lru_cache(maxsize=1)
def _load() -> dict:
    return yaml.safe_load(_FILE.read_text(encoding="utf-8"))


_override: dict[str, str] = {}


def load_override(kb_dir: Path) -> None:
    p = kb_dir / "_manifest.yaml"
    if p.exists():
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        bad = {k: v for k, v in data.items() if v not in VALID_SYSTEMS}
        if bad:
            raise ValueError(f"invalid system tags in _manifest.yaml: {bad}")
        _override.clear()
        _override.update(data)


def _tradition(text: str, system: str) -> str:
    low = str(text or "").lower()
    if "western" in low and "vedic" not in low and "jyotish" not in low:
        return "western"
    if any(w in low for w in ("vedic", "jyotish", "parashari", "jaimini")):
        return "vedic"
    return system if system in ("vedic", "western") else "both"


def _first_sentence(text: str, limit: int = 220) -> str:
    t = " ".join(str(text or "").split())
    m = re.match(r"(.+?[.!?])(\s|$)", t)
    return (m.group(1) if m else t)[:limit]


def source_info(stem: str, front: dict | None = None) -> SourceInfo:
    """sources.yaml entry (explicit) > file front-matter > defaults. Unknown/invalid front-matter values warn."""
    cfg = _load()
    d = dict(cfg.get("defaults", {}))
    f = cfg["files"].get(stem)
    front = front or {}
    if f is None and front:
        sysname = front.get("system", "both")
        if sysname not in VALID_SYSTEMS:
            log.warning("front-matter of %s has invalid system %r; using 'both'", stem, sysname)
            sysname = "both"
        tier = front.get("tier", 3)
        if tier not in (1, 2, 3):
            log.warning("front-matter of %s has invalid tier %r; using 3", stem, tier)
            tier = 3
        lang = str(front.get("language", "en"))
        conf = str(front.get("confidence", "medium")).lower()
        f = {"title": str(front.get("title") or stem.replace("_", " ").title())[:90], "system": sysname, "tier": tier,
             "language": lang, "confidence": conf if conf in ("high", "medium", "low") else "medium",
             "tradition": _tradition(front.get("tradition"), sysname),
             "licence": front.get("licence") or ("researched_synthesis" if front.get("sources") else "own_written"),
             "schools_differ": bool(front.get("school_notes")), "school_note": _first_sentence(front.get("school_notes")),
             "source_count": len(front.get("sources") or []), "review": conf == "low"}
    if f is None:
        log.warning("kb file %s has no entry in sources.yaml and no front-matter; defaulting to tier 3, review=true", stem)
        d.update({"tier": 3, "review": True})
        f = {"title": stem.replace("_", " ").title(), "system": "both"}
    d.update(f)
    system = _override.get(stem, d.get("system", "both"))
    return SourceInfo(
        stem=stem, title=d.get("title", stem), system=system, tradition=d.get("tradition", "both"),
        tier=int(d.get("tier", 1)), licence=d.get("licence", "own_written"), language=d.get("language", "en"),
        author=d.get("author"), attribute_author=bool(d.get("attribute_author", False)),
        review=bool(d.get("review", False)), exclude_headings=tuple(d.get("exclude_headings", ()) or ()),
        confidence=d.get("confidence", "medium"), schools_differ=bool(d.get("schools_differ", False)),
        school_note=d.get("school_note", ""), source_count=int(d.get("source_count", 0)),
        max_merge=int(d.get("max_merge", 0)))


def all_stems() -> list[str]:
    return sorted(_load()["files"])
