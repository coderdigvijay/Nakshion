---
title: "Ashtakoota Guna Milan: The Eight Kootas, Scoring Tables and Variants"
tradition: vedic
system: vedic
tier: 2
language: en
sources:
  - "Saravali / Maitreya 8 documentation, Asta Koota pages (Varna, Vashya, Dina, Yoni, Gana, Rasi, Nadi): https://saravali.github.io/astrology/astakoota.html and the koota_*.html pages"
  - "Wikipedia, Astrological compatibility (orientation only): https://en.wikipedia.org/wiki/Astrological_compatibility"
  - "Jagannath Hora knowledge pages (Varna koot, Gana koot, Nadi dosha): https://jagannathhora.com/varna-koot-spiritual-compatibility/ , https://jagannathhora.com/gana-koot-deva-manushya-rakshasa/"
  - "AstroSaxena, Ashtakoot System of Matching Horoscopes 2: https://www.astrosaxena.com/asmh2"
  - "FreeHoroscopesOnline vashya and yoni pages: https://freehoroscopesonline.in/vashyakoota.php , https://freehoroscopesonline.in/yonikoota.php"
  - "AAPS yoni matching chart: https://aaps.space/blog/yoni-matching-chart/"
  - "Steve Hora, Marriage Compatibility (Substack): https://stevehora.substack.com/p/marriage-compatibility"
  - "Sahita Vivaha, Graha Maitri table: https://sahitavivahamatching.com/graha-maitri-koota-kundli-matching/"
  - "Muhurat Choghadiya, Graha Maitri Kuta: https://www.muhuratchoghadiya.com/en/kundali-gyan/grah-maitri-kuta"
  - "AnytimeAstro Ashtakoota and Tara koota blog pages; RoxyAPI Kundli matching guide (score bands)"
  - "Cross-check detail: docs/kb-research/ashtakoota-verification.md in this repository"
confidence: medium
school_notes: "Varna, Vashya, Tara, Yoni and Gana tables exist in several regional variants. This file gives the most widely reproduced version (the Saravali / Maitreya tables) and lists the main alternatives. The classical texts (Muhurta Chintamani, Jyotirnibandha) were not read directly; the tables below are modern transcriptions."
---

# Ashtakoota Guna Milan

## Overview

Ashtakoota ("eight factors") is the best-known North Indian method of comparing two horoscopes for marriage. It looks only at the **Moon**: the Moon's sign (rashi) and its nakshatra in each chart. Each of the eight kootas awards between 0 and a maximum number of points, and the maximum values rise from 1 to 8 so that the total is 36 gunas.

| Koota | Max | Measures (traditional gloss) | Based on |
|---|---|---|---|
| Varna | 1 | Temperament / ego level, spiritual outlook | Moon sign |
| Vashya | 2 | Mutual influence, attraction, who adapts | Moon sign |
| Tara (Dina) | 3 | Wellbeing, health and luck as a couple | Nakshatra |
| Yoni | 4 | Instinctive and physical rapport | Nakshatra |
| Graha Maitri | 5 | Mental friendship, shared outlook | Moon-sign lords |
| Gana | 6 | Temperament and behaviour style | Nakshatra |
| Bhakoot (Rasi) | 7 | Emotional flow, family and prosperity | Moon-sign distance |
| Nadi | 8 | Constitutional (health) and progeny compatibility | Nakshatra |
| **Total** | **36** | | |

**Orientation.** Most tables are written with the bride in the rows and the groom in the columns. Several kootas are asymmetric, so swapping the roles can change the score. Software that does not know the roles has to pick a convention or compute both orders.

**Caveat in the source itself.** The Saravali documentation warns that Asta Koota "should not be the only source" for judging a partnership and that each natal chart should be studied on its own first (see the companion note on factors beyond the 36 points).

## Varna Koota (1 point)

