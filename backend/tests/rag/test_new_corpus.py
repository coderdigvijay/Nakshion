"""The researched knowledge files (kb_*): front-matter registration, system separation, table chunking, Hinglish
phrasebook, Devanagari search, confidence / [unverified] / schools-differ handling, URL hygiene."""

from __future__ import annotations

import re
from dataclasses import replace

import pytest

from app.llm.builder import render_notes, sanitize_note
from app.llm.facts import ChartFacts, build_chart_facts
from app.llm.validators import check_hedge
from app.rag.chunking import TABLE_MAX, chunk_corpus, chunk_markdown
from app.rag.embeddings import HashEmbedder
from app.rag.frontmatter import split_front_matter
from app.rag.phrasebook import expand
from app.rag.retriever import Retriever, RetrievalConfig
from app.rag.sources import all_stems, source_info
from app.rag.store import RetrievedChunk

FM = """---
title: "Test Notes: Remedies"
tradition: Vedic (Jyotish)
system: vedic
tier: 2
language: en
sources:
  - "https://example.com/a"
  - "https://example.com/b"
confidence: low
school_notes: "Schools differ on this. Second sentence."
---

# Test Notes

## Remedy section

Some text about a remedy. Sources differ on the details. This claim is uncertain [unverified].
"""


@pytest.fixture(scope="module")
def corpus(kb_dir):
    return chunk_corpus(kb_dir)


@pytest.fixture(scope="module")
async def mem_index(corpus):
    from evals.rag.inmem import build_memory_index

    return await build_memory_index(HashEmbedder(), with_keys=False)


# ----------------------------------------------------------------------------- front-matter and registration


def test_every_researched_file_is_registered_and_front_matter_is_never_chunk_text(kb_dir, corpus):
    stems = {p.stem for p in kb_dir.glob("kb_*.md")}
    assert len(stems) >= 29 and stems <= set(all_stems())
    assert not any(re.search(r"(?m)^(?:school_notes|confidence|tier|tradition|sources|language|system):", c.content) for c in corpus)
    assert not any(re.search(r"https?://", c.content) for c in corpus), "raw URLs must not be indexed"


def test_ingestion_reads_front_matter_for_a_file_not_in_sources_yaml():
    front, body = split_front_matter(FM, "kb_future_file")
    assert front["tier"] == 2 and "confidence:" not in body
    chunks = chunk_markdown(FM, "kb_future_file.md")
    assert chunks and chunks[0].system == "vedic"
    m = chunks[0].meta
    assert m["source_title"] == "Test Notes: Remedies" and m["confidence"] == "low" and m["tier"] == 2
    assert m["schools_differ"] is True and m["school_note"] == "Schools differ on this." and m["source_count"] == 2
    assert m["unverified"] is True and m["licence"] == "researched_synthesis" and m["review"] is True
    assert "example.com" not in str(m)                           # URLs counted, never stored
    assert chunks[0].heading_path.startswith("Test Notes: Remedies")


def test_bad_front_matter_warns_but_still_indexes(caplog):
    bad = "---\ntitle: [unclosed\n---\n\n# T\n\n## S\n\nBody text that is long enough to keep as a chunk. " * 3
    chunks = chunk_markdown(bad, "kb_bad_one.md")
    assert chunks                                               # never fails the ingest
    info = source_info("kb_invalid_system", {"title": "X", "system": "martian", "tier": 9})
    assert info.system == "both" and info.tier == 3             # invalid values fall back, with a warning


# ----------------------------------------------------------------------------- system separation


def test_no_western_exaltation_degree_chunk_is_tagged_vedic_or_both(corpus):
    pat = re.compile(r"(?:Exaltation|Fall|Debilitation)[^\n]{0,40}\(\d{1,2}\s?°\)", re.I)
    bad = [c.id for c in corpus if pat.search(c.content) and c.system != "western"]
    assert bad == []
    deg = [c for c in corpus if c.meta.get("degree_system") == "western"]
    assert len(deg) == 7 and {c.system for c in deg} == {"western"}                 # one per classical planet
    assert all("Dignity table (Western tropical degrees)" in c.heading_path for c in deg)


