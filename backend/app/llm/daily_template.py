"""Template for the personal daily reading, used when the LLM is slow or unavailable (BUG-025).

It is built ONLY from the engine's `personal_day` facts (area scores, dasha context, key factors, Moon transit), in the
user's language, so a "Simplified reading" still says something about THIS day: which area flows, which asks for
patience, which period the user is in. No model call, no invented placements, no gendered verb forms in Hindi.

    template_daily_personal(facts, language) -> {headline, overview, areas{love,career,wellness,money:{text}}, affirmation}
"""

from __future__ import annotations

import re
from typing import Any

from app.llm.facts import ordinal

AREAS = ("love", "career", "wellness", "money")

PLANETS = {
    "english": {},
    "hindi": {"Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु", "Venus": "शुक्र",
              "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"},
    "hinglish": {"Sun": "Surya", "Moon": "Chandra", "Mars": "Mangal", "Mercury": "Budh", "Jupiter": "Guru", "Venus": "Shukra",
                 "Saturn": "Shani", "Rahu": "Rahu", "Ketu": "Ketu"},
}
AREA_NAME = {
    "english": {"love": "love", "career": "career", "wellness": "wellbeing", "money": "money"},
    "hindi": {"love": "प्रेम", "career": "करियर", "wellness": "सेहत", "money": "धन"},
    "hinglish": {"love": "pyaar", "career": "career", "wellness": "sehat", "money": "paisa"},
}

# band: hi (4-5) / mid (3) / lo (1-2). Hindi uses imperatives and impersonal forms only (no gendered verbs).
TEXT = {
    "english": {
        "love": {"hi": "Warm, honest conversation lands well today. Say what you appreciate in someone and let it be simple.",
                 "mid": "Keep plans simple and listen first; small gestures of attention matter more than big words today.",
                 "lo": "A day to go gently in relationships. Postpone heavy talks and keep your words kind and unhurried."},
        "career": {"hi": "A good day to move one important task forward. Start with what you have been putting off.",
                   "mid": "Choose one priority and finish it well. Steady focus beats spreading yourself thin.",
                   "lo": "Be patient with work today: review, tidy and prepare rather than launching something new."},
        "wellness": {"hi": "Energy is supportive. A walk, stretching or a favourite routine will feel good.",
                     "mid": "Keep a steady routine today: regular meals, water and enough sleep go a long way.",
                     "lo": "Rest is the priority today. Keep the pace slow and give yourself some quiet time."},
        "money": {"hi": "Your head is clear for planning today. A calm look at your budget and goals is time well spent.",
                  "mid": "Keep spending routine and unhurried; there is no need for any big decision today.",
                  "lo": "A day to review rather than commit. Look over your plans without rushing into anything."},
    },
    "hinglish": {
        "love": {"hi": "Aaj dil se, saaf baat karna achha rahega. Jo achha lagta hai, saral shabdon mein keh dein.",
                 "mid": "Plans simple rakhein aur pehle sunein; chhote-chhote pal bade shabdon se zyada kaam aate hain.",
                 "lo": "Rishton mein aaj narmi se chalna achha rahega. Bhaari baatein taal dein aur shabd pyaar se chunein."},
        "career": {"hi": "Aaj ek zaroori kaam ko aage badhane ka achha din hai. Jo taal rakha tha, wahin se shuru karein.",
                   "mid": "Ek priority chunein aur use achhe se poora karein. Steady focus bikhre kaam se behtar hai.",
                   "lo": "Kaam mein aaj sabr rakhein: nayi shuruaat ke bajaye review, tidy-up aur taiyari par dhyan dein."},
        "wellness": {"hi": "Energy saath de rahi hai. Walk, stretching ya apna pasandida routine achha lagega.",
                     "mid": "Aaj routine steady rakhein: samay par khana, paani aur poori neend bahut kaam aate hain.",
                     "lo": "Aaj aaram sabse zaroori hai. Raftaar dheemi rakhein aur thoda shaant samay khud ko dein."},
        "money": {"hi": "Aaj planning ke liye mann saaf hai. Budget aur goals par shaanti se nazar daalna achha rahega.",
                  "mid": "Kharch routine aur bina jaldi ke rakhein; aaj koi bada faisla zaroori nahi hai.",
                  "lo": "Aaj commit karne se zyada review ka din hai. Plans ko bina jaldbaazi ke dekhein."},
    },
    "hindi": {
        "love": {"hi": "आज दिल से, साफ़ बात करना अच्छा रहेगा। जो अच्छा लगता है, सरल शब्दों में कह दीजिए।",
                 "mid": "योजनाएँ सरल रखिए और पहले सुनिए; छोटे-छोटे पल बड़े शब्दों से ज़्यादा काम आते हैं।",
                 "lo": "रिश्तों में आज नरमी से चलना अच्छा रहेगा। भारी बातें टाल दीजिए और शब्द प्यार से चुनिए।"},
        "career": {"hi": "आज एक ज़रूरी काम को आगे बढ़ाने का अच्छा दिन है। जो टाल रखा था, वहीं से शुरू कीजिए।",
                   "mid": "एक प्राथमिकता चुनिए और उसे अच्छे से पूरा कीजिए। स्थिर ध्यान बिखरे काम से बेहतर है।",
                   "lo": "काम में आज धैर्य रखिए: नई शुरुआत की जगह समीक्षा, व्यवस्था और तैयारी पर ध्यान दीजिए।"},
        "wellness": {"hi": "ऊर्जा साथ दे रही है। टहलना, स्ट्रेचिंग या अपनी पसंद की दिनचर्या अच्छी लगेगी।",
                     "mid": "आज दिनचर्या स्थिर रखिए: समय पर भोजन, पानी और पूरी नींद बहुत काम आते हैं।",
                     "lo": "आज आराम सबसे ज़रूरी है। गति धीमी रखिए और थोड़ा शांत समय अपने लिए निकालिए।"},
        "money": {"hi": "आज योजना बनाने के लिए मन साफ़ है। बजट और लक्ष्यों पर शांति से नज़र डालना अच्छा रहेगा।",
                  "mid": "खर्च सामान्य और बिना जल्दबाज़ी के रखिए; आज कोई बड़ा निर्णय ज़रूरी नहीं है।",
                  "lo": "आज प्रतिबद्ध होने से ज़्यादा समीक्षा का दिन है। योजनाओं को बिना जल्दबाज़ी के देखिए।"},
    },
}
AFFIRMATION = {
    "english": "I move through today with patience and clarity.",
    "hinglish": "Aaj ka din dhairya aur spashtata ke saath beete.",
    "hindi": "आज का दिन धैर्य और स्पष्टता के साथ बीते।",
}
_ISO = re.compile(r"\s*\(?\s*\d{4}-\d{2}-\d{2}(?:\s*(?:to|-|–|—)\s*\d{4}-\d{2}-\d{2})?\s*\)?")


