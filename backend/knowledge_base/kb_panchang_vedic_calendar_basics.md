---
title: "Vedic (Hindu) Calendar Basics: Months, Samvat, Sankranti and Astronomical Festivals"
tradition: vedic
system: vedic
tier: 2
language: en
sources:
  - "Sewell & Dikshit, The Indian Calendar (1896, public domain; archive.org/details/indiancalendarwi00sewerich): tithi, paksha, sunrise day, eras, solar and lunar years"
  - "https://www.muhuratam.in/blog/amanta-vs-purnimanta and https://www.myzodiaq.in/en/online-library/panchang/regional-panchang/north-vs-south-indian-panchang-core-differences-and-understanding"
  - "https://en.wikipedia.org/wiki/Vikram_Samvat, https://en.wikipedia.org/wiki/Hindu_calendar, https://en.wikipedia.org/wiki/Indian_New_Year%27s_days (orientation)"
  - "https://shivallibrahmins.com/articles/adhika-masa/ (Adhika masa)"
confidence: medium
school_notes: "Calendars differ by region: North India mostly purnimanta; Maharashtra, Gujarat, Karnataka, Andhra and Telangana amanta; Tamil, Malayalam, Bengali and Odia calendars are solar. Vikram Samvat begins in Chaitra in much of North India but in Kartika in Gujarat. Sidereal (Lahiri/Chitrapaksha) conventions are standard for the Indian national calendar; some almanacs use other ayanamsas and can differ by a day on tithi or sankranti dates."
---

# Vedic (Hindu) Calendar Basics

The Hindu calendar is **luni-solar**: months follow the Moon's phases, but a leap-month rule keeps the year aligned with the Sun and seasons. Some regional calendars are purely **solar**. Everything is calculated on the **sidereal** zodiac, which is why Indian dates of "Sun entering Aries" fall around 14 April, not 21 March.

## Day, week and the sunrise rule

The **civil day starts at sunrise**, not midnight. The tithi (and nakshatra, yoga, karana) in force at local sunrise names that day; weekday runs sunrise to sunrise. Sewell and Dikshit give the classic illustration: a religious act prescribed for a particular tithi is performed on the day on which that tithi is current at a defined point of the day (sunrise, noon, afternoon or night depending on the rite). That is why a festival can fall on a different date in different cities, and why two sunrises can find the same tithi twice or a tithi can be skipped.

## Solar and lunar months

