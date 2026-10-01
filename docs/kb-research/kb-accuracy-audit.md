# KB Accuracy Audit - existing Vedic files (2026-10-01)

Scope: vedic_astrology.md, nakshatras_deep_dive.md, indian_bphs.md, indian_jaimini_sutras.md,
predictive_techniques_advanced.md, remedial_astrology.md, timing_transits.md, planets.md, houses.md,
zodiac_signs.md (all in backend/knowledge_base/).

Method: each fact was compared against (a) the public-domain Brihat Jataka of Varahamihira, tr. N. Chidambaram
Iyer 1885 (archive.org wg1079; local copy in backend/knowledge_sources/classical/), which states
exaltation signs and degrees, moolatrikona signs, vargottama rule and natural friendships; (b) independent Hindi and
English practitioner sources for dasha order/years, sade sati, karanas, nakshatra lords (see sources manifest);
(c) arithmetic checks (navamsha calculations, 13d20m spans, 120-year sum). Surya Siddhanta (Burgess 1860) was
downloaded as a reference for nakshatra spans but was not needed for a discrepancy. BPHS and Saravali/Phaladeepika
public-domain translations were not located on archive.org in an OCR-clean form in this session, so BPHS-specific
claims were checked against Brihat Jataka where they overlap and against modern sources otherwise.
Severity: HIGH = would corrupt a chart-derived answer; MEDIUM = factual error in a teaching statement;
LOW = imprecision/wording.

Total claims checked: about 460. Errors found: 4 (all fixed). Items for human review: 9.

## Summary by file

| File | Claims checked | Errors | Fixed | Notes |
|---|---|---|---|---|
| nakshatras_deep_dive.md | ~170 (27 x range, lord, deity, symbol, guna, gender, pada navamsha; kuta table) | 1 | 1 | all spans, lords, deities, gunas correct; one false vargottama claim |
| vedic_astrology.md | ~110 (27 spans/lords/deities/padas, dasha years, ayanamsa, mangal dosha, sade sati) | 0 | - | ayanamsa "approx 24 deg" correct for 2024 (Lahiri about 24 deg 11 min) |
| indian_bphs.md | ~90 (planet natures, dignities, house names, dasha table, Ashtottari, aspects, shadbala, ashtakavarga, divisional charts) | 3 | 3 | trishadaya mislabel, aspect-strength statement; see below |
| indian_jaimini_sutras.md | ~35 (karakas, rashi drishti, argala, sthira dasha, chara dasha) | 1 | 1 | karaka table label |
| predictive_techniques_advanced.md | ~25 (zodiacal releasing years, firdaria, returns) | 0 | - | ZR years Mars 15, Venus 8, Mercury 20, Moon 25, Sun 19, Jupiter 12, Saturn 27 correct; firdaria 70+3+2=75 correct |
| remedial_astrology.md | ~45 (gems, fingers, days, beej mantras, fasting, donation) | 0 | - | beej and navagraha mantras correct; practices are conventions, some uncertain (see review list) |
| timing_transits.md | ~15 (Saturn 29.5 yr, Jupiter 12 yr, retrograde cycles) | 0 | - | correct |
| planets.md | ~40 (dignities, orbital periods, retrograde durations) | 0 | - | exaltation degrees are the Western/Hellenistic set, valid for that tradition (see review) |
| houses.md | ~15 (angular/succedent/cadent, joys, derived houses) | 0 | - | correct for the Western house-class model |
| zodiac_signs.md | ~35 (rulers, element/modality, date ranges, domicile/exaltation) | 0 | - | tropical date ranges correct |

## Verified items (representative, all correct)

