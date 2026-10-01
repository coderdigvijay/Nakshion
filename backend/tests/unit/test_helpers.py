from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.core.security import create_access_token, decode_access_token, password_policy_error
from app.services import ai, quota_service
from app.services.chat_service import make_title
from app.services.compatibility_service import assemble
from app.services.geocoding_service import normalise


def test_make_title_word_boundary() -> None:
    assert make_title("short question") == "short question"
    t = make_title("Will this coming year be a good one for changing my job to something more creative?")
    assert len(t) <= 60 and not t.endswith(" ") and "creative" not in t


def test_password_policy_bytes_not_chars() -> None:
    assert password_policy_error("a" * 72) is None
    assert password_policy_error("é" * 37).startswith("PASSWORD_TOO_LONG")  # 74 bytes, 37 chars


def test_jwt_roundtrip_and_type() -> None:
    import uuid

    uid = uuid.uuid4()
    assert decode_access_token(create_access_token(uid, 3)) == (uid, 3)
    assert decode_access_token("garbage") is None


def test_quota_window_user_local_midnight() -> None:
    user = SimpleNamespace(timezone="Asia/Kolkata", subscription_tier="free")
    w = quota_service.window(user, quota_service.CHAT_REPLY, datetime(2026, 10, 1, 20, 0, tzinfo=UTC))
    assert w.start.isoformat() == "2026-10-02"  # 01:30 IST next day
    assert w.resets_at == datetime(2026, 10, 2, 18, 30, tzinfo=UTC)
    m = quota_service.window(user, quota_service.COMPAT_REPORT, datetime(2026, 12, 31, 20, 0, tzinfo=UTC))
    assert m.start.isoformat() == "2027-01-01"


def test_geocode_normalise() -> None:
    assert normalise("  ＰＵＮＥ   india ") == "pune india"


def test_assemble_contract_shape_and_clamping() -> None:
    calc = {"overall_score": 11.7, "categories": {"emotional": {"score": 6.25}},
            "synastry_aspects": [{"planet1": "Sun", "planet2": "Moon", "aspect": "trine", "orb": 1.234, "contribution": 0.5}]}
    narrative = {"categories": {}, "aspect_interpretations": ["nice"], "strengths": ["a"], "challenges": []}
    overall, data = assemble(calc, narrative)
    assert overall == 10.0
    assert set(data["categories"]) == {"emotional", "communication", "romance", "passion", "long-term"}
    assert data["categories"]["emotional"]["score"] == 6.2 or data["categories"]["emotional"]["score"] == 6.3
    assert len(data["strengths"]) == 3 and len(data["challenges"]) == 3
    assert data["synastry_aspects"][0] == {"planet1": "Sun", "planet2": "Moon", "aspect": "trine", "orb": 1.23, "interpretation": "nice"}


def test_compat_interpretations_align_by_key() -> None:
    report = {"synastry_aspects": [{"planet1": "Sun", "planet2": "North Node", "aspect": "trine"},
                                   {"planet1": "Venus", "planet2": "Mars", "aspect": "square"}]}
    keys = [ai.aspect_key(a) for a in report["synastry_aspects"]]
    assert keys == ["sun-trine-north_node", "venus-square-mars"]
    out = ai._align_interpretations(report, [{"aspect_key": keys[1], "text": "B"}, {"aspect_key": "zzz", "text": "X"}])
    assert out == ["", "B"]


def test_clean_sources_never_exposes_file_names() -> None:
    out = ai.clean_sources([{"source_id": "x1", "title": "love_relationships.md", "section": "Venus", "tier": None}])
    assert out[0]["title"] and not out[0]["title"].endswith(".md") and "_" not in out[0]["title"]
    assert out[0]["tier"] in (1, 2, 3)


def test_llm_view_forwards_full_ashtakoota_and_breakdown() -> None:
    ak = {"total": 17.5, "kootas": [{"name": "Nadi", "score": 0, "max": 8}], "nadi_dosha": True, "bhakoot_dosha": False,
          "tables_fixture_verified": False}
    view = ai._llm_report_view({"overall_score": 6.0, "categories": {"romance": {"score": 7.0}}, "synastry_aspects": [],
                                "ashtakoota": ak, "manglik": {"person1": None}, "approximate": True,
                                "score_breakdown": {"blend": "x"}, "overall_band": "Harmonious"})
    assert view["ashtakoota"] == ak and view["ashtakoota"]["nadi_dosha"] is True  # doshas reach the narrative
    assert view["kootas"] == ak["kootas"] and view["score_breakdown"] == {"blend": "x"}
    assert view["overall_band"] == "Harmonious" and view["approximate"] is True


def test_personal_chips_one_system_and_labelled() -> None:
    from app.services.personal_reading_service import _system_consistent

    facts = {"key_factors": [{"factor_id": "T.SATURN.CONJ.N.MOON", "label": "tropical"},
                             {"factor_id": "VN.SATURN.RASHI.AQUARIUS", "label": "sidereal"}],
             "factors": [{"id": "T.MARS.SQ.N.SUN"}, {"id": "V.MD.MOON"}]}
    v = _system_consistent(facts, "vedic")
    assert [f["factor_id"] for f in v["key_factors"]] == ["VN.SATURN.RASHI.AQUARIUS"]
    assert [f["id"] for f in v["factors"]] == ["V.MD.MOON"] and all(f["system"] == "vedic" for f in v["key_factors"])
    w = _system_consistent(facts, "western")  # western users keep the tropical transit aspects
    assert len(w["key_factors"]) == 2 and all(f["system"] == "western" for f in w["key_factors"])


def test_template_headline_has_no_raw_dates_or_tokens() -> None:
    facts = {"key_factors": [{"label": "Mercury Mahadasha (2025-07-03 to 2042-07-03)"}]}
    h = ai._personal_template(facts)["headline"]
    assert h == "Mercury period — steady focus today" and not any(ch.isdigit() for ch in h)
    for lang in ("hindi", "hinglish"):
        t = ai._personal_template(facts, lang)
        assert "2025" not in t["headline"] and "Mercury period" in t["headline"] and t["affirmation"] != ai._personal_template(facts)["affirmation"]
    assert ai._personal_template({"key_factors": []}, "english")["headline"] == "A day for steady, mindful progress"
    assert "2026" not in ai._personal_template({"key_factors": [{"label": "Antardasha Moon 2026-01-01"}]})["headline"]


def test_humanize_machine_tokens() -> None:
    assert ai.humanize("The match is below_average with Nadi dosha PRESENT.") == "The match is below average with Nadi dosha present."
    assert ai.humanize("Venus conjunct Mars") == "Venus conjunct Mars"
    cleaned = ai._clean_strings({"summary": "score band: below_average", "strengths": ["Dosha ABSENT"], "n": 3})
    assert cleaned == {"summary": "score band: below average", "strengths": ["Dosha absent"], "n": 3}