**Solar months (saura masa):** the twelve signs, each month starting at the **Sankranti** (the Sun's ingress to a new sidereal sign). Names follow the sign: Mesha, Vrishabha, Mithuna, Karka, Simha, Kanya, Tula, Vrischika, Dhanu, Makara, Kumbha, Meena. Used as the main calendar in Tamil Nadu, Kerala, Bengal, Odisha and Assam. A solar month lasts about 29.4 to 31.5 days.

**Lunar months (chandra masa):** twelve months from new moon to new moon (about 29.53 days), named after the nakshatra near which the full moon falls: **Chaitra, Vaishakha, Jyeshtha, Ashadha, Shravana, Bhadrapada, Ashvina, Kartika, Margashirsha, Pausha, Magha, Phalguna**. A lunar year is about 354 days; the gap to the solar year of about 365.25 days is closed by the Adhika masa.

**Adhika (intercalary) masa:** a lunar month in which the Sun does not enter a new sign gets a repeated name and is called Adhika (it is also known as Mala or Purushottama masa); it occurs about every 32.5 months. Rarely, a lunar month holding two sankrantis is suppressed (Kshaya masa). See `kb_panchang_muhurta_basics.md` for how these affect ritual timing.

## Amanta vs Purnimanta

The two systems differ in **where the month ends**:

- **Amanta:** the month ends at the new moon (Amavasya). Shukla paksha comes first, then Krishna. Followed in most of South and West India: Maharashtra, Gujarat, Karnataka, Andhra Pradesh, Telangana, Goa.
- **Purnimanta:** the month ends at the full moon (Purnima). Krishna paksha comes first, then Shukla. Followed in most of North India.

**Consequence:** The bright half (Shukla) always has the same month name in both. The **dark half (Krishna paksha) carries a different name**: the Krishna paksha that the amanta calendar calls "Ashvina Krishna" (before Diwali's Amavasya, the Ashvina new moon) is called "Kartika Krishna" by purnimanta calendars. Many festivals (Diwali's Amavasya, Mahashivaratri on Krishna Chaturdashi) are therefore given different month names in different regions even though they fall on the same day. Same date, same tithi: only the month label differs. Software should store the system used.

## Eras (Samvat)

- **Vikram Samvat:** traditionally from 57 BCE; in 2026 the year numbers are in the 2080s (about 56 or 57 years ahead of the Gregorian year). In much of North and Central India the year begins on **Chaitra Shukla Pratipada**; in Gujarat the new year is the day after Diwali, **Kartika Shukla Pratipada**.
- **Shaka Samvat:** traditionally from 78 CE (the Indian national calendar, adopted 1957, counts Shaka years and begins on Chaitra 1, usually 22 March); in 2026 the year numbers are in the 1940s.
- **Kali Yuga era:** counted from 3102 BCE, used in traditional almanacs and ritual statements (sankalpa).
- **Samvatsara (Jovian) names:** a cycle of 60 named years linked to Jupiter's motion (Prabhava, Vibhava, ...). Regional almanacs name each year; different reckonings (the north Indian Brihaspati cycle and the southern solar cycle) can differ by a year in some places.

## Sankranti

**Sankranti** = the Sun's ingress into a sign. Twelve per year. The key ones:

- **Makara Sankranti** (about 14 to 15 January): the Sun enters sidereal Capricorn and the **Uttarayana** (northward course) period traditionally begins; celebrated as Pongal, Lohri, Magha Bihu and Makar Sankranti in various regions.
- **Mesha Sankranti** (about 13 to 14 April): solar new year in several regions (Vaisakhi, Puthandu, Pohela Boishakh, Bihu, Vishu in Kerala is observed by a slightly different convention).
- **Karka Sankranti** (about 16 July): the start of **Dakshinayana** (southward course).
- **Tula Sankranti** (about 17 October) and **Vrishchika Sankranti** (about 16 November), and **Dhanu Sankranti** (about 16 December), after which the Kharmas period traditionally pauses weddings in North India.

Sankranti dates drift later in the Gregorian calendar by about one day every 70 years or so, because the Hindu solar calendar follows the sidereal year (about 365.2564 days) while the Gregorian calendar follows the tropical year (about 365.2425 days); equivalently the ayanamsa grows about 50 arc-seconds a year. Different conventions about "which side of sunrise or midnight" the ingress falls also shift the observed day.

## Major astronomically tied festivals (brief)

- **Makara Sankranti (Jan):** Sun's ingress to Makara, start of Uttarayana.
- **Maha Shivaratri (Magha/Phalguna Krishna Chaturdashi; Feb/Mar):** night of the Krishna Chaturdashi; ritual vigil.
- **Holi (Phalguna Purnima; Mar):** full moon at the end of the lunar year in the purnimanta reckoning.
- **Ugadi/Gudi Padwa/Chaitra Navratri start (Chaitra Shukla Pratipada; Mar/Apr):** new lunar year for amanta regions and Vikram Samvat in North India.
- **Ram Navami (Chaitra Shukla Navami), Hanuman Jayanti (Chaitra Purnima in many traditions), Akshaya Tritiya (Vaishakha Shukla Tritiya).**
- **Guru Purnima (Ashadha Purnima), Raksha Bandhan (Shravana Purnima), Krishna Janmashtami (Shravana/Bhadrapada Krishna Ashtami), Ganesh Chaturthi (Bhadrapada Shukla Chaturthi).**
- **Navaratri and Vijayadashami/Dussehra (Ashvina Shukla 1 to 10).**
- **Diwali (Ashvina/Kartika Amavasya):** the new moon at the Ashvina-Kartika junction (the month name depends on amanta/purnimanta reckoning).
- **Kartika Purnima / Dev Diwali; Prabodhini (Devutthani) Ekadashi (Kartika Shukla 11):** end of Chaturmas.

Dates move across the Gregorian calendar by several days to a month from year to year because the festivals follow tithis, not Gregorian dates; in a year with an Adhika masa the shift is larger.

## What software should store

- The ayanamsa and the rule for sunrise.
- Amanta vs purnimanta choice (and Gujarat's Kartika year start if offered).
- The Samvat label chosen (Vikram, Shaka).
- The location and time zone, since tithi/sunrise assignment depends on place.
- A note that a "festival date" can differ by one day between cities and between almanacs, which is normal rather than an error.