- Nakshatra span 13d20m; 27 x 13d20m = 360; pada 3d20m. Spans for all 27 (Ashwini 0 Aries ... Revati 16d40m-30 Pisces) correct.
- Nakshatra lords in Vimshottari cycle Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury repeated 3 times: correct in both nakshatras_deep_dive.md and vedic_astrology.md.
- Deities (Ashwini Kumaras, Yama, Agni, Brahma/Prajapati, Soma, Rudra, Aditi, Brihaspati, Nagas, Pitris, Bhaga, Aryaman, Savitar, Tvashtar/Vishvakarma, Vayu, Indra-Agni, Mitra, Indra, Nirriti, Apas, Vishvadevas, Vishnu, Vasus, Varuna, Aja Ekapada, Ahir Budhnya, Pushan): correct.
- Gana assignments (9 Deva, 9 Manushya, 9 Rakshasa) match the standard Ashtakoota table; genders and Mrigashira/Mula/Shatabhisha neutral entries match common tables (Mrigashira varies by source).
- Padas to navamsha signs: all 27 x 4 mappings checked by calculation (fire signs start Aries, earth Capricorn, air Libra, water Cancer) - correct. Vargottama claims (Rohini p2, Punarvasu p4, Purva Phalguni p1, Chitra p2-3, Uttara Ashadha p1-2, Anuradha p4, Shatabhisha p3, Revati p4) verified; Brihat Jataka 1.14 gives the same rule (first navamsha of movable, fifth of fixed, ninth of dual signs).
- Exaltation/debilitation, Vedic (indian_bphs.md): Sun Aries 10, Moon Taurus 3, Mars Capricorn 28, Mercury Virgo 15, Jupiter Cancer 5, Venus Pisces 27, Saturn Libra 20; debilitation in opposite signs at same degrees. Matches Brihat Jataka 1.13 (Iyer 1885: "The 10th, 3rd, 28th, 15th, 5th, 27th, and 20th are the degrees of main exaltation").
- Moolatrikona (not in the KB files; per Brihat Jataka 1.14): Sun Leo, Moon Taurus, Mars Aries, Mercury Virgo, Jupiter Sagittarius, Venus Libra, Saturn Aquarius. Recommend adding to indian_bphs.md (see review list).
- Vimshottari order/years (Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17 = 120): correct in vedic_astrology.md and indian_bphs.md; nakshatra-to-dasha table correct. Ashtottari 6+15+8+17+10+19+12+21 = 108: correct.
- Graha drishti: all planets 7th; Mars 4 and 8; Jupiter 5 and 9; Saturn 3 and 10: correct.
- Sign lords, detriments (Vedic and Western), element/modality of all 12 signs: correct.
- Jaimini rashi drishti table (movable-fixed except adjacent; mutable mutual): correct. Argala 2/4/11 with virodha 12/10/3; 5th secondary with 9th virodha: correct. Sthira dasha 7/8/9 years: correct.
- Shadbala dig bala houses, naisargika bala values (60, 51.43, 42.86, 34.29, 25.71, 17.14, 8.57), minimum rupas (5, 6, 5, 7, 6.5, 5.5, 5): correct. SAV 337 average 28/house, maximum 56: correct.
- Natural friendships quoted in Brihat Jataka 2.15 agree with the standard table where the KB uses it.
- Mercury combustion (about 14 deg direct, 12 deg retrograde) used in indian_bphs.md Budhaditya statement: consistent.
- Retrograde/orbit data in planets.md/timing_transits.md (Mercury ~3 per year ~3 weeks; Venus ~584-day cycle, ~40 days; Mars ~26-month cycle ~2.4 months; Jupiter ~4 months; Saturn ~4.5 months; periods 11.86, 29.46, 84, 165, 248 yr; Chiron 50.7 yr): correct.

## Errors found and fixes applied (each logged)

