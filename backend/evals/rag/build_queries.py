"""Build the labelled retrieval eval set: evals/rag/queries.jsonl.

    python -m evals.rag.build_queries

Two families, both deterministic:

1. CHART-DERIVED (real engine output). For each real chart in evals/fixtures/real_charts.json
   (computed by app.astrology, never hand-written) a question is generated from the chart's
   OWN computed placement (Moon nakshatra, Sun sign, Mahadasha lord, Saturn's house, a natal
   aspect), so the query text and the gold label both follow from engine facts.
2. FREE-FORM topical questions (houses, nakshatras, dashas, yogas, transits, remedies,
   compatibility, career, love, health, daily guidance, ...). Each intent is written in English,
   Hindi (Devanagari) and Hinglish with the same gold.

Gold is expressed as matchers on (file stem, heading_path regex or content regex, grade), not
as chunk ids, so it survives re-chunking; matchers are resolved against the current chunking
at eval time and this builder refuses to emit a query whose gold resolves to nothing.
grade 2 = directly answers the question, grade 1 = relevant supporting material.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
KB = HERE.parents[1] / "knowledge_base"

# ---------------------------------------------------------------------------- free-form intents
# (id, topic, system, {en, hi, hg}, gold)
G = lambda f, h=None, g=2, c=None: {"file": f, "h": h, "c": c, "g": g}  # noqa: E731

INTENTS = [
    ("houses-7th", "houses", "both",
     {"en": "What does the 7th house represent in a birth chart?",
      "hi": "जन्म कुंडली में सातवां भाव किस बात का प्रतीक है?",
      "hg": "Birth chart mein 7th house kya represent karta hai?"},
     [G("houses", r"Seventh House"), G("indian_bphs", r"Bhava", 1)]),
    ("nakshatra-rohini", "nakshatras", "vedic",
     {"en": "Tell me about the Rohini nakshatra and its qualities.",
      "hi": "रोहिणी नक्षत्र के गुण और स्वभाव के बारे में बताइए।",
      "hg": "Rohini nakshatra ke gun aur nature ke baare mein batao."},
     [G("nakshatras_deep_dive", r"\d+\.\s*Rohini"), G("vedic_astrology", r"Rohini", 1)]),
    ("dasha-vimshottari", "dashas", "vedic",
     {"en": "How does the Vimshottari dasha system work?",
      "hi": "विंशोत्तरी दशा प्रणाली कैसे काम करती है?",
      "hg": "Vimshottari dasha system kaise kaam karta hai?"},
     [G("indian_bphs", r"Dasha Systems"), G("vedic_astrology", r"Dasha Systems")]),
    ("yogas-raja-dhana", "yogas", "vedic",
     {"en": "What are Raja Yoga and Dhana Yoga in Vedic astrology?",
      "hi": "वैदिक ज्योतिष में राजयोग और धनयोग क्या होते हैं?",
      "hg": "Vedic astrology mein Raj yoga aur Dhan yoga kya hote hain?"},
     [G("vedic_astrology", r"Important Yogas"), G("indian_bphs", r"Yoga Formations", 1)]),
    ("sade-sati", "transits", "vedic",
     {"en": "What is Sade Sati and how long does it last?",
      "hi": "साढ़ेसाती क्या है और यह कितने समय तक रहती है?",
      "hg": "Sade sati kya hai aur kitne time tak rehti hai?"},
     [G("vedic_astrology", r"Sade Sati"), G("timing_transits", r"Saturn Return", 1)]),
    ("remedies-saturn", "remedies", "vedic",
     {"en": "What remedies are traditionally suggested for a weak or troublesome Saturn?",
      "hi": "कमज़ोर या कष्टकारी शनि के लिए कौन से उपाय बताए जाते हैं?",
      "hg": "Weak Saturn ke liye traditionally kaun se upay bataye jaate hain?"},
     [G("remedial_astrology", r"Mantra|Charity|Fasting|Gemstone"), G("vedic_astrology", r"Remedies", 1),
      G("indian_bphs", r"Remedial Measures", 1)]),
    ("compat-kundli-milan", "compatibility", "vedic",
     {"en": "How do astrologers judge compatibility between two people's charts?",
      "hi": "दो लोगों की कुंडली का मिलान कैसे देखा जाता है?",
      "hg": "Do logon ki kundli milan kaise dekhte hain?"},
     [G("compatibility_synastry_advanced", r"Seven Pillars|Overview"), G("nakshatras_deep_dive", r"Kuta", 2),
      G("love_relationships", r"Synastry", 1)]),
    ("career-factors", "career", "both",
     {"en": "Which chart factors indicate career strengths and direction?",
      "hi": "करियर की दिशा और ताकत के लिए कुंडली में कौन से ग्रह और भाव देखे जाते हैं?",
      "hg": "Career ki direction ke liye chart mein kaun se planets aur houses dekhte hain?"},
     [G("career_astrology", r"Midheaven|10th House|Planets in the 10th"), G("career_astrology", r"Jupiter and Saturn", 1)]),
    ("love-venus", "love", "both",
     {"en": "What does Venus say about how I love and what I need in a relationship?",
      "hi": "शुक्र मेरे प्रेम करने के तरीके और रिश्ते की ज़रूरतों के बारे में क्या बताता है?",
      "hg": "Venus mere love style aur relationship needs ke baare mein kya batata hai?"},
     [G("love_relationships", r"Venus"), G("planets", r"Venus", 1)]),
    ("health-body-parts", "health", "both",
     {"en": "Which parts of the body are linked with each zodiac sign?",
      "hi": "हर राशि का शरीर के किस अंग से संबंध माना जाता है?",
      "hg": "Har zodiac sign ka body ke kaun se part se relation hota hai?"},
     [G("health_astrology", r"Body Parts Ruled"), G("health_astrology", r"Planets and Health", 1)]),
    ("daily-moon-phases", "daily", "both",
     {"en": "How should I use the Moon phases in my daily life?",
      "hi": "चंद्रमा की कलाओं का अपने दैनिक जीवन में कैसे उपयोग करूं?",
      "hg": "Moon phases ko apni daily life mein kaise use karein?"},
     [G("daily_guidance", r"Moon Phase")]),
    ("mercury-retro", "transits", "both",
     {"en": "What does Mercury retrograde actually mean and how should I handle it?",
      "hi": "बुध वक्री का वास्तव में क्या मतलब है और इसमें क्या सावधानी रखें?",
      "hg": "Mercury retrograde ka actual matlab kya hai aur kya dhyan rakhein?"},
     [G("daily_guidance", r"Mercury Retrograde"), G("timing_transits", r"Mercury Retrograde"),
      G("planets", r"Mercury >.*Retrograde", 1)]),
    ("mangal-dosha", "yogas", "vedic",
     {"en": "What is Mangal Dosha and does it ruin marriage?",
      "hi": "मांगलिक दोष क्या है और क्या इससे विवाह में बाधा आती है?",
      "hg": "Manglik dosha kya hota hai aur kya isse shaadi mein problem aati hai?"},
     [G("vedic_astrology", r"Mangal Dosha")]),
    ("rahu-ketu", "planets", "vedic",
     {"en": "What do Rahu and Ketu represent in a chart?",
      "hi": "कुंडली में राहु और केतु क्या दर्शाते हैं?",
      "hg": "Chart mein Rahu aur Ketu kya represent karte hain?"},
     [G("vedic_astrology", r"Rahu and Ketu"), G("planets", r"North Node|South Node", 1)]),
    ("sidereal-vs-tropical", "systems", "both",
     {"en": "What is the difference between the sidereal and tropical zodiac?",
      "hi": "सायन और निरयन राशिचक्र में क्या अंतर है?",
      "hg": "Sayan aur nirayan zodiac mein kya difference hai?"},
     [G("vedic_astrology", r"Sidereal vs"), G("vedic_astrology", r"Key Differences", 1)]),
    ("aspects-trine-square", "aspects", "western",
     {"en": "What do trine and square aspects mean between planets?",
      "hi": "ग्रहों के बीच ट्राइन और स्क्वेयर एस्पेक्ट का क्या मतलब होता है?",
      "hg": "Planets ke beech trine aur square aspect ka kya matlab hota hai?"},
     [G("aspects", r"Square|Trine")]),
    ("navamsa-d9", "vargas", "vedic",
     {"en": "What is the Navamsa chart and what is it used for?",
      "hi": "नवांश कुंडली क्या है और इसका क्या उपयोग होता है?",
      "hg": "Navamsa chart kya hota hai aur kis kaam aata hai?"},
     [G("vedic_astrology", r"Navamsa"), G("indian_bphs", r"Divisional Charts")]),
    ("saturn-return", "transits", "western",
     {"en": "What happens during the first Saturn return?",
      "hi": "पहली शनि वापसी (सैटर्न रिटर्न) के दौरान क्या होता है?",
      "hg": "First Saturn return ke time kya hota hai?"},
     [G("timing_transits", r"Saturn Return"), G("books_greene_saturn", None, 1, r"Saturn [Rr]eturn")]),
    ("shadbala", "strength", "vedic",
     {"en": "What is Shadbala and how is planetary strength measured?",
      "hi": "षड्बल क्या होता है और ग्रहों की शक्ति कैसे मापी जाती है?",
      "hg": "Shadbala kya hota hai aur planets ki strength kaise measure hoti hai?"},
     [G("indian_bphs", r"Shadbala")]),
    ("jaimini-atmakaraka", "jaimini", "vedic",
     {"en": "What is the Atmakaraka in Jaimini astrology?",
      "hi": "जैमिनी ज्योतिष में आत्मकारक क्या होता है?",
      "hg": "Jaimini astrology mein Atmakaraka kya hota hai?"},
     [G("indian_jaimini_sutras", r"Atmakaraka"), G("indian_jaimini_sutras", r"Chara Karakas", 1)]),
]


# HOLD-OUT intents: written AFTER the query-planning glossary was frozen and never used to tune it. Reported
# separately (split="holdout") so the headline number is not inflated by vocabulary tuned to the dev queries.
HOLDOUT = [
    ("h-mars-retro", "transits", "both",
     {"en": "What does Mars retrograde mean for my energy and drive?",
      "hi": "मंगल वक्री होने पर ऊर्जा और काम करने की क्षमता पर क्या असर पड़ता है?",
      "hg": "Mars retrograde hone par meri energy aur drive par kya asar padta hai?"},
     [G("timing_transits", r"Mars Retrograde"), G("planets", r"Mars >.*Retrograde", 1)]),
    ("h-gem-jupiter", "remedies", "vedic",
     {"en": "Which gemstone is recommended for Jupiter and how is it worn?",
      "hi": "गुरु ग्रह के लिए कौन सा रत्न पहनना चाहिए?",
      "hg": "Guru ke liye kaun sa ratna pehnna chahiye?"},
     [G("remedial_astrology", r"Gemstone"), G("indian_bphs", r"Remedial Measures", 1), G("vedic_astrology", r"Remedies", 1)]),
    ("h-voc-moon", "daily", "western",
     {"en": "What is a void of course Moon and when should I avoid starting things?",
      "hi": "वॉइड ऑफ कोर्स चंद्रमा क्या होता है और उस समय कौन से काम नहीं करने चाहिए?",
      "hg": "Void of course Moon kya hota hai aur us time kaun se kaam nahi karne chahiye?"},
     [G("daily_guidance", r"Void of Course"), G("timing_transits", r"Void of Course")]),
    ("h-solar-return", "timing", "western",
     {"en": "What is a solar return chart and how is it read?",
      "hi": "सोलर रिटर्न चार्ट क्या होता है और इसे कैसे पढ़ा जाता है?",
      "hg": "Solar return chart kya hota hai aur kaise padhte hain?"},
     [G("timing_transits", r"Solar and Lunar Returns"), G("predictive_techniques_advanced", r"Return Charts")]),
    ("h-profections", "timing", "western",
     {"en": "How do annual profections work?",
      "hi": "वार्षिक प्रोफेक्शन कैसे काम करते हैं?",
      "hg": "Annual profections kaise kaam karte hain?"},
     [G("predictive_techniques_advanced", r"Annual Profections"), G("modern_techniques", r"Profections")]),
    ("h-eclipses", "transits", "western",
     {"en": "How do eclipses affect my birth chart?",
      "hi": "ग्रहण का मेरी जन्म कुंडली पर क्या प्रभाव पड़ता है?",
      "hg": "Grahan ka meri janam kundli par kya asar padta hai?"},
     [G("timing_transits", r"Eclipse"), G("predictive_techniques_advanced", r"Eclipse")]),
    ("h-chiron", "planets", "western",
     {"en": "What does Chiron represent in a natal chart?",
      "hi": "जन्म कुंडली में काइरॉन क्या दर्शाता है?",
      "hg": "Janam kundli mein Chiron kya dikhata hai?"},
     [G("planets", r"Chiron")]),
    ("h-pancha-mahapurusha", "yogas", "vedic",
     {"en": "What are the Pancha Mahapurusha yogas?",
      "hi": "पंच महापुरुष योग क्या होते हैं?",
      "hg": "Panch Mahapurush yog kya hote hain?"},
     [G("indian_bphs", r"Yoga Formations")]),
    ("h-argala", "jaimini", "vedic",
     {"en": "What is Argala in Jaimini astrology?",
      "hi": "जैमिनी ज्योतिष में अर्गला का क्या मतलब है?",
      "hg": "Jaimini mein Argala ka kya matlab hota hai?"},
     [G("indian_jaimini_sutras", r"Argala")]),
    ("h-ashtakavarga", "strength", "vedic",
     {"en": "How does the Ashtakavarga system work?",
      "hi": "अष्टकवर्ग प्रणाली कैसे काम करती है?",
      "hg": "Ashtakavarga system kaise kaam karta hai?"},
     [G("indian_bphs", r"Ashtakavarga")]),
    ("h-midheaven", "career", "western",
     {"en": "What does my Midheaven say about my public image and career?",
      "hi": "मेरा मध्य आकाश मेरी सार्वजनिक छवि और करियर के बारे में क्या बताता है?",
      "hg": "Mera Midheaven meri public image aur career ke baare mein kya batata hai?"},
     [G("career_astrology", r"Midheaven")]),
    ("h-element-compat", "compatibility", "western",
     {"en": "How compatible are fire and air signs in love?",
      "hi": "अग्नि और वायु तत्व की राशियां प्रेम में कितनी अनुकूल होती हैं?",
      "hg": "Fire aur air signs love mein kitne compatible hote hain?"},
     [G("love_relationships", r"Compatibility by Element"), G("compatibility_synastry_advanced", r"Seven Pillars", 1)]),
    ("h-health-houses", "health", "both",
     {"en": "Which house and planets point to health problems in a chart?",
      "hi": "कुंडली में स्वास्थ्य संबंधी परेशानियां किस भाव और ग्रह से देखी जाती हैं?",
      "hg": "Chart mein health problems kaun se house aur planet se dekhte hain?"},
     [G("health_astrology", r"6th House"), G("health_astrology", r"Planets and Health", 1)]),
    ("h-stellium", "aspects", "western",
     {"en": "What is a stellium and how does it show up in a chart?",
      "hi": "स्टेलियम क्या होता है और कुंडली में कैसे दिखता है?",
      "hg": "Stellium kya hota hai aur chart mein kaise dikhta hai?"},
     [G("aspects", r"Stellium")]),
    ("h-uranus-opposition", "transits", "western",
     {"en": "What is the Uranus opposition at midlife?",
      "hi": "मध्य आयु में यूरेनस ऑपोज़िशन क्या होता है?",
      "hg": "Midlife mein Uranus opposition kya hota hai?"},
     [G("timing_transits", r"Uranus Opposition"), G("books_arroyo_chart_interpretation", r"Cycles of Transformation", 1)]),
    ("h-planetary-hours", "daily", "western",
     {"en": "How do planetary hours help me choose the right time for activities?",
      "hi": "ग्रह होरा से किसी काम का सही समय कैसे चुनें?",
      "hg": "Planetary hours se kaam ka sahi time kaise choose karein?"},
     [G("daily_guidance", r"Planetary Hours|Best Days for Activities")]),
    ("h-jupiter-return", "transits", "western",
     {"en": "What happens at a Jupiter return every twelve years?",
      "hi": "हर बारह साल में गुरु वापसी पर क्या होता है?",
      "hg": "Har 12 saal mein Jupiter return par kya hota hai?"},
     [G("timing_transits", r"Jupiter Return")]),
    ("h-dasha-results", "dashas", "vedic",
     {"en": "How do I interpret the results of a dasha period?",
      "hi": "दशा के फल की व्याख्या कैसे करें?",
      "hg": "Dasha ke results ko kaise interpret karein?"},
     [G("indian_bphs", r"Interpreting Dasha Results")]),
    ("h-venus-retro", "transits", "both",
     {"en": "What does Venus retrograde do to relationships?",
      "hi": "शुक्र वक्री का रिश्तों पर क्या प्रभाव पड़ता है?",
      "hg": "Venus retrograde ka relationships par kya asar padta hai?"},
     [G("timing_transits", r"Venus Retrograde"), G("planets", r"Venus >.*Retrograde", 1)]),
    ("h-moon-dignity", "planets", "both",
     {"en": "In which signs is the Moon exalted and debilitated?",
      "hi": "चंद्रमा किस राशि में उच्च और किस राशि में नीच का होता है?",
      "hg": "Moon kis rashi mein exalted aur debilitated hota hai?"},
     [G("planets", r"The Moon")]),
]

# HOLD-OUT 2: written after the glossary + phonetic bridge were frozen (post holdout-1 fixes). The only set
# that is blind to every tuning step; report it as the generalisation estimate.
HOLDOUT2 = [
    ("g-yod", "aspects", "western",
     {"en": "What is the Yod or Finger of God aspect pattern?",
      "hi": "योड यानी फिंगर ऑफ गॉड एस्पेक्ट पैटर्न क्या होता है?",
      "hg": "Yod yaani Finger of God aspect pattern kya hota hai?"},
     [G("aspects", r"Yod")]),
    ("g-hellenistic", "techniques", "western",
     {"en": "What are the key Hellenistic concepts like sect and lots?",
      "hi": "हेलेनिस्टिक ज्योतिष में सेक्ट और लॉट्स की अवधारणाएं क्या हैं?",
      "hg": "Hellenistic astrology mein sect aur lots ke concepts kya hain?"},
     [G("modern_techniques", r"Hellenistic")]),
    ("g-bach-crystals", "remedies", "western",
     {"en": "How do Bach flower essences and crystals work as remedies?",
      "hi": "बाख फ्लावर एसेंस और क्रिस्टल उपाय के रूप में कैसे काम करते हैं?",
      "hg": "Bach flower essences aur crystals remedy ke roop mein kaise kaam karte hain?"},
     [G("remedial_astrology", r"Western Remedial")]),
    ("g-capricorn-careers", "career", "western",
     {"en": "Which careers suit someone with the Sun in Capricorn?",
      "hi": "मकर राशि में सूर्य वाले लोगों के लिए कौन से करियर उपयुक्त होते हैं?",
      "hg": "Capricorn Sun sign walon ke liye kaun se career suit karte hain?"},
     [G("career_astrology", r"Best Careers by Sun Sign > Capricorn")]),
    ("g-karakamsha", "jaimini", "vedic",
     {"en": "What is the Karakamsha in Jaimini astrology?",
      "hi": "कारकांश क्या होता है?",
      "hg": "Karakamsha kya hota hai?"},
     [G("indian_jaimini_sutras", r"Karakamsha")]),
    ("g-neptune-transit", "transits", "western",
     {"en": "How should I interpret Neptune transits?",
      "hi": "नेपच्यून गोचर के प्रभाव को कैसे समझें?",
      "hg": "Neptune transit ke effects ko kaise samjhein?"},
     [G("timing_transits", r"Neptune Transit")]),
    ("g-mars-sexual", "love", "western",
     {"en": "How is Mars and sexual energy read in a chart?",
      "hi": "कुंडली में मंगल और यौन ऊर्जा को कैसे पढ़ा जाता है?",
      "hg": "Chart mein Mars aur sexual energy ko kaise padhte hain?"},
     [G("love_relationships", r"Mars")]),
    ("g-empty-8th", "houses", "both",
     {"en": "What does an empty eighth house mean?",
      "hi": "खाली आठवें भाव का क्या मतलब होता है?",
      "hg": "Khaali eighth house ka kya matlab hota hai?"},
     [G("houses", r"Eighth House > Empty")]),
    ("g-fasting", "remedies", "vedic",
     {"en": "What are the traditional fasting practices for the planets?",
      "hi": "ग्रहों के लिए उपवास की पारंपरिक विधियां क्या हैं?",
      "hg": "Planets ke liye traditional fasting practices kya hain?"},
     [G("remedial_astrology", r"Fasting")]),
    ("g-avasthas", "strength", "vedic",
     {"en": "What are the Baladi avasthas, the age states of planets?",
      "hi": "ग्रहों की बाल्यादि अवस्थाएं क्या होती हैं?",
      "hg": "Planets ki Baladi avasthas kya hoti hain?"},
     [G("indian_bphs", r"Avasthas")]),
    ("g-pluto-houses", "transits", "western",
     {"en": "What does Pluto transiting through the houses mean?",
      "hi": "प्लूटो का अलग-अलग भावों में गोचर क्या दर्शाता है?",
      "hg": "Pluto ka alag alag houses mein transit kya dikhata hai?"},
     [G("timing_transits", r"Pluto Transit")]),
    ("g-color-therapy", "remedies", "vedic",
     {"en": "How do I use color therapy with planetary colors?",
      "hi": "ग्रहों के रंगों से कलर थेरेपी कैसे करें?",
      "hg": "Planetary colors se color therapy kaise karein?"},
     [G("remedial_astrology", r"Color Therapy")]),
]

# ---------------------------------------------------------------------------- chart-derived

NAK_Q = {
    "en": "What does my Moon in {n} nakshatra mean for my emotional nature?",
    "hi": "मेरा चंद्रमा {n} नक्षत्र में है, इसका मेरे भावनात्मक स्वभाव पर क्या असर होता है?",
    "hg": "Mera Moon {n} nakshatra mein hai, iska mere emotional nature par kya asar hota hai?",
}
SUN_Q = {
    "en": "What are the core traits of someone with the Sun in {s}?",
    "hi": "{s} राशि में सूर्य वाले व्यक्ति के मुख्य गुण क्या होते हैं?",
    "hg": "{s} mein Sun hone par insaan ke main traits kya hote hain?",
}
DASHA_Q = {
    "en": "I am running the {d} Mahadasha. What should I expect from this period?",
    "hi": "मेरी {d} महादशा चल रही है, इस अवधि से क्या उम्मीद रखनी चाहिए?",
    "hg": "Meri {d} Mahadasha chal rahi hai, is period se kya expect karna chahiye?",
}
HOUSE_Q = {
    "en": "What does Saturn in the {h} house mean?",
    "hi": "शनि का {h} भाव में होना क्या दर्शाता है?",
    "hg": "Saturn ka {h} house mein hona kya batata hai?",
}
ASPECT_Q = {
    "en": "What does {a} between {p1} and {p2} mean in a chart?",
    "hi": "कुंडली में {p1} और {p2} के बीच {a} का क्या अर्थ है?",
    "hg": "Chart mein {p1} aur {p2} ke beech {a} ka kya matlab hai?",
}
ORD = {1: "1st", 2: "2nd", 3: "3rd"}
ORDW = {1: "First", 2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth", 6: "Sixth", 7: "Seventh", 8: "Eighth",
        9: "Ninth", 10: "Tenth", 11: "Eleventh", 12: "Twelfth"}
HI_ORD = {1: "पहले", 2: "दूसरे", 3: "तीसरे", 4: "चौथे", 5: "पांचवें", 6: "छठे", 7: "सातवें", 8: "आठवें",
          9: "नौवें", 10: "दसवें", 11: "ग्यारहवें", 12: "बारहवें"}
ASPECT_FILE = {"conjunction": r"Conjunction", "sextile": r"Sextile", "square": r"Square", "trine": r"Trine",
               "opposition": r"Opposition"}
LANGS = ["en", "hi", "hg"]
VEDIC_CHARTS = {"delhi_1994", "mumbai_1988", "chennai_1992_notime", "kolkata_1969", "bengaluru_2003"}


def _ord(n: int) -> str:
    return ORD.get(n, f"{n}th")


def chart_queries(charts: dict) -> list[dict]:
    out: list[dict] = []
    for ci, (name, c) in enumerate(charts.items()):
        approx = bool(c["metadata"].get("approximate_time"))
        vedic = name in VEDIC_CHARTS
        sysname = "vedic" if vedic else "western"
        v = c["vedic"]

        def add(kind: str, lang: str, text: str, gold: list[dict], topic: str, system: str) -> None:
            out.append({"id": f"{name}:{kind}:{lang}", "source": "chart", "split": "dev", "chart": name, "lang": lang, "text": text,
                        "topic": topic, "system": system, "gold": gold})

        # 1. Moon nakshatra (Vedic, always available even with unknown time)
        nak = v["moon_nakshatra"]["name"]
        add("moon-nak", LANGS[ci % 3], NAK_Q[LANGS[ci % 3]].format(n=nak),
            [G("nakshatras_deep_dive", rf"\d+\.\s*{nak}"), G("vedic_astrology", rf"{nak}", 1)], "nakshatras", "vedic")
        # 2. Sun sign (tropical)
        sun = c["sun_sign"]["sign"]
        lg = LANGS[(ci + 1) % 3]
        add("sun-sign", lg, SUN_Q[lg].format(s=sun),
            [G("zodiac_signs", rf"{sun} \("), G("planets", r"The Sun", 1)], "self", sysname)
        # 3. Mahadasha lord
        d = v["dasha"]["maha_dasha"]["current"]
        lg = LANGS[(ci + 2) % 3]
        add("dasha", lg, DASHA_Q[lg].format(d=d),
            [G("indian_bphs", r"Dasha Systems"), G("vedic_astrology", r"Dasha Systems")], "dashas", "vedic")
        # 4. Saturn's house (needs known time)
        if not approx:
            sat = next(p for p in c["planets"] if p["name"] == "Saturn")
            h = int(sat["house"])
            lg = LANGS[ci % 3]
            txt = HOUSE_Q[lg].format(h=(_ord(h) if lg != "hi" else HI_ORD[h]))
            add("saturn-house", lg, txt,
                [G("houses", rf"{ORDW[h]} House"), G("planets", r"Saturn", 1)], "houses", sysname)
        # 5. first major natal aspect between two planets (not angles)
        for a in c["aspects"]:
            if a["type"] in ASPECT_FILE and a["planet1"] not in ("MC", "ASC") and a["planet2"] not in ("MC", "ASC"):
                lg = LANGS[(ci + 1) % 3]
                add("aspect", lg, ASPECT_Q[lg].format(a=a["type"], p1=a["planet1"], p2=a["planet2"]),
                    [G("aspects", ASPECT_FILE[a["type"]]), G("aspects", r"Planet Pairs", 1)], "aspects", sysname)
                break
    return out


def free_queries() -> list[dict]:
    out = []
    for split, intents in (("dev", INTENTS), ("holdout", HOLDOUT), ("holdout2", HOLDOUT2)):
        for iid, topic, system, texts, gold in intents:
            for lang in LANGS:
                out.append({"id": f"{iid}:{lang}", "source": "free", "split": split, "chart": None, "lang": lang,
                            "text": texts[lang], "topic": topic, "system": system, "gold": gold})
    return out


def validate(queries: list[dict]) -> None:
    from app.rag.chunking import chunk_corpus
    from evals.rag.metrics import resolve_gold

    chunks = chunk_corpus(KB)
    bad = []
    for q in queries:
        rel = resolve_gold(q["gold"], chunks)
        if not rel:
            bad.append(q["id"])
        elif not any(g == 2 for g in rel.values()):
            bad.append(q["id"] + " (no grade-2 chunk)")
    if bad:
        raise SystemExit(f"gold resolves to nothing for: {bad}")


def main() -> int:
    from evals.rag import gap_queries as GQ

    charts = json.loads((HERE.parent / "fixtures" / "real_charts.json").read_text(encoding="utf-8"))
    qs = chart_queries(charts) + free_queries()
    for q in qs:                                   # corpus growth: add the new files' matchers, keep the old gold as strict
        iid = q["id"].rsplit(":", 1)[0]
        extra = GQ.EXTRA_GOLD.get(iid)
        if q["source"] == "chart" and q["id"].split(":")[1] in GQ.EXTRA_CHART_GOLD:
            kind = q["id"].split(":")[1]
            c = charts[q["chart"]]
            arg = c["vedic"]["dasha"]["maha_dasha"]["current"] if kind == "dasha" else next(
                (int(p["house"]) for p in c["planets"] if p["name"] == "Saturn" and p.get("house")), None)
            extra = GQ.EXTRA_CHART_GOLD[kind](arg) if arg is not None else None
        if extra:
            q["gold_strict"] = q["gold"]
            q["gold"] = q["gold"] + extra
    qs += GQ.gap_free_queries() + GQ.chart_gap_queries(charts)
    validate(qs)
    (HERE / "queries.jsonl").write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in qs) + "\n",
                                        encoding="utf-8")
    by_lang = {l: sum(1 for q in qs if q["lang"] == l) for l in LANGS}
    print(f"wrote {len(qs)} queries ({by_lang}); chart-derived={sum(q['source'] == 'chart' for q in qs)}; "
          f"holdout={sum(q['split'] == 'holdout' for q in qs)} holdout2={sum(q['split'] == 'holdout2' for q in qs)} holdout3={sum(q['split'] == 'holdout3' for q in qs)} holdout4={sum(q['split'] == 'holdout4' for q in qs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
