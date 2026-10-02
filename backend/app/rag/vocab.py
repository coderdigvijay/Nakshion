"""Complete vocabulary classes for the query glossary (BUG-027): every member of a class is mapped, not just the ones
a test happened to use. Query-side only: this maps how people SPELL a term (Devanagari, Roman, abbreviations) onto the
English words the knowledge base uses. It adds no astrological claim.

Classes: 12 signs, 27 nakshatras (incl. joined Devanagari forms), 12 ordinals and house-lord words, house types,
planets and their nicknames, dasha / varga abbreviations, kuta and dosha names plus 6/8 style numerics, Panchang
limbs, tithi names and weekdays.
Merged into `glossary.GLOSS` / `NAK_HI` / `NAK_ROMAN` without overriding hand-written entries.
"""

from __future__ import annotations

import re

# sign (English) -> spellings (Devanagari + Roman). The value placed in the glossary is "english sanskrit".
SIGNS: dict[str, tuple[str, list[str]]] = {
    "aries": ("mesha", ["मेष", "मेश", "mesh", "mesha", "meish"]),
    "taurus": ("vrishabha", ["वृषभ", "वृष", "vrishabh", "vrishabha", "vrish", "vrushabh", "brishabh", "vrisabha"]),
    "gemini": ("mithuna", ["मिथुन", "mithun", "mithuna"]),
    "cancer": ("karka", ["कर्क", "कर्कट", "kark", "karka", "karak", "kataka"]),
    "leo": ("simha", ["सिंह", "singh", "simha", "sinh"]),
    "virgo": ("kanya", ["कन्या", "kanya", "kanyaa"]),
    "libra": ("tula", ["तुला", "tula", "tulaa", "thula"]),
    "scorpio": ("vrishchika", ["वृश्चिक", "vrishchik", "vrishchika", "vrischik", "vruschik", "brishchik", "vrishik"]),
    "sagittarius": ("dhanu", ["धनु", "धनुष", "dhanu", "dhanus", "dhanush"]),
    "capricorn": ("makara", ["मकर", "makar", "makara"]),
    "aquarius": ("kumbha", ["कुंभ", "कुम्भ", "kumbh", "kumbha", "kumb"]),
    "pisces": ("meena", ["मीन", "meen", "meena", "mina"]),
}

