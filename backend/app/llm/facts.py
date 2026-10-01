"""CHART FACTS: the authoritative, machine-generated context for every interpretation prompt.

Input is the engine's `chart_data` (docs/astrology-engine.md §9) plus, when available, the
engine's ranked `Factor`s (§6.4, `select_factors`). This module never computes a position:
it only reformats values the engine already computed. When the engine's factors are not
passed in, `derive_factors` turns the stored chart_data into Factor views with the same ID
scheme so citations still work (lower-fidelity: no transits, no weights from scoring.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable

from app.llm.lexicon import canon_planet, canon_sign

def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _slug(s: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", s.upper()).strip("_")


@dataclass(frozen=True)
class FactorView:
    """Mirror of the engine's Factor (astrology-engine.md §6.4). Built from engine objects or dicts."""

    id: str
    kind: str
    label: str
    topics: tuple[str, ...] = ()
    weight: float = 0.5
    valence: float = 0.0
    window: tuple[str, str] | None = None
    kb_keys: tuple[str, ...] = ()

    @classmethod
    def coerce(cls, f: Any) -> "FactorView":
        if isinstance(f, FactorView):
            return f
        get = f.get if isinstance(f, dict) else (lambda k, d=None: getattr(f, k, d))
        win = get("window")
        return cls(
            id=str(get("id")), kind=str(get("kind", "natal")), label=str(get("label")),
            topics=tuple(get("topics", ()) or ()), weight=float(get("weight", 0.5) or 0.5),
            valence=float(get("valence", 0.0) or 0.0),
            window=(str(win[0]), str(win[1])) if win else None,
            kb_keys=tuple(get("kb_keys", ()) or ()),
        )


# ----------------------------------------------------------------------------- chart index


@dataclass
class ChartIndex:
    """Lookup tables the claim checker resolves claims against."""

    approximate_time: bool
    western: dict[str, tuple[str | None, int | None, bool]] = field(default_factory=dict)  # planet -> (sign, house, retro)
    vedic: dict[str, tuple[str | None, int | None, bool, str | None]] = field(default_factory=dict)
    rising: str | None = None
    lagna: str | None = None
    aspects: set[tuple[str, str, str]] = field(default_factory=set)  # (p1, type, p2) sorted planets
    maha: str | None = None
    antar: str | None = None
    nakshatras: set[str] = field(default_factory=set)
    birth_year: int | None = None

    @classmethod
    def from_chart(cls, chart: dict) -> "ChartIndex":
        meta = chart.get("metadata", {}) or {}
        idx = cls(approximate_time=bool(meta.get("approximate_time")))
        for p in chart.get("planets", []) or []:
            name = canon_planet(p.get("name", "")) or p.get("name")
            idx.western[name] = (canon_sign(p.get("sign", "") or ""), p.get("house"), bool(p.get("retrograde")))
        rs = chart.get("rising_sign") or {}
        idx.rising = canon_sign(rs.get("sign", "") or "") if rs else None
        for a in chart.get("aspects", []) or []:
            p1, p2 = canon_planet(a.get("planet1", "")), canon_planet(a.get("planet2", ""))
            t = (a.get("type") or "").lower()
            t = {"conjunct": "conjunction", "opposite": "opposition"}.get(t, t)
            if p1 and p2:
                a1, a2 = sorted((p1, p2))
                idx.aspects.add((a1, t, a2))
        v = chart.get("vedic") or {}
        for p in v.get("planets", []) or []:
            name = canon_planet(p.get("english", "") or p.get("name", ""))
            if name:
                idx.vedic[name] = (canon_sign(p.get("rashi_english", "") or p.get("rashi", "")),
                                   p.get("house"), bool(p.get("retrograde")), p.get("nakshatra"))
                if p.get("nakshatra"):
                    idx.nakshatras.add(p["nakshatra"])
        lg = v.get("lagna") or {}
        idx.lagna = canon_sign(lg.get("rashi_english", "") or lg.get("rashi", "")) if lg else None
        if lg.get("nakshatra"):
            idx.nakshatras.add(lg["nakshatra"])
        mn = v.get("moon_nakshatra") or {}
        if mn.get("name"):
            idx.nakshatras.add(mn["name"])
        d = v.get("dasha") or {}
        idx.maha = canon_planet((d.get("maha_dasha") or {}).get("current", "") or "")
        idx.antar = canon_planet((d.get("antar_dasha") or {}).get("current", "") or "")
        utc = meta.get("utc_datetime") or ""
        if len(utc) >= 4 and utc[:4].isdigit():
            idx.birth_year = int(utc[:4])
        return idx


