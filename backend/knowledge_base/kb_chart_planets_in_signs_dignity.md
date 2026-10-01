---
title: "Planetary Dignity, Friendship, Combustion, Retrogression and Avasthas (with degree tables)"
tradition: "Jyotish (Parashari) with Varahamihira / Jataka Parijata cross-checks"
system: vedic
tier: 2
language: en
sources:
  - "Jataka Parijata (Vaidyanatha), tr. V. Subrahmanya Sastri 1932, ch. 2 - archive.org/details/JatakaParijata1932 (moolatrikona/exaltation passage read directly)"
  - "BPHS chapters 3 and 7 as summarised at indianastrologysoftware.com/the-power-of-moola-trikona, vedicka.com, astrocalc.in/learn/friendships"
  - "Combustion orbs: jagannathhora.com/retrograde-and-combust-planets-birth-chart, ournakshatra.com, glama.ai Vedaksha compute_combustion"
  - "Pushkara data: komilla.com, vijayalur.com, jyotishabharati.com notes"
  - "Engine tables: backend/app/astrology/data/grahas.py"
confidence: medium
school_notes: "Exaltation/debilitation degrees are uncontested for the seven planets. Moolatrikona degree ranges differ between BPHS and Varahamihira/Jataka Parijata for Mercury and probably Venus; node dignities differ widely. Both positions are recorded."
---

# Planetary Dignity, Friendship, Combustion and Related Tables

