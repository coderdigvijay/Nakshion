from __future__ import annotations

import pytest

from app.rag.glossary import gloss_terms
from app.rag.phonetic import match, skeleton, translit


@pytest.mark.parametrize("q,expect", [
    ("साढ़ेसाती क्या है और यह कितने समय तक रहती है?", {"sade", "sati", "saturn"}),
    ("Rohini nakshatra ke gun aur nature ke baare mein batao", {"rohini", "nakshatra"}),
    ("मांगलिक दोष क्या है", {"dosha", "manglik"}),
    ("Weak Saturn ke liye kaun se upay bataye jaate hain?", {"saturn", "remedies", "weak"}),
    ("कुंडली मिलान कैसे देखा जाता है", {"compatibility", "kuta", "guna"}),
    ("What does the 7th house represent?", {"seventh", "house"}),
])
def test_glossary_maps_hindi_hinglish_to_kb_vocabulary(q, expect):
    assert expect <= set(gloss_terms(q))


def test_stopwords_and_unknown_words_are_dropped_not_guessed():
    assert gloss_terms("आप कैसे हैं") == []
    assert "kaise" not in gloss_terms("kaise kaam karta hai")


def test_plural_suffix_stripped():
    assert "eclipse" in gloss_terms("ग्रहणों का असर")


@pytest.mark.parametrize("hindi,english", [("काइरॉन", "chiron"), ("स्टेलियम", "stellium"), ("अष्टकवर्ग", "ashtakavarga"),
                                           ("अर्गला", "argala"), ("यूरेनस", "uranus")])
def test_phonetic_bridge_matches_loanwords(hindi, english):
    from app.rag.phonetic import match_all

    assert english in match_all(hindi)


def test_phonetic_bridge_is_conservative():
    assert match("मतलब") is None and match("प्रणाली") is None
    assert len(skeleton(translit("कुंडली"))) >= 3