# ----------------------------------------------------------------------------- derivation

_BASE_WEIGHT = {"Sun": 1.0, "Moon": 1.0, "Saturn": 0.9, "Jupiter": 0.9, "Mars": 0.7, "Venus": 0.7,
                "Mercury": 0.7, "Rahu": 0.8, "Ketu": 0.8, "Uranus": 0.6, "Neptune": 0.6, "Pluto": 0.6}
_PLANET_TOPICS = {"Venus": ("love", "money"), "Mars": ("career", "self"), "Saturn": ("career", "timing"),
                  "Jupiter": ("money", "spiritual"), "Moon": ("self", "health", "family"),
                  "Mercury": ("career",), "Sun": ("self", "career")}
_HOUSE_TOPICS = {1: ("self",), 2: ("money",), 4: ("family",), 5: ("love",), 6: ("health", "career"),
                 7: ("love",), 8: ("money", "spiritual"), 10: ("career",), 11: ("money",), 12: ("spiritual",)}


def derive_factors(chart: dict, *, system: str = "both") -> list[FactorView]:
    """Factor views straight from stored chart_data (fallback when engine factors are absent)."""
    meta = chart.get("metadata", {}) or {}
    approx = bool(meta.get("approximate_time"))
    hs = meta.get("house_system", "placidus")
    out: list[FactorView] = []
    if system in ("western", "both"):
        for p in chart.get("planets", []) or []:
            name = canon_planet(p.get("name", "")) or p.get("name", "")
            sign = p.get("sign")
            if not sign:
                continue
            w = _BASE_WEIGHT.get(name, 0.5)
            retro = ", retrograde" if p.get("retrograde") else ""
            out.append(FactorView(
                id=f"N.{_slug(name)}.SIGN.{_slug(sign)}", kind="natal",
                label=f"Natal {name} in {sign} (tropical){retro}", topics=_PLANET_TOPICS.get(name, ()),
                weight=w, kb_keys=(f"{name.lower()} in {sign.lower()}",)))
            h = p.get("house")
            if h and not approx:
                out.append(FactorView(
                    id=f"N.{_slug(name)}.H{h}", kind="natal",
                    label=f"Natal {name} in the {ordinal(int(h))} house ({hs})",
                    topics=_HOUSE_TOPICS.get(int(h), ()), weight=w * 0.9,
                    kb_keys=(f"{name.lower()} in the {ordinal(int(h))} house",)))
        rs = chart.get("rising_sign") or {}
        if rs.get("sign") and not approx:
            out.append(FactorView(id=f"N.ASC.SIGN.{_slug(rs['sign'])}", kind="natal",
                                  label=f"{rs['sign']} rising (tropical Ascendant)", topics=("self",),
                                  weight=1.0, kb_keys=(f"{rs['sign'].lower()} rising",)))
        for a in chart.get("aspects", []) or []:
            p1, p2, t = a.get("planet1"), a.get("planet2"), (a.get("type") or "")
            if not (p1 and p2 and t):
                continue
            w = (_BASE_WEIGHT.get(p1, 0.5) * _BASE_WEIGHT.get(p2, 0.5))
            orb = a.get("orb")
            orb_s = f" (orb {orb}°)" if orb is not None else ""
            out.append(FactorView(id=f"A.{_slug(p1)}.{_slug(t)}.{_slug(p2)}", kind="aspect",
                                  label=f"Natal {p1} {t} {p2}{orb_s}", weight=w * 0.8,
                                  topics=tuple(set(_PLANET_TOPICS.get(p1, ())) | set(_PLANET_TOPICS.get(p2, ()))),
                                  kb_keys=(f"{p1.lower()} {t} {p2.lower()}",)))
    v = chart.get("vedic") or {}
    if v and system in ("vedic", "both"):
        lg = v.get("lagna") or {}
        if lg.get("rashi") and not approx:
            out.append(FactorView(id=f"VN.LAGNA.{_slug(lg.get('rashi_english') or lg['rashi'])}", kind="natal",
                                  label=f"Lagna {lg['rashi']} ({lg.get('rashi_english', '')}, sidereal)",
                                  topics=("self",), weight=1.0,
                                  kb_keys=(f"{(lg.get('rashi_english') or lg['rashi']).lower()} lagna",)))
        for p in v.get("planets", []) or []:
            eng = p.get("english") or p.get("name", "")
            if not p.get("rashi"):
                continue
            nak = f", {p['nakshatra']} nakshatra" if p.get("nakshatra") else ""
            house = f", house {p['house']} from lagna" if p.get("house") and not approx else ""
            out.append(FactorView(
                id=f"VN.{_slug(eng)}.RASHI.{_slug(p.get('rashi_english') or p['rashi'])}", kind="natal",
                label=f"Sidereal {eng} in {p['rashi']} ({p.get('rashi_english', '')}){nak}{house}",
                topics=_PLANET_TOPICS.get(eng, ()), weight=_BASE_WEIGHT.get(eng, 0.5) * 0.95,
                kb_keys=(f"{eng.lower()} in {(p.get('rashi_english') or p['rashi']).lower()} vedic",)))
        mn = v.get("moon_nakshatra") or {}
        if mn.get("name"):
            out.append(FactorView(id=f"VN.MOON.NAK.{_slug(mn['name'])}", kind="natal",
                                  label=f"Moon nakshatra {mn['name']} (lord {mn.get('lord', '?')})",
                                  topics=("self",), weight=0.95, kb_keys=(f"{mn['name'].lower()} nakshatra",)))
        d = v.get("dasha") or {}
        d_approx = approx or bool(d.get("approximate"))
        for key, prefix, w, word in (("maha_dasha", "V.MD", 1.0, "Mahadasha"), ("antar_dasha", "V.AD", 0.8, "Antardasha")):
            cur = (d.get(key) or {})
            if cur.get("current"):
                win = None if d_approx or not cur.get("start") else (cur["start"], cur["end"])
                out.append(FactorView(id=f"{prefix}.{_slug(cur['current'])}", kind="dasha",
                                      label=f"Current {cur['current']} {word}" + ("" if win else " (dates withheld)"),
                                      topics=("timing",), weight=w, window=win,
                                      kb_keys=(f"{cur['current'].lower()} {word.lower()}",)))
        for y in v.get("yogas", []) or []:
            if y.get("present"):
                out.append(FactorView(id=f"Y.{_slug(y['name'].replace(' Yoga', ''))}", kind="yoga",
                                      label=f"{y['name']} ({y.get('strength', 'present')})", weight=0.6,
                                      kb_keys=(y["name"].lower(),)))
        ss = v.get("sade_sati") or {}
        if ss.get("active"):
            out.append(FactorView(id=f"V.SADESATI.{_slug(ss.get('phase', 'ACTIVE'))}", kind="dosha",
                                  label=f"Sade Sati active ({ss.get('phase')} phase)", topics=("timing",),
                                  weight=0.85, kb_keys=("sade sati",)))
    out.sort(key=lambda f: f.weight, reverse=True)
    return out