Varna groups the 12 Moon signs into four classes by element and compares them. The rule: the groom's varna should be **equal to or higher than** the bride's; if so the couple gets 1 point, otherwise 0. Order from highest: Brahmin, Kshatriya, Vaishya, Shudra. In modern language it is a rough proxy for ego level and sense of "who leads", not a statement about social caste.

**Assignment (majority version):**
- Brahmin (water signs): Cancer, Scorpio, Pisces
- Kshatriya (fire): Aries, Leo, Sagittarius
- Vaishya (earth): Taurus, Virgo, Capricorn
- Shudra (air): Gemini, Libra, Aquarius

**Variant.** The Saravali page swaps the last two lines (Vaishya = air, Shudra = earth). Jagannath Hora, AstroSaxena and AnytimeAstro-style pages use the earth = Vaishya version above. The difference only matters for pairs involving an earth sign and an air sign.

**Interpretation note.** Because it is a single point, Varna rarely changes an overall reading. Reputable modern writers frame it as "spiritual outlook" and avoid any caste meaning.

## Vashya Koota (2 points)

Vashya asks which partner tends to influence or "bring under control" the other, and how easily they adapt. Signs fall into five animal-type groups:

- **Chatushpada** (quadrupeds): Aries, Taurus, the second half of Sagittarius and the first half of Capricorn
- **Manava** (humans): Gemini, Virgo, Libra, Aquarius, first half of Sagittarius
- **Jalachara** (water creatures): Cancer, Pisces, second half of Capricorn
- **Vanachara** (wild animal): Leo
- **Keeta** (insect): Scorpio

The Saravali list omits Sagittarius; the half-sign split above (first 15 degrees human, last 15 degrees quadruped) is the standard one used elsewhere. Capricorn splits at 15 degrees too.

**Matrix A (Saravali / Maitreya 8; rows = bride, columns = groom):**

| Bride \ Groom | Chatushpada | Manava | Jalachara | Vanachara | Keeta |
|---|---|---|---|---|---|
| Chatushpada | 2 | 0 | 0 | 0.5 | 0 |
| Manava | 1 | 2 | 1 | 0.5 | 1 |
| Jalachara | 0.5 | 1 | 2 | 1 | 1 |
| Vanachara | 0 | 0 | 0 | 2 | 0 |
| Keeta | 1 | 1 | 1 | 0 | 2 |

**Matrix B (AstroSaxena, FreeHoroscopesOnline, Steve Hora and several Indian portals):**

| Bride \ Groom | Chatushpada | Manava | Jalachara | Vanachara | Keeta |
|---|---|---|---|---|---|
| Chatushpada | 2 | 1 | 1 | 1.5 | 1 |
| Manava | 1 | 2 | 1.5 | 0 | 1 |
| Jalachara | 1 | 1.5 | 2 | 1 | 1 |
| Vanachara | 0 | 0 | 0 | 2 | 0 |
| Keeta | 1 | 1 | 1 | 0 | 2 |

Both matrices agree that the same group scores 2 and that Leo (Vanachara) and Scorpio (Keeta) are the most self-contained groups. They disagree on 8 of the 25 cells. Matrix B follows the "food chain" idea (the Jalachara group is food for the Manava group; the Chatushpada group is food for the Vanachara group) and gives partial credit more generously. There is also a rarely seen third table (vedikastrologer.com) that differs further and was not adopted anywhere else found. Which matrix a given calculator uses is not usually stated.

## Tara (Dina) Koota (3 points)

Tara looks at the distance between the two birth nakshatras. Count from the bride's nakshatra to the groom's (the birth nakshatra itself is 1), divide by 9 and note the remainder. Then repeat from groom to bride.

The nine taras and their reputations: 1 Janma (birth), 2 Sampat (wealth), 3 Vipat (danger), 4 Kshema (wellbeing), 5 Pratyak (obstacle), 6 Sadhana (achievement), 7 Naidhana (loss), 8 Mitra (friend), 0 (that is, 9) Parama Mitra (best friend).