# nakshatra (English, as the KB spells it) -> Devanagari spellings (spaced and JOINED forms) + Roman variants
NAKSHATRAS: dict[str, tuple[list[str], list[str]]] = {
    "Ashwini": (["अश्विनी", "अश्वनी", "अश्विन"], ["ashwini", "ashvini", "aswini", "ashwani"]),
    "Bharani": (["भरणी"], ["bharani", "bharni"]),
    "Krittika": (["कृत्तिका", "कृतिका", "कृत्तका"], ["krittika", "kritika", "krithika", "krittka"]),
    "Rohini": (["रोहिणी", "रोहणी"], ["rohini", "rohni"]),
    "Mrigashira": (["मृगशिरा", "मृगशीर्ष", "मृगशिर", "मृगशिरस"], ["mrigashira", "mrigshira", "mrigasira", "mrigashirsha"]),
    "Ardra": (["आर्द्रा", "आद्रा", "अर्द्रा"], ["ardra", "aardra", "adra"]),
    "Punarvasu": (["पुनर्वसु", "पुनर्वस"], ["punarvasu", "punarvas", "punarbasu"]),
    "Pushya": (["पुष्य", "पूष्य", "पुष्या"], ["pushya", "pushy", "pusya", "poshya"]),
    "Ashlesha": (["आश्लेषा", "अश्लेषा", "आश्लेशा"], ["ashlesha", "aslesha", "ashlesa", "ashlesh"]),
    "Magha": (["मघा", "मखा"], ["magha", "makha"]),
    "Purva Phalguni": (["पूर्वाफाल्गुनी", "पूर्वा फाल्गुनी", "पूर्वा फल्गुनी", "पूर्वाफल्गुनी", "पूर्व फाल्गुनी"],
                       ["purva phalguni", "poorva phalguni", "purvaphalguni", "poorvaphalguni", "purva falguni", "pubba"]),
    "Uttara Phalguni": (["उत्तराफाल्गुनी", "उत्तरा फाल्गुनी", "उत्तरा फल्गुनी", "उत्तराफल्गुनी", "उत्तर फाल्गुनी"],
                        ["uttara phalguni", "uttra phalguni", "uttaraphalguni", "uttaraphalguni", "uttara falguni"]),
    "Hasta": (["हस्त", "हस्ता"], ["hasta", "hast"]),
    "Chitra": (["चित्रा", "चित्र"], ["chitra", "chitraa", "citra"]),
    "Swati": (["स्वाति", "स्वाती", "स्वात"], ["swati", "svati", "swathi", "swaati"]),
    "Vishakha": (["विशाखा", "विषाखा"], ["vishakha", "visakha", "vishaka", "vishakhaa"]),
    "Anuradha": (["अनुराधा", "अनुराध"], ["anuradha", "anuradhaa", "anuradh"]),
    "Jyeshtha": (["ज्येष्ठा", "ज्येष्ठ", "जेष्ठा", "ज्येश्ठा"], ["jyeshtha", "jyestha", "jyeshta", "jyeshth", "jeshtha"]),
    "Mula": (["मूल", "मूला", "मुल"], ["mula", "mool", "moola", "mul"]),
    "Purva Ashadha": (["पूर्वाषाढ़ा", "पूर्वाषाढा", "पूर्वा आषाढ़ा", "पूर्वा आषाढा", "पूर्वाषाढ", "पूर्व आषाढ़ा"],
                      ["purva ashadha", "poorva ashadha", "purvashadha", "poorvashadha", "purva ashada", "purvaashadha"]),
    "Uttara Ashadha": (["उत्तराषाढ़ा", "उत्तराषाढा", "उत्तरा आषाढ़ा", "उत्तरा आषाढा", "उत्तराषाढ", "उत्तर आषाढ़ा"],
                       ["uttara ashadha", "uttra ashadha", "uttarashadha", "uttarashada", "uttaraashadha"]),
    "Shravana": (["श्रवण", "श्रावण", "श्रवणा"], ["shravana", "sravana"]),
    "Dhanishta": (["धनिष्ठा", "श्रविष्ठा", "धनिष्टा", "धनिष्ठ"], ["dhanishta", "dhanishtha", "dhanista", "shravishtha"]),
    "Shatabhisha": (["शतभिषा", "शतभिषक", "शतभिष", "शतभीषा"], ["shatabhisha", "satabhisha", "shatabhishak", "shatbhisha", "shatabisha"]),
    "Purva Bhadrapada": (["पूर्वाभाद्रपद", "पूर्वा भाद्रपद", "पूर्वाभाद्रपदा", "पूर्व भाद्रपद", "पूर्वा भाद्रपदा", "पूर्वाभाद्रपद"],
                         ["purva bhadrapada", "poorva bhadrapada", "purvabhadra", "poorvabhadra", "purva bhadra", "purvabhadrapada", "purva bhadrapad"]),
    "Uttara Bhadrapada": (["उत्तराभाद्रपद", "उत्तरा भाद्रपद", "उत्तराभाद्रपदा", "उत्तर भाद्रपद", "उत्तरा भाद्रपदा"],
                          ["uttara bhadrapada", "uttra bhadrapada", "uttarabhadra", "uttarabhadrapada", "uttara bhadra", "uttara bhadrapad"]),
    "Revati": (["रेवती", "रेवति"], ["revati", "revathi", "raivati"]),
}