def factor_system(fid: str) -> str:
    """Which zodiac system a factor id belongs to: vedic (sidereal) | western (tropical) | both (neutral)."""
    if fid.startswith(("VN.", "V.", "Y.", "D.", "P.", "G.")):
        return "vedic"            # G.* = vedic gochara / graha conjunction-opposition (engine, BUG-018)
    if fid.startswith(("N.", "A.", "W.")):
        return "western"
    if fid.startswith("T.MOON.H"):
        return "vedic"          # gochara of the Moon by house; the western request gets the Sun-sign variant of the same id
    if fid.startswith("T."):
        return "western"        # T.* is western-only since BUG-018; the filter stays as defence in depth
    return "both"


def system_allows(fid: str, system: str) -> bool:
    """One system per answer (D3). vedic: graha/gochara only; western: tropical aspects only; both: everything."""
    if system not in ("vedic", "western"):
        return True
    fs = factor_system(fid)
    if fid.startswith("T.MOON.H"):
        return True
    return fs in ("both", system)


SYSTEM_TAG = {"vedic": "Vedic, sidereal", "western": "Western, tropical"}


TIME_UNKNOWN = FactorView(id="META.TIME_UNKNOWN", kind="natal",
                          label="Birth time unknown: no Ascendant, Lagna, houses or exact dasha dates",
                          weight=1.0)
