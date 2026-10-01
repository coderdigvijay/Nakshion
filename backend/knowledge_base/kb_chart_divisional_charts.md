---
title: "Divisional Charts (Vargas): Purpose, Computation and Reading"
tradition: "Jyotish (Parashari Shodashavarga)"
system: vedic
tier: 2
language: en
sources:
  - "BPHS chapter on Shodasha Varga (ch. 6-7) as summarised at jagannathhora.com, komilla.com, jyotishabharati.com (notes on navamsa and pushkara navamsa)"
  - "Jataka Parijata (1932) ch. 2, vargas section - archive.org/details/JatakaParijata1932 (the text lists the varga names Rasi, Hora, Drekkana, Chaturthamsa, Saptamsa, Navamsa, Dasamsa, Dwadasamsa, Shodasamsa, Vimsamsa, Siddhamsa, and others)"
  - "Engine: backend/app/astrology/vedic.py (vargas)"
confidence: medium
school_notes: "Rules for D2 (Hora) and D30 differ between Parashari and other methods (Jaimini, Kalyana Varma). D9 and D10 rules are consistent. D60 start-sign rules for even signs differ among commentators. Both positions are recorded where known."
---

# Divisional Charts (Vargas)

A divisional chart splits each 30-degree sign into equal parts and maps each part to a sign. The result is a new chart that zooms into one life theme. The rashi chart (D1) is the "body"; the vargas are "organs". Parashara describes sixteen standard vargas (Shodashavarga). Vimshopaka bala (a weighted score) uses them to rate planetary strength.

Always read the divisional chart *with* the D1 chart: a planet's house and sign are considered in both, and a planet in the same sign in D1 and the relevant varga (a "vargottama" situation) is notably reinforced.

## D1 Rashi (birth chart)

The primary chart: body, personality, overall pattern of life. All other vargas derive from it by longitude.

## D2 Hora (wealth and resource management)

Each sign is split into two 15-degree halves. Parashari method: in odd signs the first half belongs to the Sun's hora (Leo), the second to the Moon's hora (Cancer); in even signs the order reverses. So planets map only to Leo or Cancer. Other methods (for example the Jaimini and some South Indian approaches) differ. Use: assessing earning capacity and resource flow, mainly through the 2nd and 11th houses.

## D3 Drekkana (siblings, courage, initiative)

