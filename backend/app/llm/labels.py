"""Citation chip labels in the reply language.

Factor labels are generated in English by the engine/facts layer. For a Hindi reply the UI would show
English chips under a Hindi answer, so labels are re-rendered from the stable factor ID structure.
Unknown shapes fall back to the English label (never wrong, only unlocalised). Hinglish uses Roman
script, so it keeps the English label.
"""

from __future__ import annotations

PLANET_HI = {"SUN": "सूर्य", "MOON": "चंद्रमा", "MERCURY": "बुध", "VENUS": "शुक्र", "MARS": "मंगल", "JUPITER": "गुरु",
             "SATURN": "शनि", "URANUS": "यूरेनस", "NEPTUNE": "नेपच्यून", "PLUTO": "प्लूटो", "NORTH_NODE": "राहु",
             "SOUTH_NODE": "केतु", "RAHU": "राहु", "KETU": "केतु", "ASC": "लग्न", "MC": "मध्य आकाश", "CHIRON": "काइरॉन"}
SIGN_HI = {"ARIES": "मेष", "TAURUS": "वृषभ", "GEMINI": "मिथुन", "CANCER": "कर्क", "LEO": "सिंह", "VIRGO": "कन्या",
           "LIBRA": "तुला", "SCORPIO": "वृश्चिक", "SAGITTARIUS": "धनु", "CAPRICORN": "मकर", "AQUARIUS": "कुंभ",
           "PISCES": "मीन"}
ASPECT_HI = {"CONJUNCTION": "युति", "CONJ": "युति", "OPPOSITION": "प्रतियुति", "OPP": "प्रतियुति", "SQUARE": "चतुष्कोण",
             "SQ": "चतुष्कोण", "TRINE": "त्रिकोण", "TRI": "त्रिकोण", "SEXTILE": "षडाष्टक", "SEXT": "षडाष्टक",
             "QUINCUNX": "द्विद्वादश"}
NAK_HI = {"ASHWINI": "अश्विनी", "BHARANI": "भरणी", "KRITTIKA": "कृत्तिका", "ROHINI": "रोहिणी", "MRIGASHIRA": "मृगशिरा",
          "ARDRA": "आर्द्रा", "PUNARVASU": "पुनर्वसु", "PUSHYA": "पुष्य", "ASHLESHA": "आश्लेषा", "MAGHA": "मघा",
          "PURVA_PHALGUNI": "पूर्वा फाल्गुनी", "UTTARA_PHALGUNI": "उत्तरा फाल्गुनी", "HASTA": "हस्त", "CHITRA": "चित्रा",
          "SWATI": "स्वाति", "VISHAKHA": "विशाखा", "ANURADHA": "अनुराधा", "JYESHTHA": "ज्येष्ठा", "MULA": "मूल",
          "PURVA_ASHADHA": "पूर्वाषाढ़ा", "UTTARA_ASHADHA": "उत्तराषाढ़ा", "SHRAVANA": "श्रवण", "DHANISHTA": "धनिष्ठा",
          "SHATABHISHA": "शतभिषा", "PURVA_BHADRAPADA": "पूर्वा भाद्रपद", "UTTARA_BHADRAPADA": "उत्तरा भाद्रपद",
          "REVATI": "रेवती"}
YOGA_HI = {"GAJAKESARI": "गजकेसरी योग", "RAJA": "राजयोग", "DHANA": "धनयोग", "MANGAL": "मंगल दोष",
           "BUDHADITYA": "बुधादित्य योग", "KAAL_SARP": "कालसर्प दोष"}
HOUSE_HI = {1: "पहले", 2: "दूसरे", 3: "तीसरे", 4: "चौथे", 5: "पांचवें", 6: "छठे", 7: "सातवें", 8: "आठवें", 9: "नौवें",
            10: "दसवें", 11: "ग्यारहवें", 12: "बारहवें"}


def _pl(x: str) -> str:
    return PLANET_HI.get(x, x.title().replace("_", " "))


def localize_label(factor_id: str, label_en: str, language: str) -> str:
    if language != "hindi":
        return label_en
    p = factor_id.split(".")
    try:
        if factor_id == "META.TIME_UNKNOWN":
            return "जन्म समय अज्ञात: लग्न, भाव और सटीक दशा तिथियां उपलब्ध नहीं"
        if p[0] == "N" and len(p) == 4 and p[2] == "SIGN":
            return (f"जन्म कुंडली: लग्न {SIGN_HI.get(p[3], p[3])} (सायन)" if p[1] == "ASC"
                    else f"जन्म {_pl(p[1])} {SIGN_HI.get(p[3], p[3])} राशि में (सायन)")
        if p[0] == "N" and len(p) == 3 and p[2].startswith("H") and p[2][1:].isdigit():
            return f"जन्म {_pl(p[1])} {HOUSE_HI.get(int(p[2][1:]), p[2][1:])} भाव में"
        if p[0] == "A" and len(p) == 4:
            return f"जन्म {_pl(p[1])} और {_pl(p[3])} के बीच {ASPECT_HI.get(p[2], p[2].lower())}"
        if p[0] == "VN" and len(p) == 4 and p[2] == "RASHI":
            return f"{_pl(p[1])} {SIGN_HI.get(p[3], p[3])} राशि में (निरयन)"
        if p[0] == "VN" and p[1] == "LAGNA":
            return f"{SIGN_HI.get(p[2], p[2])} लग्न (निरयन)"
        if p[0] == "VN" and len(p) == 4 and p[2] == "NAK":
            return f"चंद्र नक्षत्र: {NAK_HI.get('_'.join(p[3:]), p[3].title())}"
        if p[0] == "V" and p[1] == "MD":
            return f"वर्तमान {_pl(p[2])} महादशा"
        if p[0] == "V" and p[1] == "AD":
            return f"वर्तमान {_pl(p[2])} अंतर्दशा"
        if p[0] == "V" and p[1] == "SADESATI":
            return "साढ़ेसाती का चरण"
        if p[0] == "Y":
            return YOGA_HI.get(p[1], label_en)
        if p[0] == "T" and len(p) >= 5 and p[3] == "N":
            return f"गोचर {_pl(p[1])} का जन्म {_pl(p[4])} से {ASPECT_HI.get(p[2], p[2].lower())}"
        if p[0] == "T" and p[1] == "MOON" and len(p) == 3 and p[2].startswith("H"):
            return f"आज चंद्रमा का गोचर {HOUSE_HI.get(int(p[2][1:]), p[2][1:])} भाव में"
    except (ValueError, IndexError):
        pass
    return label_en


_SUFFIX = {"english": {"vedic": "Vedic (sidereal)", "western": "Western (tropical)"},
           "hindi": {"vedic": "वैदिक (निरयन)", "western": "पाश्चात्य (सायन)"}}


def system_suffix(factor_id: str, language: str) -> str:
    """" · Vedic (sidereal)" / " · Western (tropical)" for the chip, in the reply language. Neutral ids get none."""
    from app.llm.facts import factor_system

    fs = factor_system(factor_id)
    if fs not in ("vedic", "western") or factor_id.startswith("T.MOON.H"):
        return ""
    return " · " + _SUFFIX["hindi" if language == "hindi" else "english"][fs]


def with_system(factor_id: str, label: str, language: str) -> str:
    suffix = system_suffix(factor_id, language)
    if not suffix:
        return label
    for redundant in (" (tropical)", " (sidereal)"):
        label = label.replace(redundant, "")
    return label + suffix
