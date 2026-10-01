---
title: "Vimshottari Dasha — Foundations, Calculation and Reading"
tradition: vedic
system: vedic
tier: 2
language: en
sources:
  - "https://jagannathhora.com/vimshottari-mahadasha-calculation-step-by-step/"
  - "https://www.myzodiaq.in/en/online-library/panchang/vimshottari-and-yogini/calculating-vimshottari-dasha-the-120-year-roadmap-of-your-life"
  - "https://srath.com/jyoti%E1%B9%A3a/dasa/vimshottari-dasha-2/"
  - "https://en.wikipedia.org/wiki/Dasha_(astrology) (orientation only)"
  - "Brihat Jataka of Varahamihira, tr. Swami Vijnananda, archive.org BrihatJatakaOfVarahamihiraBySwamiVijnananda (public domain translator's notes on Ashtottari and on non-Vimshottari dasa logic)"
  - "Brihat Parashara Hora Shastra (Vimshottari chapters) via the secondary summaries above"
confidence: high
school_notes: "The 120-year sequence and the nakshatra-to-lord mapping are universal within Parashari practice. Schools differ on (1) the length of the year used to convert dasha years into calendar dates (365.25 days, 365.2422 days, or the 360-day savana year), (2) whether the dasha starts from the Moon's nakshatra position or, in rare variants, from other reference points, and (3) the ayanamsa used (Lahiri is the dominant default), which can shift the Moon's nakshatra position and so the whole timeline."
---

# Vimshottari Dasha — Foundations

## What the system is

**Vimshottari** (Sanskrit for "one hundred and twenty") is a nakshatra-based planetary period system. It divides a notional 120-year human life into nine consecutive **Mahadashas** (major periods), each ruled by one of nine grahas (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu). It is by far the most used timing system in Parashari (BPHS) astrology, and the one used in Nakshion.

The idea is simple: at birth, the Moon sits in one of 27 nakshatras. That nakshatra's ruling planet is the first Mahadasha lord, and the portion of the nakshatra the Moon has not yet crossed determines how much of that first period remains. After it, the other Mahadashas follow in a fixed order. Dashas describe *which planetary themes are being emphasised*, and work together with transits (gochara); they are not a stand-alone prediction machine.

## The order and years

The fixed sequence and durations are:

| Order | Lord | Years |
|---|---|---|
| 1 | Ketu | 7 |
| 2 | Venus | 20 |
| 3 | Sun | 6 |
| 4 | Moon | 10 |
| 5 | Mars | 7 |
| 6 | Rahu | 18 |
| 7 | Jupiter | 16 |
| 8 | Saturn | 19 |
| 9 | Mercury | 17 |

The total is 7 + 20 + 6 + 10 + 7 + 18 + 16 + 19 + 17 = 120 years. The cycle repeats if a life extends beyond 120 years, though in practice charts use the dashas that fall within a lifetime. A person is always inside exactly one Mahadasha, one Antardasha and one Pratyantardasha at a time.

## Nakshatra-to-lord mapping

The 27 nakshatras (each 13 degrees 20 minutes of the zodiac) are assigned to the nine lords in the dasha order, repeating three times:

- **Ketu:** Ashwini, Magha, Mula
- **Venus:** Bharani, Purva Phalguni, Purva Ashadha
- **Sun:** Krittika, Uttara Phalguni, Uttara Ashadha
- **Moon:** Rohini, Hasta, Shravana
- **Mars:** Mrigashira, Chitra, Dhanishtha
- **Rahu:** Ardra, Swati, Shatabhisha
- **Jupiter:** Punarvasu, Vishakha, Purva Bhadrapada
- **Saturn:** Pushya, Anuradha, Uttara Bhadrapada
- **Mercury:** Ashlesha, Jyeshtha, Revati

A convenient formula: with Ashwini as 1, the lord index (0-8, in the order above) is (nakshatra number - 1) mod 9.

## Balance of the first dasha at birth

The Moon's sidereal longitude (in the system used, normally Lahiri) is converted to a nakshatra and the fraction of that nakshatra already travelled:

1. nakshatra index = floor(Moon longitude / 13.3333 degrees)
2. fraction elapsed = (longitude mod 13.3333) / 13.3333
3. first Mahadasha lord = lord of that nakshatra
4. balance at birth = (1 - fraction elapsed) x full years of that lord

**Worked example.** Suppose the sidereal Moon is at 50.0 degrees (20 degrees Taurus). 50 / 13.3333 = 3.75, so the Moon is in the 4th nakshatra, Rohini (lord: Moon, 10 years), and 75 percent of Rohini has passed. Balance = 0.25 x 10 = 2.5 years of Moon Mahadasha remaining at birth. After it come Mars (7), Rahu (18), Jupiter (16) and so on.

