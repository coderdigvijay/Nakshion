"""The finite vocabulary of factor `kb_keys` (llm-integration.md §6.3: "the factor kb_keys form a finite set,
so they're pre-embedded at index time").

Mirrors the key templates of BOTH producers:
  - app/astrology/personal.py (engine personal_day factors)
  - app/llm/facts.py::derive_factors (natal factors derived from chart_data)
A test (tests/rag/test_keys.py) generates real charts and asserts every emitted key is in this set, so the
two cannot drift apart silently. With the keys pre-embedded, a retrieval needs ZERO runtime embeddings for
them; only the user's question is embedded at query time.

    python -m app.rag.keys --out keys.txt          # then: python -m app.rag.ingest --kb-keys-file keys.txt
(ingest generates and embeds them automatically when --kb-keys-file is not given)
"""

from __future__ import annotations

import argparse
from functools import lru_cache

from app.llm.facts import ordinal
from app.llm.lexicon import NAKSHATRAS, SIGNS

PLANETS = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
NODES = ["north node", "south node", "rahu", "ketu"]
ANGLES = ["asc", "mc"]
ASPECTS = ["conjunction", "opposition", "square", "trine", "sextile", "quincunx", "semi-sextile", "semi-square",
           "sesquiquadrate", "conjunct", "opposite"]
VEDIC_RASHI = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius",
               "capricorn", "aquarius", "pisces"]
LORDS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]
TITHIS = ["pratipada", "dwitiya", "tritiya", "chaturthi", "panchami", "shashthi", "saptami", "ashtami", "navami",
          "dashami", "ekadashi", "dwadashi", "trayodashi", "chaturdashi", "purnima", "amavasya"]
YOGAS = ["gajakesari yoga", "raja yoga", "dhana yoga", "mangal dosha", "kaal sarp dosha", "budhaditya yoga",
         "pancha mahapurusha yoga", "ruchaka yoga", "bhadra yoga", "hamsa yoga", "malavya yoga", "sasa yoga",
         "chandra mangala yoga", "neecha bhanga raja yoga", "viparita raja yoga", "kemadruma yoga"]


def _engine_yoga_names() -> list[str]:
    """Yoga/dosha names exactly as the engine emits them (read from app/astrology/yogas.py, so this follows the engine)."""
    import re
    from pathlib import Path

    try:
        src = (Path(__file__).resolve().parents[1] / "astrology" / "yogas.py").read_text(encoding="utf-8")
    except OSError:
        return []
    return sorted({m.lower() for m in re.findall(r'"([A-Z][A-Za-z\- ]+ (?:Yoga|Dosha))"', src)})


@lru_cache(maxsize=1)
def generate_keys() -> list[str]:
    k: set[str] = set()
    bodies = PLANETS + NODES
    for p in bodies:
        for s in SIGNS:
            k.add(f"{p} in {s.lower()}")
            k.add(f"{p} in {s.lower()} vedic")
        for h in range(1, 13):
            k.add(f"{p} in the {ordinal(h)} house")
        k.add(f"{p} transit")
    for s in SIGNS:
        k.update({f"{s.lower()} rising", f"{s.lower()} lagna"})
    for a in PLANETS + NODES + ANGLES:
        for b in PLANETS + NODES + ANGLES:
            for t in ASPECTS[:5]:
                if a != b:
                    k.add(f"{a} {t} {b}")
                if a in PLANETS:                       # a transiting planet may aspect its own natal position
                    k.add(f"{a} {b} {t} transit")
    for n in NAKSHATRAS:
        k.add(f"{n.lower()} nakshatra")
    for lord in LORDS:
        k.update({f"{lord} dasha", f"{lord} mahadasha", f"{lord} antardasha"})
    for h in range(1, 13):
        k.add(f"moon transit house {h}")
    # Vedic gochara factors (engine personal.py: G.<graha>.H<n>, G.<graha>.CONJ|OPPO.N.<point>)
    grahas = LORDS
    for g in grahas:
        k.update({f"{g} gochara", f"{g} transit from moon"})
        for h in range(1, 13):
            k.add(f"{g} gochara house {h}")
        for n in grahas + ["lagna"]:
            k.update({f"{g} {n} conjunction gochara", f"{g} {n} opposition gochara"})
    k.update({"moon gochara", "sade sati", "sade sati rising", "sade sati peak", "sade sati setting", "daily guidance"})
    for t in TITHIS:
        k.add(f"{t} tithi")
    k.update(YOGAS)
    for y in _engine_yoga_names():
        k.update({y, y.replace("-", " ")})
    return sorted(k)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    keys = generate_keys()
    open(a.out, "w", encoding="utf-8").write("\n".join(keys) + "\n")
    print(f"wrote {len(keys)} keys to {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
