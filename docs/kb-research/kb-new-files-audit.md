# KB audit: new kb_* files (2026-10-02)

Scope: all 29 `backend/knowledge_base/kb_*.md` files (chart 8, dasha 6, panchang 6, match 4, lang 3, remedy 2), each read in full. Only kb_* files were edited. Not touched: non-kb_ files, backend/app, RAG index, sources.yaml; no re-ingest. Engine files were read, never edited.

Primary sources used: Brihat Jataka (Iyer 1885) ch. VIII and 1.14; Jataka Parijata v1 ch. 2 slokas 26-28; Sewell and Dikshit art. 40 (karanas); Vijnananda Brihat Jataka note on Ashtottari; plus web checks (Jyotish-research.com Mangal table, Pushkara degrees). Computations by Python in the session scratchpad.

## Verified numerically
- Antardasha: all 81 durations = MD x AD x 12 / 120 months (0 mismatches at 0.05 tolerance); each MD's nine rows sum to MD years x 12 (84, 240, 72, 120, 84, 216, 192, 228, 204); every row order starts with the MD lord and follows Ketu-Venus-Sun-Moon-Mars-Rahu-Jupiter-Saturn-Mercury; all 72 friend/neutral/enemy statements match the BPHS natural-friendship table with Rahu/Ketu convention (Mercury, Venus, Saturn friends; Sun, Moon, Mars enemies).
- Vimshottari foundations: 120-year sum, nakshatra-lord mapping, worked example (50 deg = Rohini, 2.5 y balance), MD x AD / 10 months formula.
- Ashtakoota: KB Yoni 14x14 (196 cells), Vashya matrix A (25) and Gana matrix A (9) are identical to engine data; Vashya A vs B differ in exactly 8 cells; Nadi 9/9/9, Gana 9/9/9, yoni animals 27/27; ashtakoota maxima 1+2+3+4+5+6+7+8 = 36; Tara 1 in 9 remainder frequency.
- Panchang: karana structure (60 = 1 + 56 + 3; Vishti at positions 8,15,...,57 mapped to the eight half-tithis stated; fixed karanas correct, matches Sewell and Dikshit art. 40); Rahu Kaal/Yamaganda/Gulika weekday part tables and the 06:53-18:59 worked example (rounded to the minute; unrounded 08:23.75); Abhijit 11:36-12:24; hora order and next-day Moon rule; 27 yogas; nine cautionary yogas; nakshatra groups (4+5+5+4+3+4+2 = 27); tithi classes; all 7 gochara vedha tables and favourable-house sets; SAV 337 (48+49+39+54+56+52+39) and 28.08 average; Sade Sati sign-difference sets {11,0,1}, Dhaiya {3,7}.
- Charts: lordship of all 84 planet-lagna pairs in functional_nature_by_lagna (0 errors); yogakarakas; D2-D60 rules; D30 degrees; worked D9 example; vargottama windows; Pushkara navamsa and bhaga values (match two web sources and the Vargottama overlap).
- Dignity: exaltation/debilitation degrees, moolatrikona and combustion orbs equal engine `grahas.py`; moolatrikona signs equal Brihat Jataka 1.14.

## Errors found and fixed (before -> after)
| # | File | Before | After | Basis |
|---|---|---|---|---|
| 1 | kb_dasha_antardasha_combinations.md (hint section and source line) | "Brihat Jataka ties sub-period results to the sub-lord's position from the dasha lord"; source line claimed it confirms Vimshottari sub-period logic | Brihat Jataka ch. VIII is a different dasha (strongest of Lagna/Sun/Moon; kendra/panaphara/apoklima) and uses 1/2, 1/3, 1/7, 1/4 placement ratios to scale sub-period LENGTHS only; result-reading by house from the dasha lord is later practice, flagged [unverified] | Iyer 1885 ch. VIII stanzas 1-3 |
| 2 | kb_dasha_mahadasha_effects.md (Venus) | "Venus as lord of 1, 5, 9 or 10 (for Taurus, Libra Lagna)" | "lord of a kendra or trikona for the Lagna (e.g. 5th and 10th for Capricorn)" | Venus rules 1+6 (Taurus), 1+8 (Libra) |
| 3 | kb_dasha_gochara_and_dasha_interplay.md | Jupiter difficult in 3, 6, 8, 12 | complement of favourable set: 1, 3, 4, 6, 8, 10, 12 (one source gave 3, 6, 8, 12) | Phaladeepika favourable set 2, 5, 7, 9, 11 |
| 4 | kb_chart_yogas_catalogue.md (Raja Yoga cancellation) | "Mercury for Gemini ascendants, or Jupiter for Capricorn" as kendra+dusthana lords | Mars for Taurus (7th and 12th) | Mercury rules 1,4 for Gemini; Jupiter 3,12 for Capricorn |
| 5 | kb_chart_planets_in_signs_dignity.md (moolatrikona variants) | Venus variant "OCR unclear, 10 or 20 [unverified]"; Jupiter "none noted" | Jataka Parijata, read directly: first 20 deg for Venus (Libra), Saturn, Sun and Jupiter (Sagittarius); engine/BPHS 0-15 and 0-10 kept first | JP v1 ch. 2 slokas 26-28 |
| 6 | same file (baladi avastha) | infant and old "about half" | fractions differ by text [unverified] | no primary source |
| 7 | kb_panchang_eclipses_and_special_days.md | "partial or penumbral lunar eclipse not counted for Sutak" | "penumbral lunar eclipse" only | partial lunar eclipses are normally counted |
| 8 | kb_panchang_vedic_calendar_basics.md | Sankranti drift "about a day every few decades" caused by ayanamsa | about one day per 70 years: sidereal year 365.2564 vs tropical 365.2425 d | arithmetic (1/0.0139 = 72 y) |
| 9 | kb_lang_glossary_hi_en.md | Shakat yog "Moon in 6th/8th from Jupiter" ; Yamaganda romanised "yamghant" | adds 12th and the Jupiter-from-Moon modern form; yamgand, with note that yamghant (यमघंट) is a different yoga | consistency with yogas catalogue |
| 10 | kb_chart_nakshatra_pada_and_ascendant_notes.md | "up to several years for a 20-year Venus" ; pada passage "13 to 15 minutes" | "up to about 10 years" (6.5/13.33 x 20 = 9.75) ; "about 13 minutes on average, varies with sign and latitude" | arithmetic |
| 11 | kb_match_doshas_and_cancellations.md | BPHS verse paraphrased with explicit widowhood outcome | softened: severe outcome stated in absolute terms, not repeated as a prediction | tone rule |
| 12 | kb_match_beyond_36_points.md | 5/9 "good" with no note | notes that Ashtakoota Bhakoot scores 5/9 as 0 and that authors dispute | internal consistency |

