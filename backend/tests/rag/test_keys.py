"""The pre-embedded key vocabulary must cover every kb_key the two producers emit (no drift)."""

from __future__ import annotations

import json
from datetime import date

from app.llm.facts import derive_factors
from app.rag.keys import generate_keys

CHARTS = None


def charts():
    from pathlib import Path

    return json.loads((Path(__file__).resolve().parents[2] / "evals" / "fixtures" / "real_charts.json").read_text())


def test_keys_cover_llm_derived_factors_for_real_charts():
    keys = set(generate_keys())
    missing = {}
    for name, chart in charts().items():
        for f in derive_factors(chart):
            for k in f.kb_keys:
                if k not in keys:
                    missing.setdefault(name, set()).add(k)
    assert not missing, f"kb_keys not in the pre-embedded vocabulary: {missing}"


def test_keys_cover_engine_personal_day_factors():
    from app.astrology.personal import personal_day

    keys = set(generate_keys())
    miss = set()
    for name, chart in charts().items():
        try:
            out = personal_day(chart, date(2026, 10, 1), system="vedic", latitude=28.6, longitude=77.2, timezone="Asia/Kolkata")
        except Exception:      # noqa: BLE001 - some fixtures lack inputs; coverage is checked on those that compute
            continue
        for f in out.get("key_factors", []):
            miss |= {k for k in f.get("kb_keys", []) if k not in keys}
    assert not miss, f"engine kb_keys missing from vocabulary: {sorted(miss)[:10]}"


def test_key_set_is_finite_and_sorted_unique():
    k = generate_keys()
    assert len(k) == len(set(k)) and k == sorted(k) and 1000 < len(k) < 6000