HOUSE_FACTOR = re.compile(r"\.(H\d{1,2}|ASC|MC|LAGNA)(\.|$)")


def apply_time_unknown(factors: Iterable[FactorView], approximate: bool) -> list[FactorView]:
    """Drop house/angle factors and dasha dates at the source (llm-integration.md §3 [3])."""
    fs = list(factors)
    if not approximate:
        return fs
    kept = []
    for f in fs:
        if HOUSE_FACTOR.search(f.id) and "CHANDRA" not in f.id:
            continue
        if f.kind == "yoga" or f.id.startswith("D.MANGAL"):
            continue  # yogas/doshas are house-based; the engine may still emit them (defence in depth)
        if f.kind == "dasha" and f.window:
            f = FactorView(**{**f.__dict__, "window": None})
        kept.append(f)
    if not any(f.id == TIME_UNKNOWN.id for f in kept):
        kept.insert(0, TIME_UNKNOWN)
    return kept


# ----------------------------------------------------------------------------- rendering


@dataclass(frozen=True)
class ChartFacts:
    display_name: str
    system: str                     # user preference: western | vedic | both
    approximate_time: bool
    house_system: str
    ayanamsa: str
    engine_version: str
    today: str
    summary_lines: tuple[str, ...]
    factors: tuple[FactorView, ...]
    is_minor: bool = False
    kb_aliases: tuple[tuple[str, str], ...] = ()      # (alias "KB1", chunk_id) for the notes in this prompt
    kb_hedge: tuple[str, ...] = ()                    # aliases whose claims must be hedged (low confidence / unverified / schools differ)

    @property
    def factor_ids(self) -> set[str]:
        return {f.id for f in self.factors}

    @property
    def citable_ids(self) -> set[str]:
        """Everything a model may cite: computed factors and the reference notes it was shown."""
        return self.factor_ids | {a for a, _ in self.kb_aliases}

    def label_for(self, fid: str) -> str | None:
        return next((f.label for f in self.factors if f.id == fid), None)

    def _systems_line(self) -> str:
        w = f"Western tropical (houses: {self.house_system})"
        v = f"Vedic sidereal (ayanamsa: {self.ayanamsa})"
        return "Systems: " + {"vedic": v, "western": w}.get(self.system, f"{w}; {v}")

    def _system_rule(self) -> str:
        if self.system == "vedic":
            return ("Use ONLY the Vedic (sidereal) system: graha, rashi, nakshatra, dasha and gochara. Do not mention any other "
                    "zodiac system's placements unless the user asks.")
        if self.system == "western":
            return "Use ONLY the Western (tropical) system. Do not mention any other zodiac system's placements unless the user asks."
        return "Both systems are available: name the system whenever you name a sign, and never blend them in one placement."

    def render(self) -> str:
        lines = [
            "CHART FACTS (authoritative; computed by the Swiss Ephemeris engine)",
            f"Name: {self.display_name}",
            self._systems_line(),
            f"Preferred system: {self.system}",
            self._system_rule(),
            "Birth time known: " + (
                "NO - Moon sign, Moon nakshatra and dasha are approximate (say so); do not mention Ascendant, Lagna, "
                "houses, house-based yogas or exact dasha dates" if self.approximate_time else "yes"),
            f"Today: {self.today}",
        ]
        if self.is_minor:
            lines.append("Chart belongs to a minor: no romance, marriage or relationship predictions.")
        lines.append("Natal summary:")
        lines += [f"- {s}" for s in self.summary_lines]
        lines.append("Factors (cite by the ID in brackets):")
        for f in self.factors:
            win = f", {f.window[0]} to {f.window[1]}" if f.window else ""
            fs_ = factor_system(f.id)
            if fs_ == "both" and f.id.startswith("T.MOON.H") is False:
                tag = ""
            else:
                tag = f" ({SYSTEM_TAG[self.system if self.system in SYSTEM_TAG and f.id.startswith('T.MOON.H') else fs_]})"
            lines.append(f"[{f.id}] {f.label}{tag} (weight {f.weight:.2f}{win})")
        return "\n".join(lines)