# house ordinals 1-12: Hindi (m/f/oblique), Sanskrit, Roman Hindi -> "Nth nword"
_ORD_EN = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"]
_ORD_SFX = ["st", "nd", "rd"] + ["th"] * 9
ORDINAL_WORDS: list[list[str]] = [
    ["पहला", "पहली", "पहले", "प्रथम", "pehla", "pehle", "pehli", "pahla", "pahle", "pratham", "lagna bhav"],
    ["दूसरा", "दूसरी", "दूसरे", "द्वितीय", "doosra", "dusra", "doosre", "dusre", "dwitiya", "dvitiya"],
    ["तीसरा", "तीसरी", "तीसरे", "तृतीय", "teesra", "tisra", "teesre", "tisre", "tritiya"],
    ["चौथा", "चौथी", "चौथे", "चतुर्थ", "chautha", "chauthe", "chauthi", "chaturth"],
    ["पांचवां", "पांचवें", "पाँचवाँ", "पाँचवें", "पाचवां", "पाचवें", "पांचवी", "पंचम", "paanchva", "panchva", "paanchve", "panchve", "pancham", "panchm"],
    ["छठा", "छठी", "छठे", "छठवां", "षष्ठ", "षष्ठम", "chhatha", "chatha", "chhathe", "chhathe", "shashth", "shashtha"],
    ["सातवां", "सातवाँ", "सातवें", "सातवी", "सप्तम", "saatva", "satva", "saatve", "satve", "saptam", "saptama", "saatwa", "saatwe", "satwa", "satwe"],
    ["आठवां", "आठवाँ", "आठवें", "आठवी", "अष्टम", "aathva", "athva", "aathve", "athve", "ashtam", "ashtama", "aathwa", "aathwe"],
    ["नौवां", "नौवाँ", "नौवें", "नवां", "नवें", "नवम", "nauva", "nauve", "navva", "navam", "navama", "nauwa", "nauwe"],
    ["दसवां", "दसवाँ", "दसवें", "दशम", "दसवी", "dasva", "dasve", "dasvan", "dasham", "dashama", "daswa", "daswe"],
    ["ग्यारहवां", "ग्यारहवाँ", "ग्यारहवें", "एकादश", "gyarahva", "gyarahve", "gyarvan", "ekadash", "ekadasha", "gyarahwa"],
    ["बारहवां", "बारहवाँ", "बारहवें", "द्वादश", "barahva", "barahve", "barahwa", "dwadash", "dwadasha", "dvadasha"],
]
# house-lord words: Sanskrit "-esha" forms
HOUSE_LORDS: list[list[str]] = [
    ["लग्नेश", "तनुपति", "lagnesh", "lagnesha"], ["धनेश", "dhanesh", "dhanesha"], ["सहजेश", "पराक्रमेश", "sahajesh", "parakramesh"],
    ["सुखेश", "चतुर्थेश", "sukhesh", "chaturthesh"], ["पंचमेश", "पुत्रेश", "panchamesh", "putresh", "panchmesh"],
    ["षष्ठेश", "रिपुेश", "shashthesh", "shashtesh"], ["सप्तमेश", "जायेश", "saptamesh", "saptmesh", "jayesh"],
    ["अष्टमेश", "आयुरेश", "ashtamesh", "ashtmesh"], ["नवमेश", "भाग्येश", "navamesh", "navmesh", "bhagyesh"],
    ["दशमेश", "कर्मेश", "dashamesh", "dashmesh", "karmesh"], ["एकादशेश", "लाभेश", "ekadashesh", "labhesh"],
    ["द्वादशेश", "व्ययेश", "dwadashesh", "dvadashesh", "vyayesh"],
]
HOUSE_TYPES = {
    "kendra": "kendra angular houses house classifications", "केंद्र": "kendra angular houses house classifications",
    "kendr": "kendra angular houses house classifications", "केन्द्र": "kendra angular houses house classifications",
    "trikona": "trikona trinal houses house classifications", "त्रिकोण भाव": "trikona trinal houses house classifications",
    "dusthana": "dusthana difficult houses house classifications", "दुःस्थान": "dusthana difficult houses house classifications",
    "dusthan": "dusthana difficult houses house classifications", "दुस्थान": "dusthana difficult houses house classifications",
    "upachaya": "upachaya growth houses house classifications", "उपचय": "upachaya growth houses house classifications",
    "upachay": "upachaya growth houses house classifications", "maraka": "maraka house classifications",
    "मारक": "maraka house classifications", "panapara": "panapara succedent house classifications", "apoklima": "apoklima cadent house classifications",
}
HOUSE_WORDS = {"ghar": "house", "bhav": "house", "bhava": "house", "भाव": "house", "घर": "house", "sthan": "house", "स्थान": "house",
               "ghar me": "house", "bhav me": "house"}

