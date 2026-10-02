"""Safety policy (llm-integration.md §8, ai_llm_rules §8).

- Input pre-filter: rule-based, multilingual. Crisis / medical emergency / abuse skip the
  LLM entirely and return a STATIC, pre-written reply (never improvised by a model).
- Output filter: forbidden classes checked on every model answer. A hit triggers one
  repair; a second hit returns the canned reply for that class.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

InputClass = Literal["crisis", "medical_emergency", "abuse"]
OutputClass = Literal["death", "child_sex", "medical_legal_financial", "paid_remedy", "caste", "leak", "fatalism"]

DISCLAIMER = {
    "english": "For self-reflection and entertainment. Not a substitute for professional advice.",
    "hindi": "यह आत्म-चिंतन और मनोरंजन के लिए है। यह पेशेवर सलाह का विकल्प नहीं है।",
    "hinglish": "Yeh self-reflection aur entertainment ke liye hai. Professional advice ka substitute nahi hai.",
}

# ----------------------------------------------------------------------------- input


def _rx(*parts: str) -> re.Pattern[str]:
    return re.compile("|".join(parts), re.I)


# --- normalisation (BUG-025): obfuscated phrasing must not slip past the crisis filter ------------------------------

_ZERO_WIDTH = re.compile("[​-‏‪-‮⁠-⁤﻿­᠎]")
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i", "|": "i", "¡": "i"})
_LEET_CHARS = "013457@$!|¡"
_LEET_IN_WORD = re.compile(rf"(?<=[a-z])[{re.escape(_LEET_CHARS)}]|[{re.escape(_LEET_CHARS)}](?=[a-z])")
_INTRA_PUNCT = re.compile(r"(?<=[a-z])[*.\-_~^`+·•](?=[a-z])")
_SPACED_LETTERS = re.compile(r"(?<![a-z])(?:[a-z][\s.\-_*]+){2,}[a-z](?![a-z])")
_REPEATS = re.compile(r"([a-zऀ-ॿ])\1+")
_NON_LETTER = re.compile(r"[^a-zऀ-ॿ]+")
# Devanagari variants: nukta forms, chandrabindu, ZWJ/ZWNJ, candrabindu vs anusvara.
_DEV_MAP = str.maketrans({"ँ": "ं", "़": None, "‌": None, "‍": None, "ऑ": "ॉ"})
_DEV_ALIASES = [("ख़", "ख")]


def normalize_variants(text: str) -> list[str]:
    """Lower-cased, NFKC, zero-width stripped, Devanagari nukta/chandrabindu folded. Returns the variants the crisis
    patterns run on: base, leet+punctuation folded, spaced letters joined, repeated letters collapsed (Hinglish
    spellings: jeene/jine, mann/man), and a letters-only squash for the few unambiguous long tokens."""
    t = unicodedata.normalize("NFKC", text or "")
    t = _ZERO_WIDTH.sub("", t).lower()
    t = unicodedata.normalize("NFD", t).translate(_DEV_MAP)           # nukta lives in NFD
    t = unicodedata.normalize("NFC", t)
    t = re.sub(r"\s+", " ", t)
    base = t
    folded = _INTRA_PUNCT.sub("", _LEET_IN_WORD.sub(lambda m: m.group(0).translate(_LEET), t))
    spaced = _SPACED_LETTERS.sub(lambda m: re.sub(r"[\s.\-_*]+", "", m.group(0)), folded)
    repeats = _REPEATS.sub(r"\1", spaced)
    squash = _NON_LETTER.sub("", spaced)
    out: list[str] = []
    for v in (base, folded, spaced, repeats):
        if v not in out:
            out.append(v)
    # The squash (letters only, no boundaries) runs only when obfuscation was actually undone, so ordinary text such as
    # "skill myself" is never glued into "killmyself".
    return out + (["\x00" + squash] if (folded != base or spaced != folded) else [])


_INPUT_RULES: list[tuple[InputClass, re.Pattern[str]]] = [
    ("crisis", _rx(
        # English (explicit)
        r"\b(kill|hurt|harm|cut|hang|drown|poison|end|off)(?:ing)?\s*(myself|my\s*self)\b", r"\bkill\s+me\b",
        r"\bsuicid", r"\bsu[i1]?c[iy]+d(?:e|al)?\b", r"\bsuic?ied\b", r"\bsucide\b", r"\bsuiside\b", r"\bsicide\b",
        r"\bend\s+(my|it)\s+(life|all)\b", r"\bend(?:ing)?\s+(?:it\s+all|everything|this\s+life)\b",
        r"\btake\s+my\s+(?:own\s+)?life\b", r"\btak(?:e|ing)\s+my\s+own\s+life\b",
        r"\bwant\s+to\s+die\b", r"\bwanna\s+die\b", r"\bwish\s+i\s+(?:was|were)\s+(?:dead|never\s+born)\b", r"\bwish\s+i\s+(?:never|wasn'?t)\s+(?:born|existed)\b",
        r"\b(?:better|rather)\s+(?:off\s+)?dead\b", r"\bdon'?t\s+want\s+to\s+(live|be\s+alive|exist|wake\s+up)\b",
        r"\bno\s+reason\s+to\s+(?:live|go\s+on|be\s+alive)\b", r"\bnot\s+worth\s+living\b", r"\blife\s+(?:is\s+)?(?:not|isn'?t)\s+worth\b",
        r"\b(?:tired|sick|done|finished)\s+(?:of|with)\s+(?:living|life|being\s+alive)\b", r"\bcan'?t\s+go\s+on\s+(?:living|like\s+this|anymore)\b",
        r"\bdon'?t\s+want\s+to\s+(?:be\s+here|exist)\s+anymore\b", r"\bwant\s+to\s+disappear\s+forever\b",
        r"\bself[-\s]?harm", r"\bself[-\s]?injur", r"\bcut(ting)?\s+(?:myself|my\s+wrists?)\b", r"\bslit(?:ting)?\s+my\s+wrists?\b",
        r"\bjump(?:ing)?\s+(?:off|from)\s+(?:a|the|my)?\s*(?:bridge|building|roof|terrace|balcony|cliff)\b",
        r"\b(?:take|swallow|taking)\s+(?:all\s+)?(?:my|the|a\s+bunch\s+of)\s+(?:pills|tablets|sleeping\s+pills)\b",
        r"\bhang(?:ing)?\s+myself\b", r"\bsewer\s*slid",
        # obfuscations / euphemisms
        r"\bkms\b", r"\bun\s*-?\s*aliv(?:e|ing|ed)\b", r"\bunaliv", r"\bkys\b(?=.*\b(?:myself|me|i)\b)",
        # Hinglish (matched on a letters-collapsed variant too: jeene/jine, mann/man)
        r"\bkhud\s*kushi\b", r"\bkhudkushi\b", r"\bkhud\s*khushi\b", r"\baa?tma?\s*hatya\b", r"\bsuside\b",
        r"\bmarna\s+chaht[aie]\b", r"\bmarn[ae]\s+(?:hai|h)\b", r"\b(?:mujhe|mai|main|me|mein)\s+(?:\w+\s+){0,2}marn[ae]\b",
        r"\bjaan\s+de\s+(dunga|dungi|du|dun)\b", r"\bapn[ei]\s+jaan\s+(?:de|le|lu|lun|dun|du)\b", r"\bmar\s+j[aou]+n?\b(?=\s*(?:ga|gi|chaht|ch[ae]h|hai|h\b|$|[.!,]))",
        r"\bmar\s+jaun\b", r"\bmar\s+jau\b", r"\bmar\s+jaaun\b", r"\bmar\s+jaon\b", r"\bmar\s+jan[ae]\s+(?:ch[ae]h|hai|h\b)",
        r"\bj[ei]+n[ei]?\s+(?:ka|ki|ke)\s+(?:(?:koi|bhi|ab|aur)\s+)*(?:mann?|mn|dil|ichh?a|icha|matlab|fayda|faida|maksad|maqsad|reason|wajah|point|raas)\s+(?:\w+\s+){0,2}(?:nahi|nhi|nhin|nai|na\s+rah)\b",
        r"\bj[ei]+n[aei]?\s+nahi\s+ch[ae]h?t", r"\bnahi\s+j[ei]+n[aei]?\s+ch[ae]h?t", r"\bj[ei]+n[aei]?\s+nahi\s+h[ae]i?\b",
        r"\bzind[ae]gi\s+(?:khatam|khtm|khatm|khtam|samapt)\b", r"\bkhatam\s+kar\s+(?:du|dun|dunga|dungi|lu|lun|lunga|lungi)\s+(?:apni|ye|yeh|sab|sb|zindagi|jaan)",
        r"\b(?:sab|sb|sabkuch|sabkush)\s+khatam\s+kar\s+(?:du|dun|dunga|dungi)\b", r"\bkhud\s*ko\s+(?:khatam|maar|nuksan|hurt|chot)\b",
        r"\bzind[ae]gi\s+se\s+thak\s+(?:gay[ae]|gayi|gaya)\b", r"\bthak\s+(?:gay[ae]|gayi|gaya)\s+(?:hu|hoon|hun)\s+(?:is\s+)?(?:zind[ae]gi|jeene)\b",
        r"\bzinda\s+(?:rehna|rahna)\s+nahi\b", r"\bjee\s+kar\s+kya\s+(?:karu|karunga|karungi)\b",
        # Devanagari (nukta and chandrabindu are folded before matching)
        r"आत्महत्या", r"आत्म\s*हत्या", r"खुद्?\s*कुशी", r"आत्मघात", r"खुदकुशी", r"खुद\s*कुशी", r"खुदखुशी", r"सुसाइड", r"सुइसाइड", r"सुसाईड",
        r"मरना\s+चाहत", r"मर\s+जाना\s+चाहत", r"मर\s+जाऊं", r"मर\s+जाऊ\b", r"मर\s+जाने\s+का\s+मन", r"मर\s+जाना\s+है", r"मरना\s+है",
        r"जान\s+दे\s+दूं", r"जान\s+दे\s+दूँ", r"जान\s+दे\s+दूंगी", r"जान\s+दे\s+दूंगा", r"अपनी\s+जान\s+(?:ले|दे)",
        r"जीना\s+नहीं\s+चाहत", r"जीने\s+का\s+(?:मन|दिल|कोई\s+मतलब|कोई\s+फ़?ायदा|कोई\s+फायदा)\s+(?:भी\s+)?(?:नहीं|नही)", r"जीने\s+की\s+(?:इच्छा|चाह)\s+(?:भी\s+)?(?:नहीं|नही)",
        r"जिंदगी\s+(?:खत्म|ख़त्म|खतम)", r"ज़िंदगी\s+(?:खत्म|खतम)", r"जिंदगी\s+से\s+थक", r"खुद\s+को\s+(?:खत्म|खतम|मार|नुकसान|चोट)",
        r"सब\s+(?:कुछ\s+)?(?:खत्म|खतम)\s+कर", r"जीवन\s+(?:समाप्त|खत्म|खतम)", r"जी\s+कर\s+क्या\s+करूं",
    )),
    ("medical_emergency", _rx(
        r"\bchest\s+pain\b", r"\bcan'?t\s+breathe\b", r"\b(heart\s+attack|stroke)\s+(now|right now|happening)\b",
        r"\boverdos", r"\bbleeding\s+(heavily|a lot|won'?t stop)\b", r"\bunconscious\b", r"\bseizure\b",
        r"\bpoison(ed|ing)\b", r"\bsaans\s+nahi\b", r"सीने\s+में\s+दर्द", r"सांस\s+नहीं", r"बेहोश",
    )),
    ("abuse", _rx(
        r"\b(he|she|they|husband|wife|partner|father|mother)\s+(hits|beats|hit|beat|abuses|chokes)\s+me\b",
        r"\bbeing\s+abused\b", r"\bdomestic\s+violence\b", r"\bmaarta\s+hai\b", r"\bmaarti\s+hai\b",
        r"मुझे\s+मारता", r"मुझे\s+मारती", r"घरेलू\s+हिंसा",
    )),
]

STATIC_REPLIES: dict[InputClass, dict[str, str]] = {
    "crisis": {
        "english": (
            "I'm really sorry you're feeling this way. You don't have to go through it alone, and "
            "talking to someone right now can help.\n\n"
            "In India, you can call Tele-MANAS on 14416 or 1-800-891-4416 (free, 24x7). "
            "If you are outside India, findahelpline.com lists free, confidential helplines in your country. "
            "If you are in immediate danger, please call 112 or your local emergency number.\n\n"
            "If you can, reach out to someone you trust and let them know how you're feeling."
        ),
        "hindi": (
            "मुझे बहुत दुख है कि आप ऐसा महसूस कर रहे हैं। आप अकेले नहीं हैं, और अभी किसी से बात करना मदद कर सकता है।\n\n"
            "भारत में Tele-MANAS को 14416 या 1-800-891-4416 पर कॉल करें (निःशुल्क, 24x7)। "
            "भारत से बाहर हों तो findahelpline.com पर अपने देश की हेल्पलाइन देखें। "
            "तत्काल ख़तरे में हों तो 112 पर कॉल करें।\n\n"
            "हो सके तो किसी भरोसेमंद व्यक्ति को बताएं कि आप कैसा महसूस कर रहे हैं।"
        ),
        "hinglish": (
            "Mujhe bahut dukh hai ki aap aisa feel kar rahe hain. Aap akele nahi hain, aur abhi kisi se baat karna madad kar sakta hai.\n\n"
            "India mein Tele-MANAS ko 14416 ya 1-800-891-4416 par call karein (free, 24x7). "
            "India ke bahar hon to findahelpline.com par apne desh ki helpline dekhein. "
            "Agar turant khatra ho to 112 par call karein.\n\n"
            "Ho sake to kisi bharosemand insaan ko batayein ki aap kaisa feel kar rahe hain."
        ),
    },
    "medical_emergency": {
        "english": ("This sounds like it could be a medical emergency. Please call 112 (India) or your local "
                    "emergency number now, or go to the nearest hospital. Astrology can wait; your safety comes first."),
        "hindi": "यह मेडिकल इमरजेंसी हो सकती है। कृपया अभी 112 पर कॉल करें या नज़दीकी अस्पताल जाएं। आपकी सुरक्षा सबसे पहले है।",
        "hinglish": "Yeh medical emergency ho sakti hai. Please abhi 112 par call karein ya nazdeeki hospital jaayein. Aapki safety sabse pehle hai.",
    },
    "abuse": {
        "english": ("I'm sorry you're dealing with this. No one deserves to be hurt. If you are in danger right now, "
                    "call 112. In India, the Women Helpline 181 offers support 24x7. "
                    "findahelpline.com lists confidential services in other countries."),
        "hindi": "मुझे दुख है कि आप इससे गुज़र रहे हैं। किसी को भी चोट पहुंचाना ठीक नहीं। ख़तरे में हों तो 112 पर कॉल करें। महिला हेल्पलाइन 181 (24x7) से भी मदद ले सकते हैं।",
        "hinglish": "Mujhe dukh hai ki aap isse guzar rahe hain. Kisi ko bhi chot pahunchana theek nahi. Khatre mein hon to 112 par call karein. Women Helpline 181 (24x7) se bhi madad le sakte hain.",
    },
}


_SQUASH = re.compile(r"killmyself|killingmyself|unalive|suicid|hangmyself|hurtmyself|harmmyself|selfharm|cutmywrist|slitmywrist|"
                     r"takemyownlife|sewerslid|khudkushi|atmahatya|aatmahatya|jeenekamannahi|jenekamannahi")


def classify_input(text: str) -> InputClass | None:
    variants = normalize_variants(text)
    for cls, pat in _INPUT_RULES:
        for v in variants:
            if v.startswith("\x00"):
                if cls == "crisis" and _SQUASH.search(v[1:]):
                    return cls
                continue
            if pat.search(v):
                return cls
    return None


# --- soft distress (hopelessness without an explicit self-harm phrase): the model must lead with care + resources ---
_DISTRESS = re.compile(
    r"\bhopeless(?:ness)?\b|\bworthless\b|\bno\s+point\s+(?:in\s+)?(?:anything|going\s+on|trying|living|life)\b|\bnothing\s+matters\b|"
    r"\bgive\s+up\s+on\s+(?:life|everything|myself)\b|\bcan'?t\s+(?:take|handle|cope)\s+(?:it|this|anything)\s+anymore\b|"
    r"\b(?:a\s+)?burden\s+(?:to|on|for)\s+(?:everyone|my\s+family|them|others)\b|\beveryone\s+(?:would\s+be\s+)?better\s+off\s+without\s+me\b|"
    r"\b(?:nobody|no\s+one)\s+(?:cares|would\s+(?:notice|miss))\b|\blife\s+(?:is\s+)?(?:pointless|meaningless)\b|"
    r"\bwhat'?s\s+the\s+point\s+of\s+(?:living|life|anything|it\s+all)\b|\bi\s*(?:feel|am|'m)\s+(?:completely\s+)?(?:broken|empty\s+inside|so\s+alone|trapped)\b|"
    r"\bkoi\s+fayd[ae]\s+nahi\s+(?:hai\s+)?(?:jeene|zindagi)\b|\bsab\s+bekaar\b|\bzind[ae]gi\s+bekaar\b|\bkisi\s+ko\s+meri\s+parwah\b|"
    r"\bbahut\s+(?:akela|akeli)\s+(?:hu|hoon|feel)\b|"
    r"निराश|हताश|कोई\s+फायदा\s+नहीं|सब\s+बेकार|ज़िंदगी\s+बेकार|जिंदगी\s+बेकार|अकेला\s+(?:महसूस|हूं|हूँ)|अकेली\s+(?:महसूस|हूं|हूँ)|"
    r"किसी\s+को\s+मेरी\s+परवाह|बोझ\s+(?:हूं|हूँ|बन)",
    re.I)


def distress_signals(text: str) -> bool:
    """Soft lexicon: hopelessness / isolation wording that is not an explicit self-harm phrase. Used to require that the
    model's reply carries empathy and the crisis resources instead of astrology predictions."""
    return any(_DISTRESS.search(v) for v in normalize_variants(text) if not v.startswith("\x00"))