## Structural additions (no content deleted)
- kb_chart_house_lords_in_houses.md: provenance header stating rows are synthesised, not verse paraphrase. 6th/8th/12th lords in kendras (7 rows) and trikonas (7 rows) changed from "visible and well supported (kendra)" / "carried by merit and good fortune (trikona)" to a mixed, chart-dependent reading (the templated favourable claim had no classical basis for dusthana lords). "classical authors note over-focus" for own-house flagged [unverified].
- kb_chart_planets_in_houses_vedic.md: same provenance header; node rows flagged low-confidence; Mars 6th "overcomes ill health" reworded (medical-certainty tone).
- kb_match_ashtakoota_guna_milan.md: new section "Which variant the Nakshion engine uses" (Varna, Vashya A, Tara 3/5/7, Yoni asymmetric cells, Graha Maitri scale, Gana A and gana_dosha <= 1, Bhakoot 0/7, bands) with alternatives; the 15+ disputed cells in ashtakoota-verification.md are documented as variants in the file body. Rajju-as-ninth-koota, "key five porutham" and dirah.org 12-factor claim tagged [unverified].
- Flags added: Laghu Kalyani alias (Sade Sati file), Jaimini 7-karaka Rahu tie rule, Mangal Dosha "Mars in Cancer/Leo" cancellation, Jataka Chandrika sign table (re-fetched; matches source, other authors differ).

## Tone pass
All 29 files were read for fear-based, deterministic, medical or financial certainty language. grep for guarantee/doom/death/curse/cure/diagnose: every hit is a prohibition or a hedge. Only offenders were items 11 and the Mars-6th wording above. Remedy files carry mandatory safety lines and scam warnings; Tele-MANAS 14416 / 1-800-891-4416 is correct but marked "verify before publishing" in the file.

## Remaining doubts
- Gochara favourable sets and vedhas for Sun, Moon, Mars, Mercury, Venus match standard lists but the files cite only secondary summaries; Brihat Samhita ch. 104 citation unconfirmed.
- Ashtottari nakshatra mapping and Yogini "+3" rule: Yogini rule checked (Ardra = Mangala) but no primary text; Vijnananda OCR years garbled for Sun/Moon (consistent with 6/15 and 108 total).
- Baladi avastha fractions, Deeptadi avastha list, Graha yuddha winner rule, Muhurta "Sarvartha/Amrita Siddhi" pairings, Rajju details: no primary source.
- Yoni Horse-Deer and Lion-Buffalo asymmetry may be a source typo; Vashya A vs B, Gana A vs others, Tara remainder 1: need Prokerala or Drik fixtures (engine `FIXTURE_VERIFIED` is False).
- Varna: engine and KB follow the majority; the declared source (Saravali) differs.
- Moolatrikona Moon 3-30 (engine/JP) vs 4-30 (BPHS summaries); Mercury 15-20 vs 16-20.
- Antardasha characterisations (all 81) are synthesised from natural-friendship and planet nature, as the file's school_notes state; they are consistent with that rule set but are not classical quotations. 20 spot-checked (Ketu-Sun, Venus-Sun, Sun-Saturn, Moon-Rahu, Mars-Mercury, Rahu-Jupiter, Jupiter-Venus, Saturn-Moon, Mercury-Moon and others): relation text matches the table in every case.

## Needs a human astrologer
1. kb_chart_house_lords_in_houses.md and kb_chart_planets_in_houses_vedic.md (template rows).
2. kb_dasha_antardasha_combinations.md (characterisations) and the house-from-dasha-lord reading rule.
3. kb_match_doshas_and_cancellations.md (cancellation lists) and kb_match_ashtakoota_guna_milan.md (convention choices).
4. kb_panchang_muhurta_basics.md (activity-specific nakshatra/month lists) and kb_chart_yogas_catalogue.md (Kemadruma, Neecha Bhanga variants).
5. kb_remedy_* (religious-practice accuracy; safety framing already sound) and Devanagari spellings in kb_lang_glossary_hi_en.md (spot-checked only; a native reader should skim sections 8, 10, 13-15).