**Saravali / Dina rule (used here):** a direction scores 1.5 unless the remainder is 3, 5 or 7. Both directions good = 3, one good = 1.5, neither = 0.

**Variant (AnytimeAstro, AstroSaxena):** all **odd** remainders (1, 3, 5, 7) are treated as unfavourable, so Janma Tara (remainder 1) also loses the half-point. Scoring is the same 3 / 1.5 / 0 by parity.

Practical effect: the two conventions disagree whenever either count leaves remainder 1, which is roughly one pair in nine per direction.

## Yoni Koota (4 points)

Each nakshatra is given an animal (yoni), and the animals have natural affinities and enmities. Yoni is read as instinctive and physical rapport and the ease of intimacy.

**Nakshatra to yoni (male / female nakshatra of the pair):** Horse: Ashwini / Shatabhisha. Elephant: Bharani / Revati. Sheep: Pushya / Krittika. Serpent: Rohini / Mrigashira. Dog: Mula / Ardra. Cat: Ashlesha / Punarvasu. Rat: Magha / Purva Phalguni. Cow: Uttara Phalguni / Uttara Bhadrapada. Buffalo: Swati / Hasta. Tiger: Vishakha / Chitra. Deer: Jyeshtha / Anuradha. Monkey: Purva Ashadha / Shravana. Mongoose: Uttara Ashadha / (Abhijit). Lion: Purva Bhadrapada / Dhanishta. This list is consistent across Saravali, Sahita Vivaha, AAPS and FindYourFate; one site (Jagannath Hora) shows a garbled Punarvasu entry that was not corroborated.

**Scale:** 4 same animal, 3 friendly, 2 neutral, 1 unfriendly, 0 sworn enemies. The seven sworn-enemy pairs, agreed everywhere, are Horse-Buffalo, Elephant-Lion, Sheep-Monkey, Serpent-Mongoose, Dog-Deer, Cat-Rat and Cow-Tiger.

## Yoni Koota: the full matrix

Saravali / Maitreya 8 matrix (rows = bride yoni, columns = groom yoni):

| | Hor | Ele | Shp | Ser | Dog | Cat | Rat | Cow | Buf | Tig | Dee | Mon | Mgs | Lio |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Horse** | 4 | 2 | 2 | 3 | 2 | 2 | 2 | 1 | 0 | 1 | 3 | 3 | 2 | 1 |
| **Elephant** | 2 | 4 | 3 | 3 | 2 | 2 | 2 | 2 | 3 | 1 | 2 | 3 | 2 | 0 |
| **Sheep** | 2 | 3 | 4 | 2 | 1 | 2 | 1 | 3 | 3 | 1 | 2 | 0 | 3 | 1 |
| **Serpent** | 3 | 3 | 2 | 4 | 2 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 0 | 2 |
| **Dog** | 2 | 2 | 1 | 2 | 4 | 2 | 1 | 2 | 2 | 1 | 0 | 2 | 1 | 1 |
| **Cat** | 2 | 2 | 2 | 1 | 2 | 4 | 0 | 2 | 2 | 1 | 3 | 3 | 2 | 1 |
| **Rat** | 2 | 2 | 1 | 1 | 1 | 0 | 4 | 2 | 2 | 2 | 2 | 2 | 1 | 2 |
| **Cow** | 1 | 2 | 3 | 1 | 2 | 2 | 2 | 4 | 3 | 0 | 3 | 2 | 2 | 1 |
| **Buffalo** | 0 | 3 | 3 | 1 | 2 | 2 | 2 | 3 | 4 | 1 | 2 | 2 | 2 | 1 |
| **Tiger** | 1 | 1 | 1 | 2 | 1 | 1 | 2 | 0 | 1 | 4 | 1 | 1 | 2 | 1 |
| **Deer** | 1 | 2 | 2 | 2 | 0 | 3 | 2 | 3 | 2 | 1 | 4 | 2 | 2 | 1 |
| **Monkey** | 3 | 3 | 0 | 2 | 2 | 3 | 2 | 2 | 2 | 1 | 2 | 4 | 3 | 2 |
| **Mongoose** | 2 | 2 | 3 | 0 | 1 | 2 | 1 | 2 | 2 | 2 | 2 | 3 | 4 | 2 |
| **Lion** | 1 | 0 | 1 | 2 | 1 | 1 | 2 | 1 | 2 | 1 | 1 | 2 | 2 | 4 |