Each sign is divided into three 10-degree parts that map to the sign itself, the 5th from it and the 9th from it. Use: siblings, courage, effort and stamina, shared enterprises. Some texts attach deity or "Drekkana forms" (Parashara's faces) with descriptive imagery.

## D4 Chaturthamsa (property, fixed assets, home)

Four parts of 7.5 degrees each, mapping to the sign itself and the 4th, 7th and 10th signs from it. Use: residence, property, vehicles, and rootedness.

## D7 Saptamsa (children and progeny)

Seven parts of about 4.2857 degrees each. In odd signs the count starts from the sign itself; in even signs it starts from the 7th sign. Use: children, creative lineage and legacy; read together with the 5th house and Jupiter.

## D9 Navamsa (dharma, spouse, inner strength)

Nine parts of 3 degrees 20 minutes. Rule: for fire signs the first navamsa is Aries; earth signs begin at Capricorn; air signs at Libra; water signs at Cancer. Equivalently: movable signs begin from the sign itself; fixed signs begin from the 9th from it; dual signs begin from the 5th from it. The navamsa is the single most important varga.

Use: relationship and marriage themes, the long-run fruition of a planet's promise, a planet's true strength (dignity in navamsa), and the dharma path. Practitioners say that D1 shows the promise and D9 shows how it is lived and delivered. The Navamsa lagna and the 7th house are looked at for partners. The dasha lord's navamsa dignity matters when judging the dasha.

### Worked example
A planet at 12 degrees Taurus. Taurus is a fixed (earth) sign: navamsa count starts at Capricorn. 12 degrees falls in the 4th navamsa (9.99 to 13.33 degrees is the 4th when counting 0-3.33 as the 1st), so the 4th sign from Capricorn is Aries. The planet is in Aries navamsa. Check the arithmetic: index = floor(12 / 3.3333) = 3 (0-based), start sign for earth is Capricorn (index 9), sign index = (9 + 3) mod 12 = 0 = Aries.

### Vargottama
A planet is vargottama when it occupies the same sign in D1 and D9. It gains strength approaching own-sign strength. Vargottama positions occur at fixed degree windows: the first navamsa of movable signs (0 to 3 deg 20' of Aries, Cancer, Libra, Capricorn), the fifth navamsa of fixed signs (13 deg 20' to 16 deg 40' of Taurus, Leo, Scorpio, Aquarius) and the ninth navamsa of dual signs (26 deg 40' to 30 of Gemini, Virgo, Sagittarius, Pisces).

### Pushkara navamsa
See `kb_chart_planets_in_signs_dignity.md` for the table. A planet in one of the 24 Pushkara navamsas gains supportive quality; three of them are also vargottama.

## D10 Dashamsa (career and public life)

Ten parts of 3 degrees. In odd signs the count starts from the sign itself; in even signs from the 9th sign. Use: profession, public standing, achievements. Read with the 10th house and its lord in D1.

## D12 Dwadashamsa (parents and lineage)

Twelve parts of 2.5 degrees, starting from the sign itself and proceeding in zodiacal order. Use: parents, ancestry, inherited traits.

## D16 Shodashamsa (vehicles, comforts)

Sixteen parts of 1 degree 52 minutes 30 seconds. Starting sign: movable signs start from Aries, fixed signs from Leo, dual signs from Sagittarius. Use: vehicles, conveyances and day-to-day comfort.

## D20 Vimshamsa (spiritual practice)

Twenty parts of 1.5 degrees. Starting sign: movable signs from Aries, fixed signs from Sagittarius, dual signs from Leo. Use: spiritual inclination, devotion and practice.

## D24 Chaturvimshamsa (education and learning)

Twenty-four parts of 1 degree 15 minutes. Odd signs start from Leo, even signs from Cancer. Use: education, learning and knowledge.

## D27 Bhamsa / Nakshatramsa (strengths and weaknesses)

Twenty-seven parts of 1 degree 6 minutes 40 seconds (one nakshatra-pada-like unit). Starting sign: fire signs from Aries, earth signs from Cancer, air signs from Libra, water signs from Capricorn. Use: inherent strengths and vulnerabilities.

## D30 Trimshamsa (challenges, character flaws, misfortune themes)

Unequal parts. Parashari division, odd signs: 0-5 degrees Mars (Aries), 5-10 Saturn (Aquarius), 10-18 Jupiter (Sagittarius), 18-25 Mercury (Gemini), 25-30 Venus (Libra). Even signs: 0-5 Venus (Taurus), 5-12 Mercury (Virgo), 12-20 Jupiter (Pisces), 20-25 Saturn (Capricorn), 25-30 Mars (Scorpio). Use: where life tests us, health and emotional vulnerabilities; read with a light touch.

## D40 Khavedamsa (maternal-line influences)

Forty parts of 45 minutes. Odd signs start from Aries, even signs from Libra. Use: auspicious/inauspicious influences from the mother's side.

## D45 Akshavedamsa (paternal-line influences)

Forty-five parts of 40 minutes. Movable signs start from Aries, fixed from Leo, dual from Sagittarius. Use: general character and paternal-line influence.

## D60 Shashtiamsa (past-life patterns, fine detail)

Sixty parts of 30 minutes each. The start is the sign itself, then proceeding through the zodiac. Use: fine-grained karmic detail; extremely sensitive to birth time (a 2-minute error changes the part). Many teachers use D60 only when birth time is reliably rectified. Names of the 60 shashtiamsas are classical; their auspiciousness is also classified.

## Why birth time matters for vargas

The higher the divisional number, the smaller the part and the faster the sign changes with time. The ascendant moves one degree about every four minutes, so D9 is relatively stable across a few minutes, D10 across a couple of minutes, and D60 within roughly two minutes only. For unknown birth time, only the planet-in-sign information from slow planets remains reliable in D9; the Moon's navamsa depends on time of day (about 13 degrees a day).

## Engine alignment

The engine currently computes D1, D9 (navamsa, `d9()`: longitude times 9) and D10 (dashamsa, `d10()`: odd signs from themselves, even signs from the 9th); all other vargas on this page are knowledge only, not computed. The knowledge here lets an assistant explain them. When asked about a varga that the engine does not output, state that it is not computed and avoid inventing positions.