PLANETS: dict[str, list[str]] = {
    "sun": ["surya", "ravi", "bhanu", "aditya", "सूर्य", "रवि", "भानु", "आदित्य", "सूरज", "suraj"],
    "moon": ["chandra", "chandrama", "soma", "chand", "चंद्र", "चन्द्र", "चंद्रमा", "चन्द्रमा", "सोम", "चांद"],
    "mars": ["mangal", "kuja", "bhauma", "angaraka", "मंगल", "कुज", "भौम", "अंगारक"],
    "mercury": ["budha", "budh", "soumya", "बुध", "सौम्य"],
    "jupiter": ["guru", "brihaspati", "jeeva", "बृहस्पति", "गुरु", "देवगुरु", "बृहस्पती"],
    "venus": ["shukra", "sukra", "bhrigu", "शुक्र", "भृगु"],
    "saturn": ["shani", "sani", "manda", "शनि", "शनी", "मंद", "शनिदेव", "shanidev"],
    "rahu": ["rahu", "राहु", "राहू"],
    "ketu": ["ketu", "केतु", "केतू"],
}
ABBREV = {
    "md": "mahadasha dasha", "ad": "antardasha dasha", "pd": "pratyantardasha dasha", "ad/pd": "antardasha pratyantardasha", "asc": "ascendant lagna", "आरोही": "ascendant lagna",
    "mc": "midheaven", "d1": "rashi chart birth chart", "d2": "hora divisional chart",
    "d3": "drekkana divisional chart", "d4": "chaturthamsa divisional chart", "d7": "saptamsa divisional chart children",
    "d9": "navamsa divisional chart", "d10": "dashamsa career divisional chart", "d12": "dwadashamsa divisional chart parents",
    "d16": "shodashamsa divisional chart vehicles", "d20": "vimshamsa divisional chart", "d24": "chaturvimshamsa divisional chart",
    "d27": "bhamsa divisional chart", "d30": "trimshamsa divisional chart", "d40": "khavedamsa divisional chart",
    "d45": "akshavedamsa divisional chart", "d60": "shashtiamsa divisional chart", "varga": "divisional chart varga",
    "वर्ग": "divisional chart varga",
}
KUTA = {
    "shadashtak": "shadashtak bhakoot 6th 8th", "षडाष्टक": "shadashtak bhakoot 6th 8th", "shadashtaka": "shadashtak bhakoot 6th 8th",
    "dwirdwadash": "dwirdwadash bhakoot 2nd 12th", "dwirdwadasha": "dwirdwadash bhakoot 2nd 12th", "द्विर्द्वादश": "dwirdwadash bhakoot 2nd 12th",
    "dvirdvadash": "dwirdwadash bhakoot 2nd 12th", "navapancham": "navapancham bhakoot 5th 9th", "navpancham": "navapancham bhakoot 5th 9th",
    "navapancham": "navapancham bhakoot 5th 9th", "नवपंचम": "navapancham bhakoot 5th 9th", "navpancham": "navapancham bhakoot 5th 9th",
    "bhakoot": "bhakoot rasi koota", "bhakut": "bhakoot rasi koota", "bhakuta": "bhakoot rasi koota", "bhakoota": "bhakoot rasi koota",
    "bhakkot": "bhakoot rasi koota", "भकूट": "bhakoot rasi koota", "भकुट": "bhakoot rasi koota",
    "gana": "gana koota", "gan": "gana koota", "गण": "gana koota", "ganakoota": "gana koota",
    "nadi": "nadi koota", "naadi": "nadi koota", "नाड़ी": "nadi koota", "नाडी": "nadi koota", "nadee": "nadi koota",
    "vashya": "vashya koota", "vashy": "vashya koota", "vasya": "vashya koota", "वश्य": "vashya koota",
    "tara": "tara dina koota", "taara": "tara dina koota", "तारा": "tara dina koota", "dina": "tara dina koota",
    "yoni": "yoni koota", "योनि": "yoni koota", "yoney": "yoni koota", "graha maitri": "graha maitri koota", "grah maitri": "graha maitri koota",
    "ग्रह मैत्री": "graha maitri koota", "maitri": "graha maitri koota", "मैत्री": "graha maitri koota",
    "varna": "varna koota temperament", "varn": "varna koota temperament", "वर्ण": "varna koota temperament",
    "koota": "koota", "kuta": "koota", "kut": "koota", "कूट": "koota", "कुट": "koota", "ashtakoota": "ashtakoota guna milan", "अष्टकूट": "ashtakoota guna milan",
    "manglik": "mangal dosha manglik mars", "mangalik": "mangal dosha manglik mars", "manglic": "mangal dosha manglik mars",
    "kuja dosha": "mangal dosha kuja mars", "kuja dosh": "mangal dosha kuja mars", "कुज दोष": "mangal dosha kuja mars",
    "mangal dosh": "mangal dosha mars", "मंगल दोष": "mangal dosha mars", "मांगलिक": "mangal dosha manglik mars", "मंगलिक": "mangal dosha manglik mars",
    "bhom dosh": "mangal dosha mars", "bhauma dosha": "mangal dosha mars",
}
PANCHANG = {
    "tithi": "tithi lunar day", "तिथि": "tithi lunar day", "vaar": "vara weekday", "var": "vara weekday", "वार": "vara weekday", "vara": "vara weekday",
    "करण": "karana", "karan": "karana", "karana": "karana", "योग": "yoga", "paksha": "paksha lunar fortnight", "पक्ष": "paksha lunar fortnight",
    "शुक्ल पक्ष": "shukla paksha waxing", "कृष्ण पक्ष": "krishna paksha waning", "shukla paksha": "shukla paksha waxing",
    "krishna paksha": "krishna paksha waning", "panch ang": "panchang five limbs", "पंचांग": "panchang five limbs", "पंच अंग": "panchang five limbs",
}
TITHIS = [("pratipada", ["प्रतिपदा", "परिवा", "pratipada", "padyami"]), ("dwitiya", ["द्वितीया", "dwitiya", "dvitiya", "dooj", "beej"]),
          ("tritiya", ["तृतीया", "tritiya", "teej"]), ("chaturthi", ["चतुर्थी", "chaturthi", "chauth"]), ("panchami", ["पंचमी", "panchami", "panchmi"]),
          ("shashthi", ["षष्ठी", "shashthi", "chhath", "shasthi"]), ("saptami", ["सप्तमी", "saptami"]), ("ashtami", ["अष्टमी", "ashtami"]),
          ("navami", ["नवमी", "navami"]), ("dashami", ["दशमी", "dashami", "dasami"]), ("ekadashi", ["एकादशी", "ekadashi", "gyaras"]),
          ("dwadashi", ["द्वादशी", "dwadashi", "dvadashi", "barah"]), ("trayodashi", ["त्रयोदशी", "trayodashi", "pradosh", "तेरस", "teras"]),
          ("chaturdashi", ["चतुर्दशी", "chaturdashi", "chaudas"]), ("purnima", ["पूर्णिमा", "purnima", "poornima", "punam"]),
          ("amavasya", ["अमावस्या", "अमावस", "amavasya", "amavas", "amavasi"])]
