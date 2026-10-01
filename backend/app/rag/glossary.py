"""Hindi / Hinglish -> English astrology glossary for retrieval.

The knowledge base is English and the default embedding model (bge-small-en) is English-only, so a
Devanagari or Roman-Hindi question must be re-expressed in the KB's vocabulary before it can match
anything. This is NOT machine translation: it maps domain terms (and drops function words) so the
result is a bag of English search terms. Unknown words are dropped, never guessed.

Used for: the FTS term query, the "gloss" query embedding, entity/topic detection, and the
cross-encoder query. Keys are normalised (see `norm`): NFC, nukta removed, lowercase.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from app.llm.lexicon import (
    NAKSHATRAS,
    PLANET_LOOKUP,
    SIGN_LOOKUP,
)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s).replace("़", "")  # drop nukta: ढ़ == ढ
    return unicodedata.normalize("NFC", s).lower()


# phrase or word -> English search terms (space separated)
_RAW: dict[str, str] = {
    # core nouns
    "कुंडली": "birth chart horoscope", "कुण्डली": "birth chart horoscope", "kundli": "birth chart horoscope",
    "kundali": "birth chart horoscope", "janam kundli": "birth chart", "जन्म कुंडली": "birth chart",
    "राशिफल": "horoscope", "rashifal": "horoscope",
    "भाव": "house", "bhava": "house", "bhav": "house", "घर": "house",
    "राशि": "zodiac sign", "rashi": "zodiac sign", "राशिचक्र": "zodiac",
    "नक्षत्र": "nakshatra", "nakshatra": "nakshatra",
    "ग्रह": "planet", "grah": "planet", "graha": "planet",
    "लग्न": "ascendant lagna", "lagna": "ascendant lagna",
    "दशा": "dasha", "dasha": "dasha", "महादशा": "mahadasha dasha", "mahadasha": "mahadasha dasha",
    "अंतर्दशा": "antardasha dasha", "antardasha": "antardasha dasha",
    "विंशोत्तरी": "vimshottari dasha", "vimshottari": "vimshottari dasha",
    "योग": "yoga", "yog": "yoga", "yoga": "yoga",
    "राजयोग": "raja yoga", "राज योग": "raja yoga", "raj yoga": "raja yoga", "rajyog": "raja yoga",
    "raja yoga": "raja yoga", "धनयोग": "dhana yoga", "धन योग": "dhana yoga", "dhan yoga": "dhana yoga",
    "dhanyog": "dhana yoga",
    "दोष": "dosha", "dosh": "dosha", "dosha": "dosha",
    "मांगलिक": "mangal dosha manglik mars", "manglik": "mangal dosha manglik mars",
    "mangalik": "mangal dosha manglik mars", "मंगल दोष": "mangal dosha mars",
    "साढ़ेसाती": "sade sati saturn", "साढ़ेसाती": "sade sati saturn", "साढ़े साती": "sade sati saturn",
    "sade sati": "sade sati saturn", "sadesati": "sade sati saturn", "sadhesati": "sade sati saturn",
    "उपाय": "remedies", "upay": "remedies", "upaye": "remedies", "upaya": "remedies", "upayas": "remedies",
    "मंत्र": "mantra", "mantra": "mantra", "रत्न": "gemstone", "ratna": "gemstone", "रत्नों": "gemstone",
    "दान": "charity donation", "daan": "charity donation", "व्रत": "fasting", "vrat": "fasting",
    "यंत्र": "yantra", "yantra": "yantra", "पूजा": "puja ritual",
    "मिलान": "compatibility matching", "milan": "compatibility matching",
    "kundli milan": "compatibility matching kuta guna", "कुंडली मिलान": "compatibility matching kuta guna",
    "गुण मिलान": "guna milan kuta compatibility", "guna milan": "guna milan kuta compatibility",
    "गुण": "qualities guna", "gun": "qualities",
    "विवाह": "marriage relationship", "shaadi": "marriage relationship", "shadi": "marriage relationship",
    "vivah": "marriage relationship", "शादी": "marriage relationship",
    "प्रेम": "love relationship", "pyaar": "love relationship", "pyar": "love relationship",
    "प्यार": "love relationship", "रिश्ता": "relationship", "rishta": "relationship", "रिश्ते": "relationship",
    "करियर": "career profession", "career": "career profession", "नौकरी": "job career", "naukri": "job career",
    "व्यापार": "business career", "vyapar": "business career", "karobar": "business career",
    "धन": "money wealth finances", "paisa": "money finances", "paise": "money finances",
    "पैसा": "money finances", "पैसे": "money finances",
    "स्वास्थ्य": "health body", "sehat": "health body", "सेहत": "health body", "shareer": "body", "शरीर": "body",
    "अंग": "body parts", "ang": "body parts", "angon": "body parts",
    "वक्री": "retrograde", "vakri": "retrograde", "retrograde": "retrograde",
    "गोचर": "transit", "gochar": "transit", "gochara": "transit",
    "दृष्टि": "aspect drishti", "drishti": "aspect drishti", "एस्पेक्ट": "aspect", "ट्राइन": "trine",
    "स्क्वेयर": "square", "त्रिकोण": "trine", "सेक्स्टाइल": "sextile",
    "नवांश": "navamsa divisional chart", "navamsa": "navamsa divisional chart", "navamsha": "navamsa divisional chart",
    "षड्बल": "shadbala planetary strength", "shadbala": "shadbala planetary strength", "बल": "strength",
    "आत्मकारक": "atmakaraka jaimini karaka", "atmakaraka": "atmakaraka jaimini karaka",
    "जैमिनी": "jaimini", "jaimini": "jaimini", "कारक": "karaka significator",
    "सायन": "tropical zodiac", "sayan": "tropical zodiac", "निरयन": "sidereal zodiac",
    "nirayan": "sidereal zodiac", "तुलना": "difference comparison", "अंतर": "difference comparison",
    "difference": "difference comparison",
    "वापसी": "return", "wapsi": "return", "वापस": "return",
    "कला": "phase", "कलाओं": "phases", "कलाएं": "phases", "kala": "phase", "phases": "phases",
    "चंद्र कला": "moon phases", "दैनिक": "daily", "रोज़": "daily", "roz": "daily", "रोज": "daily",
    "सावधानी": "caution handle", "dhyan": "caution handle", "सावधानियां": "caution",
    "प्रभाव": "effects influence", "asar": "effects influence", "असर": "effects influence",
    "स्वभाव": "nature personality traits", "swabhav": "nature personality", "nature": "nature personality",
    "व्यक्तित्व": "personality", "vyaktitva": "personality",
    "भावनात्मक": "emotional", "emotional": "emotional", "भावनाओं": "emotions", "भावनात्मक स्वभाव": "emotional nature",
    "प्रतीक": "represent significance", "dikhate": "represent signify", "दर्शाते": "represent signify",
    "दर्शाता": "represent signify", "batata": "represent signify", "batate": "represent signify",
    "सातवां": "seventh", "सातवें": "seventh", "सातवाँ": "seventh", "पहला": "first", "पहले": "first",
    "दूसरा": "second", "दूसरे": "second", "तीसरा": "third", "तीसरे": "third", "चौथा": "fourth", "चौथे": "fourth",
    "पांचवां": "fifth", "पांचवें": "fifth", "छठा": "sixth", "छठे": "sixth", "आठवां": "eighth", "आठवें": "eighth",
    "नौवां": "ninth", "नौवें": "ninth", "दसवां": "tenth", "दसवें": "tenth", "ग्यारहवां": "eleventh",
    "ग्यारहवें": "eleventh", "बारहवां": "twelfth", "बारहवें": "twelfth",
    "7th": "seventh", "1st": "first", "2nd": "second", "3rd": "third", "4th": "fourth", "5th": "fifth",
    "6th": "sixth", "8th": "eighth", "9th": "ninth", "10th": "tenth", "11th": "eleventh", "12th": "twelfth",
    "चंद्रमा की कलाओं": "moon phases", "बुध वक्री": "mercury retrograde", "शनि वापसी": "saturn return",
    "सैटर्न रिटर्न": "saturn return", "saturn return": "saturn return",
    "कमज़ोर": "weak afflicted", "kamzor": "weak afflicted", "weak": "weak afflicted",
    "कष्टकारी": "troublesome afflicted", "समय": "period timing", "avadhi": "period", "अवधि": "period timing",
    "वैदिक": "vedic", "jyotish": "astrology", "ज्योतिष": "astrology", "astrology": "astrology",
    "ग्रहण": "eclipse", "grahan": "eclipse", "होरा": "hours planetary hour", "hora": "hours planetary hour",
    "वार्षिक": "annual yearly", "varshik": "annual yearly", "मध्य आकाश": "midheaven", "मध्यआकाश": "midheaven",
    "अंतर्दृशा": "antardasha dasha", "अन्तर्दशा": "antardasha dasha", "महादृशा": "mahadasha dasha",
    "प्रत्यंतर्दशा": "pratyantardasha dasha", "विंशोतरी": "vimshottari dasha", "नक्षेत्र": "nakshatra",
    "राहु काल": "rahu kaal rahu kalam", "राहुकाल": "rahu kaal rahu kalam", "rahu kaal": "rahu kaal rahu kalam",
    "rahukaal": "rahu kaal rahu kalam", "rahu kalam": "rahu kaal rahu kalam", "rahukalam": "rahu kaal rahu kalam",
    "कालसर्प": "kaal sarp dosha", "kalsarp": "kaal sarp dosha", "kaalsarp": "kaal sarp dosha",
    "मूलत्रिकोण": "moolatrikona", "mooltrikona": "moolatrikona", "मुहूर्त": "muhurta", "muhurat": "muhurta",
    "तिथि": "tithi lunar day", "tithi": "tithi lunar day", "पंचांग": "panchang", "panchang": "panchang",
    "स्वामी": "lord", "अधिपति": "lord", "भावेश": "house lord", "अर्थ": "meaning", "मतलब": "meaning",
    "matlab": "meaning", "meaning": "meaning",
    "सूर्य": "sun", "चंद्रमा": "moon", "चंद्र": "moon", "सोम": "moon",
}

_STOP_EN = set("""a an the of in on at to for from by with and or but is are was were be been being am do does did
what whats which who whom when where why how my me i you your our we they them it its this that these those about
tell please should would could can will shall may might must also than then so such into over under between among
mean means meaning kya hai hain ho hota hoti hote ka ki ke ko se mein me par aur ya nahi na kaise kab kaun kaun-se
kaunse kitne kitna kis kisi kuch jab toh to bhi hi hum aap mera meri mere iska iske iski uska main yeh woh ye wo
karein karna kare karta karte sakte sakta sakti chal rahi raha rahe jaate jata jati hona hoga hogi batao bataiye
batayein baare liye lie lekin""".split())
_STOP_HI = set("""क्या है हैं और के का की को में से पर यह वह ये वो कैसे कब कौन कौन-से कितने कितना किस कुछ तो भी ही हम आप मेरा
मेरी मेरे इसका इसके इसकी उसका मैं करें करना करता करते सकते सकता चल रही रहा रहे जाते जाता होता होती होते हो होना
होगा बताइए बताएं बारे लिए लेकिन या न नहीं तथा द्वारा अपने अपना अपनी वाले वाला वाली जैसे बीच""".split())
_STOP = {norm(w) for w in _STOP_EN | _STOP_HI}

GLOSS: dict[str, str] = {norm(k): v for k, v in _RAW.items()}
_PHRASES = sorted((k for k in GLOSS if " " in k), key=len, reverse=True)

# Devanagari nakshatra names (+ common spellings) -> canonical English name
_NAK_HI = {
    "अश्विनी": "Ashwini", "भरणी": "Bharani", "कृत्तिका": "Krittika", "कृतिका": "Krittika", "रोहिणी": "Rohini",
    "मृगशिरा": "Mrigashira", "आर्द्रा": "Ardra", "पुनर्वसु": "Punarvasu", "पुष्य": "Pushya", "आश्लेषा": "Ashlesha",
    "मघा": "Magha", "पूर्वा फाल्गुनी": "Purva Phalguni", "उत्तरा फाल्गुनी": "Uttara Phalguni", "हस्त": "Hasta",
    "चित्रा": "Chitra", "स्वाति": "Swati", "विशाखा": "Vishakha", "अनुराधा": "Anuradha", "ज्येष्ठा": "Jyeshtha",
    "मूल": "Mula", "पूर्वाषाढ़ा": "Purva Ashadha", "उत्तराषाढ़ा": "Uttara Ashadha", "श्रवण": "Shravana",
    "धनिष्ठा": "Dhanishta", "शतभिषा": "Shatabhisha", "पूर्वा भाद्रपद": "Purva Bhadrapada",
    "उत्तरा भाद्रपद": "Uttara Bhadrapada", "रेवती": "Revati",
}
NAK_HI = {norm(k): v for k, v in _NAK_HI.items()}
NAK_ROMAN = {n.lower(): n for n in NAKSHATRAS}
NAK_ROMAN.update({"krittika": "Krittika", "kritika": "Krittika", "ashvini": "Ashwini", "mrigshira": "Mrigashira",
                  "jyestha": "Jyeshtha", "shatabisha": "Shatabhisha", "shravan": "Shravana"})

_DEV_TOK = re.compile(r"[\u0900-\u097F]+")
_TOKEN = re.compile(r"[ऀ-ॿ]+|[A-Za-z0-9']+")
_HI_SUFFIX = ("ों", "ें", "ओं", "ाओं", "ाएं", "ाएँ", "ियों", "ियां", "ियाँ", "ों")


def _lookup(tok: str) -> str | None:
    if tok in GLOSS:
        return GLOSS[tok]
    for suf in _HI_SUFFIX:
        if tok.endswith(suf) and tok[: -len(suf)] in GLOSS:
            return GLOSS[tok[: -len(suf)]]
    for suf in ("on", "en", "ein", "iyan", "s"):                 # Roman plurals: bhavon, grahon, dashas
        if len(tok) > len(suf) + 3 and tok.endswith(suf) and tok[: -len(suf)] in GLOSS:
            return GLOSS[tok[: -len(suf)]]
    return None


_FILE_GLOSS_DONE = False
_FILE = Path(__file__).resolve().parents[2] / "knowledge_base" / "kb_lang_glossary_hi_en.md"


def _english_words(gloss: str) -> str:
    g = re.sub(r"\([^)]*\)", " ", gloss)                      # drop parentheticals: 'Vedic astrology ("science of light")'
    return " ".join(w for w in re.findall(r"[a-z]{3,}", g.lower()) if w not in _STOP)[:120]


def _ensure_file_gloss() -> None:
    """Fold kb_lang_glossary_hi_en.md (Devanagari | Roman spellings | English gloss) into GLOSS, so every term the
    knowledge base itself teaches is understood by the query planner. Hand-written entries win; a bad row is skipped."""
    global _FILE_GLOSS_DONE, _PHRASES
    if _FILE_GLOSS_DONE:
        return
    _FILE_GLOSS_DONE = True
    try:
        lines = _FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in ("Devanagari",):
            continue
        eng = " ".join(_english_words(cells[2]).split()[:6])
        romans = [norm(x.strip()) for x in cells[1].split(",") if x.strip()]
        if not eng:
            continue
        value = " ".join(dict.fromkeys((eng + " " + " ".join(r for r in romans if " " not in r and r.isascii())).split()))
        keys = [x.strip() for x in re.split(r"[/]", cells[0])] + [x.strip() for x in cells[1].split(",")]
        for k in keys:
            nk = norm(k)
            if re.search(r"\d", nk) or " " in nk or not (1 < len(nk) <= 40):     # single tokens only: phrases stay hand-written
                continue
            if nk not in GLOSS and nk not in _STOP:
                GLOSS[nk] = value
    _PHRASES = sorted((k for k in GLOSS if " " in k), key=len, reverse=True)


def gloss_terms(text: str, *, phonetic: bool = True) -> list[str]:
    """English search terms for a question in English / Hindi / Hinglish. Order-preserving, de-duplicated."""
    _ensure_file_gloss()
    t = norm(text)
    out: list[str] = []
    for tokn in re.findall(r"\b\d{1,2}(?:st|nd|rd|th)\b", t):          # keep "7th" next to "seventh": headings use both
        out.append(tokn)
    for ph in _PHRASES:  # multi-word phrases first, then blank them out
        if ph in t:
            out.extend(GLOSS[ph].split())
            t = t.replace(ph, " ")
    for nk, canon in sorted(NAK_HI.items(), key=lambda kv: len(kv[0]), reverse=True):
        if nk in t and len(nk) > 2:
            out.append(canon.lower())
            t = t.replace(nk, " ")
    for tok in _TOKEN.findall(t):
        if tok in _STOP or len(tok) < 2:
            continue
        g = _lookup(tok)
        if g:
            out.extend(g.split())
            continue
        if tok in NAK_ROMAN:
            out.append(NAK_ROMAN[tok].lower())
            continue
        planet = PLANET_LOOKUP.get(tok)
        if planet:
            out.append(planet.lower())
            continue
        sign = SIGN_LOOKUP.get(tok)
        if sign:
            out.append(sign.lower())
            continue
        if re.fullmatch(r"[a-z0-9']+", tok):  # untouched English word
            out.append(tok.strip("'"))
        elif phonetic and _DEV_TOK.fullmatch(tok):  # unknown Devanagari word: sound-alike KB term
            from app.rag.phonetic import match_all

            out.extend(match_all(tok))
    seen: set[str] = set()
    return [w for w in out if w and not (w in seen or seen.add(w))]