def _summary(chart: dict, approx: bool, system: str = "both") -> list[str]:
    out = []
    west = system in ("western", "both")
    ved = system in ("vedic", "both")
    for key, label in (("sun_sign", "Sun"), ("moon_sign", "Moon")) if west else ():
        s = chart.get(key) or {}
        if s.get("sign"):
            amb = " (may be ambiguous: birth time unknown)" if label == "Moon" and (approx or s.get("approximate")) else ""
            out.append(f"{label}: {s['sign']} (tropical){amb}")
    if west and not approx and (chart.get("rising_sign") or {}).get("sign"):
        out.append(f"Ascendant: {chart['rising_sign']['sign']} (tropical)")
    v = (chart.get("vedic") or {}) if ved else {}
    if not approx and (v.get("lagna") or {}).get("rashi"):
        out.append(f"Lagna: {v['lagna']['rashi']} (sidereal)")
    for p in v.get("planets", []) or []:
        e = p.get("english") or p.get("name")
        if e in ("Sun", "Surya") and system == "vedic":
            out.append(f"Sun: {p.get('rashi')} ({p.get('rashi_english')}, sidereal)")
        if e in ("Moon", "Chandra"):
            out.append(f"Moon: {p.get('rashi')} ({p.get('rashi_english')}, sidereal)")
    mn = v.get("moon_nakshatra") or {}
    if mn.get("name"):
        out.append(f"Moon nakshatra: {mn['name']}")
    d = v.get("dasha") or {}
    md, ad = (d.get("maha_dasha") or {}).get("current"), (d.get("antar_dasha") or {}).get("current")
    if md:
        out.append(f"Current dasha: {md} Mahadasha" + (f" / {ad} Antardasha" if ad else ""))
    return out[:10]


def build_chart_facts(
    chart: dict,
    *,
    factors: Iterable[Any] | None = None,
    system: str = "both",
    display_name: str = "the user",
    today: date | None = None,
    k: int = 12,
    is_minor: bool = False,
) -> ChartFacts:
    meta = chart.get("metadata", {}) or {}
    approx = bool(meta.get("approximate_time"))
    fs = [FactorView.coerce(f) for f in factors] if factors is not None else derive_factors(chart)
    if system in ("vedic", "western"):
        fs = [f for f in fs if system_allows(f.id, system)]          # one system per answer: graha-only for vedic
    fs = apply_time_unknown(fs, approx)
    # keep dasha factors always (engine contract), then the top-k by weight
    must = [f for f in fs if f.kind == "dasha" or f.id == TIME_UNKNOWN.id]
    rest = [f for f in fs if f not in must][: max(0, k - len(must))]
    return ChartFacts(
        display_name=display_name[:60] or "the user",
        system=system,
        approximate_time=approx,
        house_system="none (time unknown)" if approx else str(meta.get("house_system", "placidus")),
        ayanamsa=str(meta.get("ayanamsa", "lahiri")),
        engine_version=str(meta.get("engine_version", "unknown")),
        today=(today or date.today()).isoformat(),
        summary_lines=tuple(_summary(chart, approx, system)),
        factors=tuple(must + rest),
        is_minor=is_minor,
    )