The elapsed part of the first dasha is simply "used up" before birth; the person starts life in the middle of it. Because the Moon moves about 13 degrees per day, a few hours of birth-time error can move the balance by several months, and a wrong date can change the first lord entirely. Where the birth time is unknown, nakshatra and first-dasha reliability are limited whenever the Moon is near a nakshatra boundary.

## Antardasha proportions

Each Mahadasha is split among the nine planets in proportion to their own Vimshottari years, starting with the Mahadasha lord itself:

Antardasha length = Mahadasha years x sub-lord years / 120 (in years)

A handy equivalent: in months, Antardasha length = (MD years x AD years) / 10. For example, Jupiter-Saturn is 16 x 19 / 10 = 30.4 months. The nine sub-periods always add up to the Mahadasha length.

## Pratyantardasha proportions

Each Antardasha is split again by the same rule, starting from the Antardasha lord:

Pratyantar length = Antardasha length x sub-sub-lord years / 120

Example: a 30.4 month Jupiter-Saturn Antardasha has a Jupiter Pratyantar of 30.4 x 16 / 120, about 4.05 months. Further levels (Sookshma, Prana) exist but are rarely used in reading charts, because birth-time uncertainty makes them unreliable.

## Calendar-year convention

Dasha years are converted to dates using a year length. Common choices: 365.25 days (Julian), 365.2422 days (tropical), or 360 days (a "savana" year, favoured in some traditional computations). Over a lifetime these differ by months, so a software implementation must state its choice and keep it consistent. Do not mix conventions when comparing two reports.

## Reading a dasha with chart context

A Mahadasha lord does not deliver "its" generic results. Classical commentators and modern practitioners judge it by chart-specific factors:

**1. Houses ruled (lordship).** The houses the lord rules for that Lagna set the life areas stressed. A lord of the 10th will emphasise career; of the 5th, creativity, children, study. Kendra and trikona lordship is generally supportive; 6, 8, 12 lordship tends to bring challenge and adjustment.

**2. House occupied.** Where the lord sits shows the arena in which it works. Placement in kendras (1,4,7,10) and trikonas (1,5,9) is considered favourable; in 6, 8, 12 it points to effort, transformation or retreat.

**3. Dignity and strength.** A planet in its sign of exaltation, own sign or moolatrikona is traditionally stronger and gives its results more cleanly. A debilitated or heavily afflicted planet gives them with difficulty, though cancellations (neecha bhanga) are noted by many schools.

**4. Nakshatra of the lord.** The star the dasha lord occupies, and that star's own lord, add a second layer: results are coloured by the nakshatra lord's house and condition. Some traditions treat the nakshatra lord as an equally important "carrier" of the dasha.

**5. Relationship to the Moon and Lagna.** Many astrologers read the dasha from both the Lagna and the Moon (Chandra Lagna). A dasha lord that is a friend of the Lagna lord, or that sits in a good house from the Moon, is read more favourably. Natural friend/enemy status between the dasha lord and the Lagna lord or Moon also matters.

**6. Aspects and conjunctions.** Benefic aspects (such as Jupiter's) soften; close malefic association sharpens. A dasha lord conjunct another planet also "delivers" part of that planet's themes.

**7. Rahu and Ketu.** These have no ownership in the Parashari scheme (BPHS gives conditional rulership in some commentaries). They are judged by the sign they sit in, its lord (dispositor), and the planets they conjoin. Many practitioners say they act like the planet that owns their sign.

**8. Divisional charts.** The Navamsa and, for specific themes, other vargas are consulted to confirm whether the promise of the birth chart can be fulfilled.

**9. Transit overlay.** A dasha shows the theme; gochara and Ashtakavarga indicate when within the dasha it becomes active. See `kb_dasha_gochara_and_dasha_interplay.md`.

## Constructive interpretation guidelines

A well-grounded dasha reading should:

- Describe the *themes in play* (career focus, learning, inward turning, relationships) and their typical rhythm, not predict specific events.
- Offer both opportunities and cautions, and name practical responses (planning, study, health routines, therapy where appropriate).
- Avoid claiming outcomes about health, legal matters or money. Where a period is traditionally called demanding, frame it as a time that asks for patience, preparation and support.
- Remember that the chart is one input among many in a person's real life.

## Historical note

Vimshottari is attributed to Parashara. Varahamihira's Brihat Jataka (6th century CE) describes a different "dasa" logic in which periods are assigned to planets according to their strength and their houses relative to the lagna, Sun or Moon, with sub-periods set by the sub-lord's position from the dasha lord. This shows that Vimshottari was not the only classical approach; it became dominant later. The Vijnananda translation carries a translator's note describing the Ashtottari (108-year) system as an alternative; see `kb_dasha_alternative_systems.md`.
