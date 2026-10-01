"""Nakshatras (spec section 2.3). 27 x 13deg20', pada = 3deg20'."""

from __future__ import annotations

from typing import Final, NamedTuple


class Nakshatra(NamedTuple):
    name: str
    lord: str
    deity: str
    symbol: str
    nature: str  # English part only (spec 2.3)
    gana: str
    nadi: str
    yoni: str
    yoni_male: bool


_M, _F = True, False

NAKSHATRAS: Final = (
    Nakshatra("Ashwini", "Ketu", "Ashwini Kumaras", "Horse's head", "Swift", "Deva", "Adi", "Horse", _M),
    Nakshatra("Bharani", "Venus", "Yama", "Yoni", "Fierce", "Manushya", "Madhya", "Elephant", _M),
    Nakshatra("Krittika", "Sun", "Agni", "Razor / flame", "Mixed", "Rakshasa", "Antya", "Sheep", _F),
    Nakshatra("Rohini", "Moon", "Brahma (Prajapati)", "Chariot", "Fixed", "Manushya", "Antya", "Serpent", _M),
    Nakshatra("Mrigashira", "Mars", "Soma", "Deer's head", "Soft", "Deva", "Madhya", "Serpent", _F),
    Nakshatra("Ardra", "Rahu", "Rudra", "Teardrop", "Sharp", "Manushya", "Adi", "Dog", _F),
    Nakshatra("Punarvasu", "Jupiter", "Aditi", "Quiver of arrows", "Movable", "Deva", "Adi", "Cat", _F),
    Nakshatra("Pushya", "Saturn", "Brihaspati", "Cow's udder", "Swift", "Deva", "Madhya", "Sheep", _M),
    Nakshatra("Ashlesha", "Mercury", "Nagas", "Coiled serpent", "Sharp", "Rakshasa", "Antya", "Cat", _M),
    Nakshatra("Magha", "Ketu", "Pitris", "Throne", "Fierce", "Rakshasa", "Antya", "Rat", _M),
    Nakshatra("Purva Phalguni", "Venus", "Bhaga", "Front legs of a bed", "Fierce", "Manushya", "Madhya", "Rat", _F),
    Nakshatra("Uttara Phalguni", "Sun", "Aryaman", "Back legs of a bed", "Fixed", "Manushya", "Adi", "Cow", _M),
    Nakshatra("Hasta", "Moon", "Savitar", "Hand", "Swift", "Deva", "Adi", "Buffalo", _F),
    Nakshatra("Chitra", "Mars", "Vishwakarma", "Bright jewel", "Soft", "Rakshasa", "Madhya", "Tiger", _F),
    Nakshatra("Swati", "Rahu", "Vayu", "Young shoot in the wind", "Movable", "Deva", "Antya", "Buffalo", _M),
    Nakshatra("Vishakha", "Jupiter", "Indra-Agni", "Triumphal arch", "Mixed", "Rakshasa", "Antya", "Tiger", _M),
    Nakshatra("Anuradha", "Saturn", "Mitra", "Lotus", "Soft", "Deva", "Madhya", "Deer", _F),
    Nakshatra("Jyeshtha", "Mercury", "Indra", "Earring / umbrella", "Sharp", "Rakshasa", "Adi", "Deer", _M),
    Nakshatra("Mula", "Ketu", "Nirriti", "Bundle of roots", "Sharp", "Rakshasa", "Adi", "Dog", _M),
    Nakshatra("Purva Ashadha", "Venus", "Apas", "Elephant tusk / fan", "Fierce", "Manushya", "Madhya", "Monkey", _M),
    Nakshatra("Uttara Ashadha", "Sun", "Vishvedevas", "Planks of a bed", "Fixed", "Manushya", "Antya", "Mongoose", _M),
    Nakshatra("Shravana", "Moon", "Vishnu", "Ear / three footprints", "Movable", "Deva", "Antya", "Monkey", _F),
    Nakshatra("Dhanishta", "Mars", "Eight Vasus", "Drum", "Movable", "Rakshasa", "Madhya", "Lion", _F),
    Nakshatra("Shatabhisha", "Rahu", "Varuna", "Empty circle", "Movable", "Rakshasa", "Adi", "Horse", _F),
    Nakshatra("Purva Bhadrapada", "Jupiter", "Aja Ekapada", "Front of a funeral cot / swords", "Fierce", "Manushya", "Adi", "Lion", _M),
    Nakshatra("Uttara Bhadrapada", "Saturn", "Ahir Budhnya", "Back of a funeral cot / twins", "Fixed", "Manushya", "Madhya", "Cow", _F),
    Nakshatra("Revati", "Mercury", "Pushan", "Fish / drum", "Soft", "Deva", "Antya", "Elephant", _F),
)

NAKSHATRA_SPAN: Final = 40.0 / 3.0  # 13deg20'
PADA_SPAN: Final = 10.0 / 3.0       # 3deg20'