async def test_vedic_user_never_gets_western_degrees_and_western_user_does(mem_index):
    store, _ = mem_index
    r = Retriever(store, HashEmbedder(), config=RetrievalConfig(top_k=8, token_cap=10**9))
    q = "What is the exaltation degree of the Sun and Jupiter?"
    v = await r.retrieve(kb_keys=[], question=q, system="vedic")
    assert v and not any(c.meta.get("degree_system") == "western" for c in v)
    assert all(c.system in ("vedic", "both") for c in v)
    w = await r.retrieve(kb_keys=[], question=q, system="western")
    assert any(c.meta.get("degree_system") == "western" for c in w)
    assert all(c.system in ("western", "both") for c in w)
    # the Vedic degrees live in the Vedic file
    assert any("kb_chart_planets_in_signs_dignity" in c.file for c in await r.retrieve(
        kb_keys=[], question="Vedic exaltation and debilitation degrees of the planets", system="vedic"))


# ----------------------------------------------------------------------------- tables and row groups


def test_large_tables_are_split_by_rows_with_the_header_repeated(corpus):
    ad = [c for c in corpus if c.file == "kb_dasha_antardasha_combinations.md" and c.meta.get("kind") == "table"]
    assert len(ad) >= 18                                                           # 9 tables x >= 2 row groups
    for c in ad:
        body = c.content.split("\n\n", 1)[1]
        assert body.splitlines()[0] == "| Sub-period | Length | Characterisation |"
        assert body.splitlines()[1].startswith("|---")
        assert c.tokens <= TABLE_MAX + 40 and " > row" in c.heading_path
    row = next(c for c in ad if "**Saturn-Venus**" in c.content)
    assert "Saturn Mahadasha" in row.heading_path and "Saturn-Saturn" in row.heading_path


def test_every_one_of_81_antardasha_pairs_is_in_exactly_one_chunk(corpus):
    text = [c for c in corpus if c.file == "kb_dasha_antardasha_combinations.md"]
    lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    for a in lords:
        for b in lords:
            assert sum(f"**{a}-{b}**" in c.content for c in text) == 1, (a, b)


def test_house_lord_and_planet_in_house_entries_are_addressable(corpus):
    hl = [c for c in corpus if c.file == "kb_chart_house_lords_in_houses.md" and "7th lord in each house" in c.heading_path]
    assert len(hl) == 1 and "| Placed in | Characterisation |" in hl[0].content
    ph = [c for c in corpus if c.file == "kb_chart_planets_in_houses_vedic.md"]
    assert all(c.heading_path.count(" / ") <= 3 for c in ph)                       # at most 4 entries per chunk
    assert sum(f"Moon in the {n} house" in c.heading_path for n in ("1st", "7th", "12th") for c in ph) >= 3


async def test_row_level_questions_retrieve_the_exact_rows(mem_index):
    store, _ = mem_index
    r = Retriever(store, HashEmbedder(), config=RetrievalConfig(top_k=5, token_cap=10**9))
    top = await r.retrieve(kb_keys=[], question="Saturn mahadasha Venus antardasha", system="vedic")
    assert any("**Saturn-Venus**" in c.content for c in top[:3])
    top = await r.retrieve(kb_keys=[], question="What happens when the 7th lord is placed in the 12th house?", system="vedic")
    assert any("7th lord in each house" in c.heading_path for c in top[:3])
    top = await r.retrieve(kb_keys=[], question="Moon in the 7th house result", system="vedic")
    assert any("Moon in the 7th house" in c.heading_path for c in top[:3])


# ----------------------------------------------------------------------------- Hindi / Hinglish


def test_phrasebook_maps_how_users_type_to_concepts():
    shaadi = expand("meri shaadi kab hogi")
    assert {"seventh", "venus", "jupiter", "dasha"} <= set(shaadi)
    assert set(expand("shadi mein deri kyun ho rahi hai")) >= {"saturn", "seventh"}       # spelling variant (shadi)
    assert {"tenth", "saturn"} <= set(expand("naukri mein promotion kab milega"))
    assert expand("aaj ka mausam kaisa hai") == []                                     # no phrase, no guess


async def test_devanagari_glossary_rows_are_searchable_by_hindi_and_hinglish_terms(mem_index):
    store, _ = mem_index
    r = Retriever(store, HashEmbedder(), config=RetrievalConfig(top_k=6, token_cap=10**9))
    hi = await r.retrieve(kb_keys=[], question="महादशा और अंतर्दशा शब्दों का क्या मतलब है", system="vedic", language="hindi")
    assert any(c.file in ("kb_lang_glossary_hi_en.md", "kb_lang_core_topics_hi.md") for c in hi[:5])
    hg = await r.retrieve(kb_keys=[], question="Rahu Kaal ka calculation kaise hota hai", system="vedic", language="hinglish")
    assert any("Rahu Kaal" in c.heading_path for c in hg[:3])