def _band(score: Any) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "mid"
    return "hi" if s >= 4 else "lo" if s <= 2 else "mid"


def _score(facts: dict, area: str) -> float | None:
    try:
        return float(((facts.get("areas") or {}).get(area) or {}).get("score"))
    except (TypeError, ValueError):
        return None


def _name(planet: str, language: str) -> str:
    return PLANETS.get(language, {}).get(planet, planet)


def _clean(label: str) -> str:
    t = _ISO.sub("", str(label))
    t = re.sub(r"\((?:Vedic|Western)[^)]*\)|\(weight[^)]*\)|\(gochara\)|\(sidereal[^)]*\)|\(tropical[^)]*\)", "", t, flags=re.I)
    return re.sub(r"\s{2,}", " ", t).strip(" ,;:-")


def template_daily_personal(facts: dict[str, Any], language: str = "english") -> dict[str, Any]:
    lang = language if language in TEXT else "english"
    dc = facts.get("dasha_context") or {}
    md, ad = str(dc.get("maha") or ""), str(dc.get("antar") or "")
    scores = {a: _score(facts, a) for a in AREAS}
    known = {a: s for a, s in scores.items() if s is not None}
    best = max(known, key=lambda a: known[a]) if known else None
    gentlest = min(known, key=lambda a: known[a]) if known else None
    nm = AREA_NAME[lang]
    pair = f"{_name(md, lang)}–{_name(ad, lang)}" if md and ad else (_name(md, lang) if md else "")
    up = best if best and known[best] >= 4 else None            # a clear high: "flows"
    low = gentlest if gentlest and known[gentlest] <= 2 else None   # a clear low: "asks for patience"
    if up and low and up == low:
        low = None

    # Headline: the period plus what stands out today. Under 90 characters in every language.
    if up and low:
        tail = {"english": f"{nm[up]} flows, {nm[low]} asks for patience", "hinglish": f"{nm[up]} aage, {nm[low]} mein sabr",
                "hindi": f"{nm[up]} में गति, {nm[low]} में धैर्य"}[lang]
    elif up:
        tail = {"english": f"{nm[up]} flows easily", "hinglish": f"{nm[up]} mein achha flow", "hindi": f"{nm[up]} में अच्छा प्रवाह"}[lang]
    elif low:
        tail = {"english": f"go gently with {nm[low]}", "hinglish": f"{nm[low]} mein narmi se", "hindi": f"{nm[low]} में नरमी से चलिए"}[lang]
    else:
        tail = {"english": "a steady, even day", "hinglish": "aaj ka din sthir hai", "hindi": "आज का दिन स्थिर है"}[lang]
    if pair:
        head = {"english": f"{pair} period: {tail}", "hinglish": f"{pair} dasha: {tail}", "hindi": f"{pair} दशा: {tail}"}[lang]
    elif up or low:
        head = {"english": f"Today: {tail}", "hinglish": f"Aaj: {tail}", "hindi": f"आज: {tail}"}[lang]
    else:
        head = {"english": "A day for steady, mindful progress", "hinglish": "Aaj ka din sthir aur sachet pragati ka hai",
                "hindi": "आज का दिन स्थिर और सजग प्रगति का है"}[lang]

    # Overview: the period, the Moon's transit house when known, and the two extremes of the day.
    parts: list[str] = []
    if pair:
        parts.append({"english": f"You are in a {_name(md, lang)} Mahadasha with a {_name(ad, lang)} Antardasha, which sets the background for today.",
                      "hinglish": f"Aap abhi {_name(md, lang)} mahadasha mein {_name(ad, lang)} antardasha mein hain; yeh aaj ki prishthbhoomi banata hai.",
                      "hindi": f"अभी {_name(md, lang)} महादशा में {_name(ad, lang)} अंतर्दशा चल रही है, जो आज की पृष्ठभूमि बनाती है।"}[lang]
                     if ad else
                     {"english": f"You are in a {_name(md, lang)} Mahadasha, which sets the background for today.",
                      "hinglish": f"Aap abhi {_name(md, lang)} mahadasha mein hain; yeh aaj ki prishthbhoomi banata hai.",
                      "hindi": f"अभी {_name(md, lang)} महादशा चल रही है, जो आज की पृष्ठभूमि बनाती है।"}[lang])
    mt = facts.get("moon_transit") or {}
    try:
        h = int(mt.get("house") or 0)
    except (TypeError, ValueError):
        h = 0
    base = str(mt.get("from") or "")
    if 1 <= h <= 12 and lang == "english":
        parts.append(f"The transiting Moon is in the {ordinal(h)} house from your {base or 'natal Moon'}.")
    elif 1 <= h <= 12 and "Moon" in base:
        parts.append(f"Aaj Chandra aapke janm-Chandra se {h}ve bhav mein gochar kar raha hai." if lang == "hinglish"
                     else f"आज चंद्र आपके जन्म-चंद्र से {h}वें भाव में गोचर कर रहा है।")
    if up or low:
        bits = []
        if up:
            bits.append({"english": f"{nm[up].capitalize()} has the easiest flow today ({known[up]:.0f} of 5)",
                         "hinglish": f"Aaj {nm[up]} mein sabse achha flow hai ({known[up]:.0f}/5)",
                         "hindi": f"आज {nm[up]} में सबसे अच्छा प्रवाह है ({known[up]:.0f}/5)"}[lang])
        if low:
            bits.append({"english": f"{nm[low]} asks for more patience ({known[low]:.0f} of 5)",
                         "hinglish": f"{nm[low]} mein thoda sabr zaroori hai ({known[low]:.0f}/5)",
                         "hindi": f"{nm[low]} में थोड़ा धैर्य ज़रूरी है ({known[low]:.0f}/5)"}[lang])
        joiner = {"english": ", while ", "hinglish": ", jabki ", "hindi": ", जबकि "}[lang]
        end = "।" if lang == "hindi" else "."
        line = joiner.join(bits) + end
        parts.append(line[:1].upper() + line[1:])
    else:
        parts.append({"english": "The day is fairly even: take things one step at a time and notice where your energy flows most easily.",
                      "hinglish": "Din kaafi sama hai: ek-ek kadam chalein aur dekhein ki energy kahan sabse aasani se behti hai.",
                      "hindi": "दिन काफ़ी सम है: एक-एक कदम चलिए और देखिए कि ऊर्जा कहाँ सबसे आसानी से बहती है।"}[lang])
    overview = " ".join(p for p in parts if p)

    return {
        "headline": head[:90],
        "overview": overview,
        "areas": {a: {"text": TEXT[lang][a][_band(scores[a])]} for a in AREAS},
        "affirmation": AFFIRMATION[lang],
    }