**Where it is not symmetric.** In this table Horse (bride) with Deer (groom) scores 3 but Deer (bride) with Horse (groom) scores 1, and Lion (bride) with Buffalo (groom) scores 2 while Buffalo (bride) with Lion (groom) scores 1. AAPS prints an otherwise identical table that is symmetric at those two pairs (Deer-Horse 3, Lion-Buffalo 1). Another page (mohitmrinal.com) gives different values for several cells of its Sheep row, including Sheep-Monkey 3, which contradicts the sworn-enemy rule and looks like a transcription error.

**A different school.** AstroSaxena scores yoni by animal gender: for example same animal with opposite sexes 4, friendly 3.5, same-sex pairs lower. This variant is not common in software.

## Graha Maitri Koota (5 points)

Graha Maitri compares the **lords of the two Moon signs** using the natural (naisargika) friendship table. Because friendship is not always mutual, both directions are checked.

| Natural friendships | Friends | Neutral | Enemies |
|---|---|---|---|
| Sun | Moon, Mars, Jupiter | Mercury | Venus, Saturn |
| Moon | Sun, Mercury | Mars, Jupiter, Venus, Saturn | none |
| Mars | Sun, Moon, Jupiter | Venus, Saturn | Mercury |
| Mercury | Sun, Venus | Mars, Jupiter, Saturn | Moon |
| Jupiter | Sun, Moon, Mars | Saturn | Mercury, Venus |
| Venus | Mercury, Saturn | Mars, Jupiter | Sun, Moon |
| Saturn | Mercury, Venus | Jupiter | Sun, Moon, Mars |

**Scoring:** same lord or mutual friends 5; friend + neutral 4; neutral + neutral 3; friend + enemy 1; neutral + enemy 0.5; mutual enemies 0.

Example of the asymmetry: the Moon counts Mercury as a friend but Mercury counts the Moon as an enemy, so a Cancer-Gemini pair scores 1, not 5. All sources checked agree on this scale.

## Gana Koota (6 points)

Each nakshatra belongs to one of three temperaments: **Deva** (gentle, balanced), **Manushya** (worldly, practical) and **Rakshasa** (forceful, independent). The names are traditional labels, not moral grades.

- **Deva:** Ashwini, Mrigashira, Punarvasu, Pushya, Hasta, Swati, Anuradha, Shravana, Revati
- **Manushya:** Bharani, Rohini, Ardra, Purva Phalguni, Uttara Phalguni, Purva Ashadha, Uttara Ashadha, Purva Bhadrapada, Uttara Bhadrapada
- **Rakshasa:** Krittika, Ashlesha, Magha, Chitra, Vishakha, Jyeshtha, Mula, Dhanishta, Shatabhisha

**Matrix A (Saravali; rows = bride, columns = groom):**

| Bride \ Groom | Deva | Manushya | Rakshasa |
|---|---|---|---|
| Deva | 6 | 6 | 0 |
| Manushya | 5 | 6 | 0 |
| Rakshasa | 1 | 0 | 6 |

