"""Safety policy (llm-integration.md §8, ai_llm_rules §8).

- Input pre-filter: rule-based, multilingual. Crisis / medical emergency / abuse skip the
  LLM entirely and return a STATIC, pre-written reply (never improvised by a model).
- Output filter: forbidden classes checked on every model answer. A hit triggers one
  repair; a second hit returns the canned reply for that class.
"""

from __future__ import annotations

import re
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


_INPUT_RULES: list[tuple[InputClass, re.Pattern[str]]] = [
    ("crisis", _rx(
        r"\b(kill|hurt|harm)\s+(myself|me)\b", r"\bsuicid", r"\bend\s+(my|it)\s+(life|all)\b",
        r"\bwant\s+to\s+die\b", r"\bdon'?t\s+want\s+to\s+(live|be\s+alive)\b", r"\bno\s+reason\s+to\s+live\b",
        r"\bself[-\s]?harm", r"\bcut(ting)?\s+myself\b", r"\bkhud\s*kushi\b", r"\bkhudkushi\b",
        r"\bmarna\s+chaht[aie]\b", r"\bjaan\s+de\s+(dunga|dungi|du)\b", r"\bmar\s+jaun\b",
        r"आत्महत्या", r"ख़ुदकुशी", r"खुदकुशी", r"मरना\s+चाहत", r"जान\s+दे\s+दूं", r"जीना\s+नहीं\s+चाहत",
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


def classify_input(text: str) -> InputClass | None:
    for cls, pat in _INPUT_RULES:
        if pat.search(text):
            return cls
    return None


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
    ("caste", _rx(r"\b(brahmin|brahman|kshatriya|vaishya|shudra|sudra|caste|jati|dalit)\b", r"जाति")),
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


def canned_output(cls: OutputClass) -> str:
    return CANNED_OUTPUT[cls]