CRISIS_RESOURCE = re.compile(r"14416|1-800-891-4416|findahelpline", re.I)


def has_crisis_resources(text: str) -> bool:
    return bool(CRISIS_RESOURCE.search(text or ""))


def static_reply(cls: InputClass, language: str) -> str:
    return STATIC_REPLIES[cls].get(language, STATIC_REPLIES[cls]["english"])


# ----------------------------------------------------------------------------- output

_FUTURE = r"(will|would|is going to|are going to|may|might|could|likely to|destined to)"
_OUTPUT_RULES: list[tuple[OutputClass, re.Pattern[str]]] = [
    ("death", _rx(
        rf"\b{_FUTURE}\s+(soon\s+)?(die|pass away|lose (his|her|their|your) life)\b",
        r"\b(time|timing|date|year|age)\s+of\s+(your\s+|his\s+|her\s+)?death\b",
        r"\b(?:your|his|her|their|my)\s+life\s*span\s+(?:is|will|would|looks|ends|shows|indicates)\b",
        r"\b(fatal|deadly)\s+accident\b", r"\bdeath\s+(in|by|around|before)\s+(19|20)\d{2}\b",
        r"\bshort\s+life\b", r"\bearly\s+death\b", r"मृत्यु\s+(होगी|हो\s+जाएगी)", r"मौत\s+(होगी|हो\s+जाएगी)",
        r"\bmaut\s+ho(gi|\s+jayegi)\b",
    )),
    ("child_sex", _rx(
        r"\b(baby|child|fetus|foetus|unborn)\b.{0,40}\b(will be|is going to be|likely to be|is)\s+(a\s+)?(boy|girl|male|female|son|daughter)\b",
        r"\b(sex|gender)\s+of\s+(the|your|her)\s+(baby|child|unborn|fetus|foetus)\s+(is|will)\b",
        r"\bconceive\b.{0,40}\b(for|to have)\s+a\s+(boy|son|girl|daughter)\b",
        r"लड़का\s+होगा", r"लड़की\s+होगी", r"\bladka\s+hoga\b", r"\bladki\s+hogi\b",
    )),
    ("medical_legal_financial", _rx(
        r"\b(stop|start|increase|reduce|skip)\s+(taking\s+)?(your\s+)?(medication|medicine|tablets|insulin|dose)\b",
        r"\b\d+\s*mg\b", r"\byou\s+(have|are suffering from)\s+(cancer|diabetes|depression|a tumou?r)\b",
        r"\b(buy|sell|short)\s+(shares|stocks?|crypto|bitcoin|gold)\s+(on|before|after|now|by)\b",
        r"\b(you will|you'll)\s+win\s+(the|your)\s+(case|lawsuit)\b",
    )),
    ("paid_remedy", _rx(
        r"\b(buy|purchase|order|wear|get)\b.{0,30}\b(gemstone|gem|ruby|emerald|sapphire|neelam|pukhraj|panna|manik|moonga|coral|hessonite|gomed|cat'?s eye|rudraksha)\b",
        r"\b(book|pay for|sponsor)\s+(a\s+)?(puja|pooja|havan|homa|yagna|ritual)\b",
        r"\b(consult|book|pay)\s+(an?\s+)?(astrologer|pandit|jyotishi)\b",
    )),
    ("caste", _rx(r"\b(brahmin|brahman|kshatriya|vaishya|shudra|sudra|caste|dalit)\b",
                 # Hinglish "jati hai" / "chali jati" is the verb "goes": only the caste noun in caste contexts counts
                 r"\bj[a]+ti\s+(?:system|vyavastha|bhed|bhedbhav|ke\s+(?:aadhar|adhar|hisaab)|wala|wali)\b", r"\bnich(?:i)?\s+jati\b",
                 r"जाति(?!\s+है|\s+हैं)")),
    ("leak", _rx(
        r"\bsystem\s+prompt\b", r"\bas per (my|the) (guidelines|instructions|rules|programming)\b",
        r"\b(my|these|the) (guidelines|instructions)\s+(say|state|require|tell|are)\b",
        r"\bI(?:'m| am) (programmed|instructed|required) to\b", r"\bCHART FACTS\b", r"\bREFERENCE NOTES\b", r"\b(my|these)\s+instructions\s+(say|are|tell)\b",
        r"\[(?:N|A|T|V|VN|Y|D|P|META)\.[A-Z0-9_.]+\]", r"(?<![\w.])(?:VN|META)\.[A-Z][A-Z0-9_.]+",
        r"(?<![\w.])[NATVYDP]\.[A-Z]{2,}(?:\.[A-Z0-9_]+)+",
    )),
    ("fatalism", _rx(
        r"\b(doomed|cursed|curse on you|no escape|nothing can be done|can never (marry|succeed|be happy))\b",
        r"\b(dosha|sade sati|kaal sarp|manglik)\b.{0,60}\b(will (ruin|destroy)|means? (divorce|death|failure))\b",
    )),
]