Dignity (the quality of a planet's placement) is the first filter in reading any planet. The tables below give the actual degrees the engine and classical texts use. All longitudes are sidereal, counted within a sign (0 to 30 degrees).

## Exaltation and debilitation (uccha / neecha)

| Planet | Exaltation sign | Peak degree | Debilitation sign | Deepest degree |
|---|---|---|---|---|
| Sun | Aries | 10 | Libra | 10 |
| Moon | Taurus | 3 | Scorpio | 3 |
| Mars | Capricorn | 28 | Cancer | 28 |
| Mercury | Virgo | 15 | Pisces | 15 |
| Jupiter | Cancer | 5 | Capricorn | 5 |
| Venus | Pisces | 27 | Virgo | 27 |
| Saturn | Libra | 20 | Aries | 20 |

The debilitation point is exactly 180 degrees from the exaltation point. A planet loses or gains strength gradually as it moves away from the peak; the whole sign is considered "exalted" in practice, with the peak degree the strongest. The classical sage-sequence is: exaltation, moolatrikona, own sign, friend, neutral, enemy, debilitation.

**Nodes (contested).** The engine default is Rahu exalted in Taurus and debilitated in Scorpio, Ketu the reverse. Other schools use Rahu exalted in Gemini (debilitated in Sagittarius), and a few use Virgo/Pisces. Jataka Parijata, as read here, gives Gemini as exaltation sign for Rahu and Virgo as own sign, with Kumbha (Aquarius) as moolatrikona. Both positions are in use; neither should be stated as the single fact. Modern teachers also assign Rahu the co-lordship of Aquarius and Ketu of Scorpio; the engine assigns nodes no own signs.

## Own signs (swakshetra)

Sun Leo; Moon Cancer; Mars Aries and Scorpio; Mercury Gemini and Virgo; Jupiter Sagittarius and Pisces; Venus Taurus and Libra; Saturn Capricorn and Aquarius.

## Moolatrikona (root-triangle) ranges

Moolatrikona is a special stretch inside a sign (always one of the planet's signs, or the exaltation sign for the Moon). A planet in its moolatrikona is read as stronger than in plain own sign but slightly below exaltation.

| Planet | Sign | Engine / BPHS-summary degrees | Other recorded variants |
|---|---|---|---|
| Sun | Leo | 0 to 20 | none noted |
| Moon | Taurus | 3 to 30 (engine, Jataka Parijata); BPHS summaries also give 4 to 30 | Taurus 4-20 is also quoted |
| Mars | Aries | 0 to 12 | none noted |
| Mercury | Virgo | 15 to 20 (engine); BPHS summaries cite 16 to 20 | Jataka Parijata: first 15 degrees exaltation, next 10 degrees (15 to 25) moolatrikona, last 5 own |
| Jupiter | Sagittarius | 0 to 10 | none noted |
| Venus | Libra | 0 to 15 (engine) | Jataka Parijata gives a single shared range for Venus, Saturn, Sun and Jupiter (OCR unclear; likely 10 or 20 degrees) [unverified] |
| Saturn | Aquarius | 0 to 20 | none noted |

The rest of each sign after the moolatrikona stretch counts as plain own sign. For the Moon, the first 3 degrees of Taurus count as exaltation, the rest as moolatrikona. Rahu is assigned Aquarius moolatrikona in Jataka Parijata and in some schools; the engine has none.

## Natural friendships (naisargika maitri)

From Parashara, a planet's relationship to each of the others (permanent):

| Planet | Friends | Neutral | Enemies |
|---|---|---|---|
| Sun | Moon, Mars, Jupiter | Mercury | Venus, Saturn |
| Moon | Sun, Mercury | Mars, Jupiter, Venus, Saturn | none |
| Mars | Sun, Moon, Jupiter | Venus, Saturn | Mercury |
| Mercury | Sun, Venus | Mars, Jupiter, Saturn | Moon |
| Jupiter | Sun, Moon, Mars | Saturn | Mercury, Venus |
| Venus | Mercury, Saturn | Mars, Jupiter | Sun, Moon |
| Saturn | Mercury, Venus | Jupiter | Sun, Moon, Mars |

Notable asymmetries: the Moon regards Mercury as a friend, while Mercury regards the Moon as an enemy. The relationship is read from the viewpoint of the planet whose placement is being judged. Nodes: the engine treats Rahu like Saturn and Ketu like Mars; other teachers say Rahu is friendly to Mercury, Venus and Saturn and hostile to the Sun, Moon and Mars, with Ketu the same or reversed. [school difference]

## Temporary friendships (tatkalika maitri) and compound relationship

A planet is a temporary friend of another if it lies in the 2nd, 3rd, 4th, 10th, 11th or 12th sign from it; otherwise (1st, 5th, 6th, 7th, 8th, 9th from it) a temporary enemy. Combining with the natural relationship gives five grades (panchadha maitri):

| Natural | Temporary | Compound |
|---|---|---|
| friend | friend | great friend (adhi mitra) |
| friend | enemy | neutral |
| neutral | friend | friend |
| neutral | enemy | enemy |
| enemy | friend | neutral |
| enemy | enemy | great enemy (adhi shatru) |

The engine's dignity labels use the natural table plus dignity signs; the compound grade is a refinement used mainly in Shadbala and detailed reading.

## Combustion (asta)

A planet very close to the Sun is "burnt". Its significations are felt less independently and often tied to ego, authority or the father. Orbs in degrees (engine, widely cited as BPHS values):

| Planet | Direct | Retrograde |
|---|---|---|
| Moon | 12 | 12 |
| Mars | 17 | 17 |
| Mercury | 14 | 12 |
| Jupiter | 11 | 11 |
| Venus | 10 | 8 |
| Saturn | 15 | 15 |

Notes: the nodes are never combust. Some Surya-Siddhanta based tables use slightly different orbs (for example 17 for Mars, 13 for Mercury direct/12 retrograde, 9 or 11 for Venus) [school difference]. Combustion is graded: planets within about 1 degree are called "deep combust"; a planet *very* close to the Sun in an astronomical sense is called cazimi by Western tradition and treated as empowered, an idea not found in the Parashari texts. In practice the reading asks: what does this planet's domain look like when it must share the stage with the self?

## Retrogression (vakri)

Retrograde motion is apparent, caused by the relative motion of Earth and the planet. The Sun and Moon never retrograde; the nodes always move backward on average (mean node). Mars, Mercury, Jupiter, Venus and Saturn do.

Two classical views are recorded:
- Retrograde planets gain *cheshta bala* (motional strength), so they act forcefully. BPHS notes that a retrograde planet counts as strong even if its sign position is weak.
- Another view (Phaladeepika tradition) says that a retrograde planet is read like a planet in exaltation sign, and that it may behave in the manner of its dispositor.

Contemporary practice: retrograde planets tend to act more internally, with themes revisited, delayed or reworked. This should not be read as "bad". A retrograde malefic or benefic in a debilitation sign is read as improving the planet's condition by some teachers. Engine: `retrograde` is derived from speed (negative longitudinal speed).

## Planetary states (avasthas), basics

**Baladi (age) avastha.** Each sign is split into five 6-degree bands: infant, youth, adult, old, dead (bala, kumara, yuva, vriddha, mrita). In odd signs the order runs from 0 to 30 degrees as listed; in even signs it is reversed. Results: the adult stage is strongest, the infant and old stages give about half, and the dead stage the least.

**Jagradadi avastha.** Wakeful (jagrat): planet in own or exaltation sign, full results. Dreaming (swapna): friend or neutral sign, moderate results. Sleeping (sushupti): enemy or debilitation sign, weak results.

**Deeptadi avasthas.** Nine states depending on sign placement: deepta (exalted), swastha (own), mudita (friend), shanta (benefic-varga), shakta (retrograde), pidita (in planetary war), deena (enemy), vikala (combust), khala (debilitation) [partial list; texts differ in assignment]. Use these as descriptive vocabulary rather than computed values.

## Planetary war (graha yuddha)

When two of Mars, Mercury, Jupiter, Venus or Saturn are within 1 degree of each other, the one with the lower (northern) latitude or smaller longitude is considered "beaten" depending on school. The engine does not compute this. Treat as an advanced topic.

## Pushkara navamsa and Pushkara bhaga (quick table)

Pushkara navamsas are navamsa portions regarded as especially nourishing. Two per sign:

| Sign group | Pushkara navamsa degrees |
|---|---|
| Aries, Leo, Sagittarius | 20 to 23 deg 20' and 26 deg 40' to 30 |
| Taurus, Virgo, Capricorn | 6 deg 40' to 10 and 13 deg 20' to 16 deg 40' |
| Gemini, Libra, Aquarius | 16 deg 40' to 20 and 23 deg 20' to 26 deg 40' |
| Cancer, Scorpio, Pisces | 0 to 3 deg 20' and 6 deg 40' to 10 |

Pushkara bhaga (single supportive degrees) are 21 degrees in fire signs, 14 in earth signs, 24 in air signs and 7 in water signs. Three of the Pushkara navamsas are also vargottama (Taurus, Cancer, Sagittarius). Sources agree on the tables; the weight given to them differs and they are a refinement rather than a core technique.

## Quick reading checklist for a planet

1. Dignity of the sign: exalted, moolatrikona, own, friend, neutral, enemy, debilitated.
2. Degree within the sign: near the peak, within the moolatrikona stretch, or at the sandhi (the first or last degree of a sign, a weakness in some schools).
3. Combustion and retrograde status.
4. Dignity in the navamsa (see `kb_chart_divisional_charts.md`).
5. House placement and house lordship (see `kb_chart_functional_nature_by_lagna.md`).