WEEKDAYS = {"sunday": ["रविवार", "इतवार", "ravivar", "itwar", "ravi var", "sunday"], "monday": ["सोमवार", "somvar", "somwar", "monday"],
            "tuesday": ["मंगलवार", "mangalvar", "mangalwar", "tuesday"], "wednesday": ["बुधवार", "budhvar", "budhwar", "wednesday"],
            "thursday": ["गुरुवार", "बृहस्पतिवार", "वीरवार", "guruvar", "guruwar", "brihaspativar", "veervar", "thursday"],
            "friday": ["शुक्रवार", "shukravar", "shukrawar", "friday"], "saturday": ["शनिवार", "shanivar", "shaniwar", "shanichar", "saturday"]}


def ordinal_keys() -> set[str]:
    """Ordinal and house-lord words: these REPLACE older hand-written one-word entries so both "5th" and "fifth" are searched."""
    return {w for ws in ORDINAL_WORDS + HOUSE_LORDS for w in ws}


def build() -> dict[str, str]:
    """term -> English search words, all keys un-normalised (the glossary normalises on merge)."""
    out: dict[str, str] = {}
    for eng, (san, names) in SIGNS.items():
        for n in names:
            out[n] = f"{eng} {san}"
    for en, names in PLANETS.items():
        for n in names:
            out[n] = en if n in ("rahu", "ketu", "राहु", "राहू", "केतु", "केतू") else f"{en} {n if n.isascii() else ''}".strip()
    for i, words in enumerate(ORDINAL_WORDS, 1):
        for w in words:
            out[w] = f"{i}{_ORD_SFX[i - 1]} {_ORD_EN[i - 1]}"
    for i, words in enumerate(HOUSE_LORDS, 1):
        for w in words:
            out[w] = f"{i}{_ORD_SFX[i - 1]} {_ORD_EN[i - 1]} lord house"
    out.update(HOUSE_TYPES)
    out.update({k: v for k, v in HOUSE_WORDS.items() if " " not in k})
    out.update(ABBREV)
    out.update(KUTA)
    out.update(PANCHANG)
    for en, names in TITHIS:
        for n in names:
            out[n] = (out[n] + " " if n in out else "") + f"{en} tithi"      # dwitiya / tritiya are also ordinals: keep both
    for en, names in WEEKDAYS.items():
        for n in names:
            out[n] = f"{en} weekday vara"
    return out


# "6/8", "2/12", "5/9" (also 6-8, 6 8 when 'koota/bhakoot/milan/rashi' is near) -> the bhakoot sub-rule names
_NUMERIC = [(re.compile(r"(?<!\d)6\s*[/\-]\s*8(?!\d)"), " shadashtak bhakoot 6th 8th "),
            (re.compile(r"(?<!\d)2\s*[/\-]\s*12(?!\d)"), " dwirdwadash bhakoot 2nd 12th "),
            (re.compile(r"(?<!\d)5\s*[/\-]\s*9(?!\d)"), " navapancham bhakoot 5th 9th ")]


def expand_numeric(t: str) -> str:
    for rx, rep in _NUMERIC:
        t = rx.sub(rep, t)
    return t


def nakshatra_forms() -> tuple[dict[str, str], dict[str, str]]:
    """(devanagari form -> English name, roman form -> English name)."""
    dev, rom = {}, {}
    for eng, (devs, roms) in NAKSHATRAS.items():
        for d in devs:
            dev[d] = eng
        for r in roms:
            rom[r] = eng
        rom[eng.lower()] = eng
    return dev, rom