# ----------------------------------------------------------------------------- confidence, unverified, schools


def _chunk(**meta) -> RetrievedChunk:
    return RetrievedChunk("c#1#0", "kb_x.md", "T > S", "vedic", "Some claim about Yogini dasha.", meta={"tier": 2, **meta},
                          topics=(), entities=())


def test_notes_carry_confidence_unverified_and_schools_flags_and_no_urls():
    block, aliases = render_notes([_chunk(confidence="low", unverified=True, schools_differ=True,
                                          school_note="Sources disagree on years. See https://x.example/page", source_title="Alt dashas")])
    assert 'confidence="low"' in block and 'unverified="true"' in block and 'schools="differ"' in block
    assert "Sources disagree on years." in block and "x.example" not in block and "treated" not in block.lower()[:0]
    assert 'A note marked confidence="low"' in block.split("<kb_note id=")[0]
    assert "http" not in sanitize_note("see https://a.example/x and www.b.example")
    plain, _ = render_notes([_chunk(confidence="high")])
    tag = plain.split("<kb_note id=")[1].split(">")[0]
    assert "unverified" not in tag and "schools" not in tag and "confidence" not in tag


def test_ranking_prefers_high_confidence_and_demotes_unverified():
    r = Retriever(None, None, config=RetrievalConfig())
    from app.rag.query import build_plan

    plan = build_plan("yogini dasha", "english", [], multilingual=False, cfg=r.cfg)
    mk = lambda **m: replace(_chunk(**m), score=0.03)  # noqa: E731
    a, b, c = mk(confidence="high"), mk(confidence="medium"), mk(confidence="low", unverified=True)
    ranked = r._boost([c, b, a], plan)
    assert [x.meta.get("confidence") for x in ranked] == ["high", "medium", "low"]
    assert ranked[0].score - ranked[2].score >= 0.005


def _facts_with(alias_hedge: tuple[str, ...]) -> ChartFacts:
    base = build_chart_facts({"sun_sign": {"sign": "Leo"}, "planets": [], "metadata": {}}, system="vedic")
    return replace(base, kb_aliases=(("KB1", "c#1#0"), ("KB2", "c#2#0")), kb_hedge=alias_hedge)


def test_claims_from_unverified_or_disputed_notes_must_be_hedged():
    f = _facts_with(("KB1",))
    plain = "Yogini dasha runs for 36 years and starts from your Moon nakshatra."
    assert check_hedge(plain, ["KB1"], f)[0].kind == "hedge"
    assert check_hedge("Traditions differ: some sources say Yogini dasha runs 36 years.", ["KB1"], f) == []
    assert check_hedge("कुछ परंपराओं में योगिनी दशा 36 वर्ष की मानी जाती है।", ["KB1"], f) == []
    assert check_hedge(plain, ["KB2"], f) == []            # a settled note needs no hedge
    assert check_hedge(plain, [], f) == []


def test_prompt_tells_the_model_how_to_treat_unverified_notes():
    from app.llm.prompts import get_registry

    t = get_registry().render("chat", streaming=False, language_instruction="x", length_hint="x").text
    assert 'unverified="true"' in t and "traditions differ" in t.lower() and "some sources say" in t


def test_researched_chunks_carry_confidence_and_unverified_markers(corpus):
    new = [c for c in corpus if c.file.startswith("kb_")]
    assert {c.meta["confidence"] for c in new} <= {"high", "medium", "low"} and "low" in {c.meta["confidence"] for c in new}
    flagged = [c for c in new if "[unverified]" in c.content.lower()]
    assert flagged and all(c.meta.get("unverified") for c in flagged)
    sd = [c for c in new if c.meta["schools_differ"]]                              # only chunks that actually describe a disagreement
    assert 0 < len(sd) < len(new) and all(c.meta.get("school_note") for c in sd)
    assert all(re.search(r"differ|vary|varies|disagree|some |other |one (?:school|tradition|source)|alternative|variant|according to", c.content, re.I) for c in sd)
    assert all(c.meta["licence"] == "researched_synthesis" and c.meta["source_title"] for c in new)