| # | File | Line (approx.) | Before | After | Correct fact and source | Severity |
|---|---|---|---|---|---|---|
| 1 | nakshatras_deep_dive.md | 289 (Hasta pada 4) | "Pada 4 (Cancer navamsha, Vargottama): ..." | "Pada 4 (Cancer navamsha): ..." | Hasta pada 4 = Virgo 20d-23d20m. Virgo (dual earth) navamshas start from Capricorn; the 7th navamsha is Cancer, not Virgo, so it is not vargottama. Vargottama needs the same sign in D-1 and D-9 (Brihat Jataka 1.14: dual signs vargottama only in the 9th navamsha, 26d40m-30 d) | MEDIUM |
| 2 | indian_bphs.md | ~151 (House Classifications) | "Trishadaya: 3, 6, 11 - houses of desire (kama)" | "Trishadaya: 3, 6, 11 - houses of effort and growth (a subset of the upachaya houses; the kama/desire trine is 3, 7, 11)" | Trishadaya (3, 6, 11) are the growth/malefic-friendly houses; the Kama trikona is 3, 7, 11 | MEDIUM |
| 3 | indian_bphs.md | ~470-476 (Aspect Strength) | "3rd and 10th (Saturn): 75%; 4th and 8th (Mars): 75%; 5th and 9th (Jupiter): 75% or 100%" | Special aspects are full strength for the owning planet; graded scheme for any planet: 3rd/10th 25%, 5th/9th 50%, 4th/8th 75%, 7th 100% | Standard graded drishti (quarter, half, three-quarter, full); Saturn's 3/10 are full, not 75% | MEDIUM |
| 4 | indian_jaimini_sutras.md | 26 (karaka table) | "8th highest (if using 8 karakas) | Darakaraka (DK)" | "8th highest / lowest degree (in the 7-karaka scheme Pitrikaraka is dropped and DK is the 7th)" | The table lists the 8-karaka scheme; calling the 8th row optional and the first seven as the 7-scheme mislabels the schemes (7-scheme: AK, AmK, BK, MK, PK, GK, DK) | LOW |

## Items for human review (not changed)

1. planets.md exaltation degrees (Sun 19 Aries, Jupiter 15 Cancer, Saturn 21 Libra, Moon 3, Mercury 15, Venus 27, Mars 28) are the Western/Hellenistic set. Vedic (Brihat Jataka) gives Sun 10, Jupiter 5, Saturn 20. The file is Western-oriented so the values are valid there, but a one-line note that Vedic degrees differ would prevent mixing. Not changed.
2. indian_bphs.md Rahu/Ketu exaltation ("Taurus or Gemini"; "Scorpio or Sagittarius") is a genuine school dispute; leave as is.
3. indian_bphs.md Ashtottari applicability ("used when Rahu is in a kendra or trikona") is a simplification; classical rule is more specific (Rahu in kendra/trikona from the lagna lord, with day/night and paksha conditions in BPHS). Review for fuller statement.
4. indian_jaimini_sutras.md Chara dasha direction (odd signs direct, even reverse) is one convention; others group Aries/Leo/Virgo/Libra/Aquarius/Pisces as direct, Taurus/Gemini/Cancer/Scorpio/Sagittarius/Capricorn as reverse (or use the 9th house rule). Schools differ; add a school note.
5. vedic_astrology.md Mangal Dosha: house list 1, 2, 4, 7, 8, 12 includes 2nd (some schools exclude it). "After age 28" cancellation is a folk rule. Already hedged.
6. vedic_astrology.md Sade Sati age ranges (25-32, 54-61, 83-90) are illustrative; actual ages depend on the Moon sign.
7. remedial_astrology.md: minimum carat weights, fingers (Moon: little finger/ring finger; Venus: middle/ring; Ketu: ring finger), days (Ketu Tuesday) and "white sapphire nearly as effective at a fraction of the cost" are practitioner conventions, not classical rules; the last statement is an unsupported efficacy claim. Suggest rewording as "a lower-cost alternative that some use". Not changed.
8. remedial_astrology.md "Critical rule: only wear gemstones for functional benefics" is one school's view; others recommend by dasha lord or oppose gems for malefics. Add a school note.
9. indian_bphs.md has no Moolatrikona section; adding the Brihat Jataka list (Sun Leo, Moon Taurus, Mars Aries, Mercury Virgo, Jupiter Sagittarius, Venus Libra, Saturn Aquarius, with degree ranges per other texts) would close a gap noted in the audit brief.

## Notes on sources not obtained

- BPHS (Santhanam/Sharma translations) is under copyright; no public-domain OCR was downloaded. BPHS claims were verified through Brihat Jataka overlap and independent modern sources.
- Saravali, Phaladeepika: public-domain translations exist in archive.org but were not located with clean OCR in this session; recommended follow-up.
- An archive.org Hindi edition of Brihat Jataka (in.ernet.dli.2015.312667) had garbled OCR and was discarded.