**Variants.** AstroSaxena gives Manushya bride / Deva groom 5, Deva bride / Manushya groom 3, Manushya bride / Rakshasa groom 3, Deva bride / Rakshasa groom 1 and Rakshasa bride with Deva or Manushya groom 0. Jagannath Hora lists Deva-Manushya 5, Manushya-Rakshasa 1, Deva-Rakshasa 0 without direction. A 4-point Gana appears on one Substack page and does not fit the 36 total. Matrix A is the most widely reproduced.

## Bhakoot (Rasi) Koota (7 points)

Bhakoot counts the sign distance between the two Moons, in both directions. The pairings **2/12, 5/9 and 6/8** score 0 and every other relationship (1/1, 1/7, 3/11, 4/10) scores 7. These are the three bhakoot doshas (see the companion note on doshas and cancellations).

Some Indian sources add a gradation (for example 4 points when the sign lords are friends); the Saravali description and the majority of websites use the strict 0 or 7 rule. Some classical commentators do not treat 5/9 as a dosha at all.

Moon-sign counting uses the sidereal Moon sign. Near a sign boundary a few minutes of birth-time error can move the Moon into the next sign and change this koota completely.

## Nadi Koota (8 points)

Nadi divides the 27 nakshatras into three groups (traditionally linked to the ayurvedic humours Vata, Pitta and Kapha) and gives 8 points when the two partners are in **different** nadis, 0 when they share one.

- **Adi (Vata):** Ashwini, Ardra, Punarvasu, Uttara Phalguni, Hasta, Jyeshtha, Mula, Shatabhisha, Purva Bhadrapada
- **Madhya (Pitta):** Bharani, Mrigashira, Pushya, Purva Phalguni, Chitra, Anuradha, Purva Ashadha, Dhanishta, Uttara Bhadrapada
- **Antya (Kapha):** Krittika, Rohini, Ashlesha, Magha, Swati, Vishakha, Uttara Ashadha, Shravana, Revati

This assignment is identical in Saravali and Jagannath Hora. Because each nadi holds nine of the 27 nakshatras, roughly one random pair in three shares a nadi, so many conventions list cancellations (see the doshas note).

## Reading the Total out of 36

All sources agree that **18 is the traditional minimum** (half the maximum). The upper bands differ slightly between sites, so any statement should name its table.

| Total | Common wording (RoxyAPI / Vedic Rishi style) | Alternative bands (AstroGiva / AnytimeAstro style) |
|---|---|---|
| below 18 | not recommended without further study | not appropriate for marriage |
| 18 to 24 | acceptable; look at specific weak kootas | average, acceptable |
| 25 to 32 | good to very good | 24 to 32: very good |
| 33 to 36 | excellent / exceptional | 32 to 36: excellent |

**Steve Hora's table** uses stricter cut-offs (under 18 poor, 18 to 22 moderate, 23 to 25 good, 26 to 28 very good, above 28 excellent) and a 4-point Gana, so it is not directly comparable.

**Guidance, not verdict.** Practitioners emphasise that a high score does not guarantee a harmonious marriage and a lower one does not rule it out. The score is best presented as a summary of Moon-based temperament, with the weakest kootas used as conversation topics rather than warnings.

## Regional Variants

- **South Indian 10 Porutham:** Dina, Gana, Mahendra, Stree Deergha, Yoni, Rasi, Rasyadhipati (Graha Maitri), Vasya, Rajju and Vedha. Dina, Rasi, Gana, Yoni and Rajju are treated as the key five, with Rajju and Dina usually weighted most. It is pass or fail on each factor rather than a 36-point sum.
- **Rajju Koota:** Saravali lists it as a ninth, optional koota, scoring 0 to 4 by the body-part group (foot, waist, navel, neck, head) of each nakshatra and whether it is ascending or descending.
- **Kuta system with 12 factors:** some Western-language sources (for example Roeland de Looff at dirah.org) describe a 12-factor version where about 21 of 36 is suggested as a minimum.
- **Bride-to-groom orientation:** in nearly every table the bride is the row; a few sites reverse this. Always check before comparing.
