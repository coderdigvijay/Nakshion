from __future__ import annotations

import re

from app.rag.chunking import TARGET_MAX, Chunk, chunk_corpus, chunk_markdown, dedupe, near_duplicates, quality_score
from app.rag.sources import all_stems, source_info

MD = """# The Planets

## Saturn

### Transit Effects
Saturn transits test structure. """ + ("Patience and discipline are rewarded over time. " * 10) + """

## Venus

""" + "\n\n".join(f"Venus paragraph {i}. " + ("Love, beauty and values shape relationships. " * 25) for i in range(6))


def test_ids_are_stable_and_unique_across_runs():
    a = chunk_markdown(MD, "planets.md")
    b = chunk_markdown(MD, "planets.md")
    assert [c.id for c in a] == [c.id for c in b] and len({c.id for c in a}) == len(a)
    edited = chunk_markdown(MD.replace("Patience", "Calm"), "planets.md")
    assert [c.id for c in edited] == [c.id for c in a]
    assert [c.content_sha256 for c in edited] != [c.content_sha256 for c in a]


def test_overlap_size_and_heading_prefix():
    chunks = chunk_markdown(MD, "planets.md")
    venus = [c for c in chunks if "Venus" in c.heading_path]
    assert len(venus) > 1 and all(c.tokens <= TARGET_MAX + 40 for c in venus)
    assert venus[1].content.split("\n\n", 1)[1][:20] in venus[0].content
    assert all(c.content.startswith(c.heading_path) for c in chunks)


def test_every_corpus_file_has_provenance_and_chunks_carry_it(kb_dir):
    stems = {p.stem for p in kb_dir.glob("*.md")}
    assert stems <= set(all_stems()), f"files without a sources.yaml entry: {stems - set(all_stems())}"
    chunks = chunk_corpus(kb_dir)
    for c in chunks[:: max(1, len(chunks) // 40)]:
        assert {"source_title", "tier", "licence", "tradition", "language", "quality"} <= set(c.meta)
        assert c.meta["tier"] in (1, 2, 3)


def test_licence_policy(kb_dir):
    """In-copyright modern authors are never named on chips; only public-domain classics carry an author."""
    for stem in ("books_arroyo_chart_interpretation", "books_greene_saturn", "books_rudhyar_humanistic"):
        s = source_info(stem)
        assert s.licence == "modern_author_paraphrase" and s.review and s.tier == 3
        assert "author" not in s.meta()
        assert not re.search(r"arroyo|greene|rudhyar", s.display_title(), re.I)
    for stem in ("books_ptolemy_tetrabiblos", "books_lilly_christian_astrology"):
        assert source_info(stem).meta()["author"]


def test_everything_is_indexed_famous_examples_as_lowest_tier(kb_dir):
    """Study project: nothing is excluded. Case studies and "Famous Examples" are indexed, tier 3 (lowest weight)."""
    chunks = chunk_corpus(kb_dir)
    assert any("Famous Examples" in c.heading_path for c in chunks)
    fc = [c for c in chunks if c.file == "famous_charts_analysis.md"]
    assert fc and {c.system for c in fc} == {"both"} and {c.meta["tier"] for c in fc} == {3}
    assert {p.name for p in kb_dir.glob("*.md")} == {c.file for c in chunks}      # every file contributes chunks


def test_corpus_size_dedupe_and_quality(kb_dir):
    chunks = chunk_corpus(kb_dir)
    assert 700 < len(chunks) < 900
    assert max(c.tokens for c in chunks) <= TARGET_MAX + 60 and min(c.quality for c in chunks) >= 0.25
    assert near_duplicates(chunks, 0.85) == []


def test_dedupe_drops_lower_authority_copy():
    base = dict(file="x.md", heading_path="X > A", system="both", topics=(), entities=(), content_sha256="", tokens=40)
    text = "Saturn rules discipline structure and patience in the natal chart " * 6
    a = Chunk(id="a#1#0", content="X > A\n\n" + text, meta={"tier": 1}, quality=0.9, **base)
    b = Chunk(id="b#1#0", content="X > A\n\n" + text, meta={"tier": 3}, quality=0.9, **base)
    assert [c.id for c in dedupe([a, b])] == ["a#1#0"]


def test_quality_score_penalises_stubs_and_symbol_soup():
    assert quality_score("Saturn rules discipline. " * 40, 200) > 0.8
    assert quality_score("|---|---|\n|---|---|", 6) < 0.4
    assert quality_score("x", 1) < 0.5