CANNED_OUTPUT: dict[OutputClass, str] = {
    "death": ("Astrology can't and shouldn't predict death or lifespan. If health is on your mind, this period "
              "is best used for care and routine check-ins with a doctor. I'm happy to look at what your chart "
              "suggests about wellbeing and balance instead."),
    "child_sex": ("I can't predict or advise on the sex of a child. I'd be glad to talk about what your chart "
                  "suggests about family life and this phase more generally."),
    "medical_legal_financial": ("I can't give medical, legal or investment advice; a qualified professional is "
                                "the right person for that. I can share what your chart suggests about the broader "
                                "themes of this period, if that helps."),
    "paid_remedy": ("You don't need to buy anything. If you'd like to work with this period, simple free practices "
                    "such as a steady routine, reflection, or a short daily mantra are optional traditions some people find grounding."),
    "caste": "I describe compatibility in terms of temperament and values, not caste or community.",
    "leak": "I can't share how I'm set up internally, but I'm happy to keep exploring your chart with you.",
    "fatalism": ("No single placement or dosha decides a life. Traditional texts list many cancellations, and your "
                 "choices matter. Let's look at what supports you in this period."),
}


@dataclass(frozen=True)
class SafetyHit:
    cls: OutputClass
    match: str


def scan_output(text: str) -> list[SafetyHit]:
    hits = []
    for cls, pat in _OUTPUT_RULES:
        m = pat.search(text)
        if m:
            hits.append(SafetyHit(cls, m.group(0)[:80]))
    return hits


def canned_output(cls: str, language: str = "english") -> str:
    """Fixed reply for a violated output class. "crisis" (a distressed question whose reply lacked the resources)
    returns the static crisis reply in the user's language."""
    if cls == "crisis":
        return static_reply("crisis", language)  # type: ignore[arg-type]
    return CANNED_OUTPUT[cls]  # type: ignore[index]
