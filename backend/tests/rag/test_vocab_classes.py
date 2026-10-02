"""BUG-027: complete vocabulary classes (every member, not a sample)."""

from __future__ import annotations

import pytest

from app.llm.lexicon import NAKSHATRAS as KB_NAKSHATRAS
from app.rag import vocab
from app.rag.glossary import gloss_terms


def words(q):
    return set(gloss_terms(q))


@pytest.mark.parametrize("eng,spec", list(vocab.SIGNS.items()))
def test_every_sign_spelling_maps_to_the_english_sign(eng, spec):
    for spelling in spec[1]:
        assert eng in words(f"{spelling} ka swabhav"), spelling


def test_all_27_nakshatras_are_covered_in_every_spelling_including_joined_forms():
    assert set(vocab.NAKSHATRAS) == set(KB_NAKSHATRAS) and len(vocab.NAKSHATRAS) == 27
    for eng, (devs, roms) in vocab.NAKSHATRAS.items():
        want = set(eng.lower().split())
        for d in devs:
            assert want <= words(f"{d} नक्षत्र का स्वामी"), (eng, d)
        for r in roms:
            assert want <= words(f"{r} nakshatra ka lord"), (eng, r)


def test_joined_and_spaced_bhadrapada_forms_agree():
    assert words("पूर्वाभाद्रपद") == words("पूर्वा भाद्रपद") >= {"purva", "bhadrapada"}


@pytest.mark.parametrize("n", range(1, 13))
def test_house_ordinals_and_lord_words_1_to_12(n):
    sfx = "st" if n == 1 else "nd" if n == 2 else "rd" if n == 3 else "th"
    for w in vocab.ORDINAL_WORDS[n - 1]:
        assert f"{n}{sfx}" in words(f"{w} bhav me"), w
    for w in vocab.HOUSE_LORDS[n - 1]:
        got = words(f"{w} ka phal")
        assert f"{n}{sfx}" in got and "lord" in got, w


@pytest.mark.parametrize("term", ["kendra", "केंद्र", "trikona", "dusthana", "upachaya", "उपचय"])
def test_house_types_reach_the_house_classification_headings(term):
    assert {"house", "classifications"} <= words(f"what is {term}")


def test_planet_names_and_nicknames():
    for planet, names in vocab.PLANETS.items():
        for n in names:
            assert planet in words(f"{n} ki dasha"), (planet, n)


def test_dasha_and_varga_abbreviations():
    assert {"mahadasha", "antardasha"} <= words("MD AD")
    for k in vocab.ABBREV:
        if k.startswith("d") and k[1:].isdigit() and k != "d1":
            assert "divisional" in words(f"{k} chart"), k
    assert "ascendant" in words("Asc sign")


@pytest.mark.parametrize("q,expect", [("6/8", "shadashtak"), ("2/12", "dwirdwadash"), ("5/9", "navapancham"), ("6-8 bhakoot", "shadashtak"),
                                      ("षडाष्टक", "shadashtak"), ("द्विर्द्वादश", "dwirdwadash"), ("नवपंचम", "navapancham")])
def test_kuta_numerics_and_names(q, expect):
    assert expect in words(q)


def test_kuta_names_and_manglik_spellings():
    for k, v in {"bhakut": "bhakoot", "naadi": "nadi", "vashy": "vashya", "taara": "tara", "योनि": "yoni", "ग्रह मैत्री": "maitri",
                 "varn": "varna", "mangalik": "manglik", "kuja dosh": "kuja", "कुज दोष": "kuja"}.items():
        assert v in words(k), k


def test_panchang_limbs_tithis_and_weekdays():
    assert "tithi" in words("तिथि") and "vara" in words("वार") and "karana" in words("करण")
    for en, names in vocab.TITHIS:
        for n in names:
            assert en in words(n), n
    for en, names in vocab.WEEKDAYS.items():
        for n in names:
            assert en in words(n), n


def test_hand_written_glossary_entries_still_win():
    from app.rag.glossary import GLOSS, norm

    assert GLOSS[norm("राहु काल")] == "rahu kaal rahu kalam"


async def test_phrasebook_and_glossary_chunks_are_down_ranked_unless_a_meaning_is_asked():
    from app.rag.retriever import RetrievalConfig, Retriever
    from app.rag.query import build_plan
    from app.rag.retriever import _TRANSLATE_ASK

    assert RetrievalConfig().lang_penalty > 0
    assert not _TRANSLATE_ASK.search("Saturn in the 10th house") and _TRANSLATE_ASK.search("translate this into Hindi")
    assert build_plan("kendra ka matlab kya hai", "hinglish", [], multilingual=False, cfg=RetrievalConfig()).is_definition
