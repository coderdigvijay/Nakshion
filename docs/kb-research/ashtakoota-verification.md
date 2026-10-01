# Ashtakoota table verification (engine vs independent sources)

Scope: `backend/app/astrology/data/ashtakoota.py`, `backend/app/astrology/data/nakshatras.py` (gana, nadi, yoni per nakshatra), `backend/app/astrology/data/grahas.py` (friendships) and the scoring in `backend/app/astrology/compatibility.py` (`guna_milan`, `_tara_ok`, `_graha_maitri`). Date of check: 2026-10-01. Engine code was not edited.

Limits of this check: Prokerala and Drik Panchang publish no tables in fetchable text (Prokerala's report page and the `/astrology/kundli-matching/` URL gave a 404 or a marketing page), so the Prokerala conventions could NOT be compared directly. The comparison below uses independent published tables. Orientation everywhere: rows = bride, columns = groom, unless stated.

## Sources

- S1 Saravali / Maitreya 8 Asta Koota pages (CC BY-SA): https://saravali.github.io/astrology/koota_yoni.html , koota_vashya.html , koota_gana.html , koota_varna.html , koota_nadi.html , koota_rasi.html , koota_dina.html (the engine's declared source)
- S2 AstroSaxena: https://www.astrosaxena.com/asmh2
- S3 FreeHoroscopesOnline vashya and yoni pages: https://freehoroscopesonline.in/vashyakoota.php , /yonikoota.php
- S4 Steve Hora, Marriage Compatibility: https://stevehora.substack.com/p/marriage-compatibility
- S5 AAPS yoni chart: https://aaps.space/blog/yoni-matching-chart/
- S6 mohitmrinal.com Kundli Matching post: http://mohitmrinal.com/blog/four.php
- S7 Jagannath Hora pages (varna, gana, nadi): https://jagannathhora.com/varna-koot-spiritual-compatibility/ , /gana-koot-deva-manushya-rakshasa/ , /nadi-dosha-complete-guide/
- S8 AnytimeAstro (tara, varna): https://www.anytimeastro.com/blog/astrology/tara-koota/
- S9 Sahita Vivaha / Muhurat Choghadiya (graha maitri table): https://sahitavivahamatching.com/graha-maitri-koota-kundli-matching/ , https://www.muhuratchoghadiya.com/en/kundali-gyan/grah-maitri-kuta
- S10 FindYourFate, Sahita Vivaha, AstroNidan nakshatra-yoni lists

No classical Sanskrit text (Muhurta Chintamani, Jyotirnibandha) was read directly; every source above is a modern transcription. Independence is therefore partial: several portals copy the same legacy tables.

## Verdict

- Transcription is exact: engine YONI_MATRIX, VASHYA_MATRIX and GANA_MATRIX equal the S1 tables cell for cell (196 + 25 + 9 cells, checked programmatically).
- Per-nakshatra data (gana 27/27, nadi 27/27, yoni animal 27/27) match S1 and at least one other source.
- Varna, Graha Maitri, Bhakoot, Nadi scoring match S2/S7/S8/S9 (Varna differs from S1 itself; see below).
- Real school discrepancies exist for **Vashya (8 cells), Gana (4 cells), Yoni (2 cells vs S5), Tara (rule at remainder 1) and Varna (sign assignment, S1 vs the rest)**. None is a bug against S1; they are convention choices that a Prokerala golden pair could flip.

## Vashya (engine = S1 matrix A)

Sign-to-group assignments in the engine (`vashya_group`): Aries, Taurus = Chatushpada; Gemini, Virgo, Libra, Aquarius = Manava; Cancer, Pisces = Jalachara; Leo = Vanachara; Scorpio = Keeta; Sagittarius first 15 degrees = Manava, last 15 = Chatushpada; Capricorn first 15 = Chatushpada, last 15 = Jalachara. This matches S3, S2 and the half-sign rule (S1 omits Sagittarius). S1 lists Chatushpada as Aries, Taurus, first half of Capricorn only; the engine's extension is the correct completion of the standard rule.

Matrix B (S2, S3, S4 and many portals) differs from the engine in 8 cells:

| Bride group | Groom group | Engine (S1) | Matrix B (S2, S3, S4) |
|---|---|---|---|
| Chatushpada | Manava | 0 | 1 |
| Chatushpada | Jalachara | 0 | 1 |
| Chatushpada | Vanachara | 0.5 | 1.5 |
| Chatushpada | Keeta | 0 | 1 |
| Manava | Jalachara | 1 | 1.5 |
| Manava | Vanachara | 0.5 | 0 |
| Jalachara | Chatushpada | 0.5 | 1 |
| Jalachara | Manava | 1 | 1.5 |

The 17 other cells (including the diagonal 2s and the Vanachara and Keeta rows) agree. S4 and S3 are copies of the same table, so matrix B is perhaps 2 independent sources (S2, S3/S4) versus 1 (S1). A third table (vedikastrologer.com) differs more and is unsupported elsewhere (not counted). **Recommendation:** treat matrix A vs B as an open convention; pick by Prokerala fixtures.

## Gana (engine = S1)

| Bride | Groom | Engine (S1) | AstroSaxena (S2) |
|---|---|---|---|
| Deva | Manushya | 6 | 3 |
| Manushya | Rakshasa | 0 | 3 |
| Deva | Rakshasa | 0 | 1 |
| Rakshasa | Deva | 1 | 0 |

5 cells match (diagonal 6s, Manushya-Deva 5, Rakshasa-Manushya 0). Jagannath Hora (S7) publishes a symmetric version (Deva-Manushya 5, Manushya-Rakshasa 1, Deva-Rakshasa 0) that disagrees with both on several cells. S4 uses a 4-point Gana (not comparable to 6). The engine's `gana_dosha = gana <= 1` follows the S1 matrix. S1's matrix is the most widely reproduced, but I could not confirm it for Prokerala.

## Yoni

Nakshatra-to-yoni assignments match S1, S3/S10 for all 27 (including Pushya = Sheep, Mrigashira = Serpent, Dhanishta and Purva Bhadrapada = Lion, Uttara Ashadha = Mongoose; Abhijit is not used). The male/female flags in the engine agree with S1's male/female columns.

14x14 matrix. Engine = S1. Differences against other full tables:

| Bride | Groom | Engine (S1) | S5 (AAPS) | S6 (mohitmrinal) |
|---|---|---|---|---|
| Deer | Horse | 1 | 3 | 1 |
| Lion | Buffalo | 2 | 1 | 2 |
| Horse | Deer | 3 | 3 | 1 |
| Buffalo | Lion | 1 | 1 | 2 |
| Sheep | Serpent | 2 | 2 | 3 |
| Sheep | Dog | 1 | 1 | 2 |
| Sheep | Rat | 1 | 1 | 2 |
| Sheep | Cow | 3 | 3 | 2 |
| Sheep | Monkey | 0 | 0 | 3 |
| Sheep | Mongoose | 3 | 3 | 2 |
| Sheep | Lion | 1 | 1 | 0 |

- S5 differs in 2 cells (S5 is symmetric where S1 is not at Horse/Deer and Lion/Buffalo; engine is asymmetric at exactly those two pairs).
- S6 differs in 9 cells; its Sheep row looks like a corrupted copy of the Elephant row (Sheep-Monkey = 3 violates the sworn-enemy pair that every source lists), so S6 is probably a transcription error, not a school variant.
- All sources agree on the seven 0-score enemy pairs (Horse-Buffalo, Elephant-Lion, Sheep-Monkey, Serpent-Mongoose, Dog-Deer, Cat-Rat, Cow-Tiger) and on the 4 diagonal. The engine's `YONI_ENEMIES` assertion is consistent. Note that the engine's Horse-Deer 3 / Deer-Horse 1 asymmetry may be a typo in S1's table (S5 shows 3 and 3); worth a Prokerala fixture.
- Some websites list friendly pairs that do not match S1: Horse-Elephant and Sheep-Tiger are described as "friendly = 3", whereas S1 gives Horse-Elephant 2 and Sheep-Tiger 1. This appears in a search-result summary only; unconfirmed.

## Tara

Engine rule (`_tara_ok`): count from one nakshatra to the other inclusive; ok unless count mod 9 is 3, 5 or 7; 1.5 for each direction. This is exactly S1 (Dina koota). Variant (S8 AnytimeAstro, S2 AstroSaxena): all **odd** remainders (1, 3, 5, 7) are bad, so Janma Tara (remainder 1) also costs 1.5; in S8 the count runs girl to boy (the other direction is also scored). The conventions differ whenever a count mod 9 is 1, about 1 in 9 per direction. Two sources versus S1 and RoxyAPI/others (which say 3, 5, 7). Unresolved.

## Varna

Engine (`VARNA_RANK`): Brahmin = Cancer, Scorpio, Pisces (3); Kshatriya = Aries, Leo, Sagittarius (2); Vaishya = Taurus, Virgo, Capricorn (1); Shudra = Gemini, Libra, Aquarius (0); groom rank >= bride rank gives 1. This matches S2, S7, AstroSaxena and AnytimeAstro. **S1 itself assigns the air signs to Vaishya and the earth signs to Shudra**, the reverse of the engine. This is a conflict between the engine's declared source and its Varna data. Majority of sources (3 or 4) agree with the engine; S1 is the outlier. No code change needed unless fixtures disagree, but the engine docstring says "fully specified by the spec", so spec wording should state the assignment explicitly.

## Graha Maitri

Engine friendships (`RELATIONSHIPS`) match S9's 7x7 table cell for cell (Sun-Mercury neutral; Moon has no enemies; Mercury treats Moon as enemy; Venus treats Sun and Moon as enemies; Saturn treats Sun, Moon, Mars as enemies; Jupiter-Saturn neutral). Scale in `_graha_maitri` (5 / 4 / 3 / 1 / 0.5 / 0) matches S2 and S9. Sorting the two relations makes ("enemy","friend") = 1 and ("enemy","neutral") = 0.5, as in S9. Same-lord returns 5 (S9 agrees). Rahu and Ketu are not Moon-sign lords, so the node mapping is not exercised here.

## Bhakoot and Nadi

Bhakoot: 0 for 2/12, 5/9, 6/8 (both directions) and 7 otherwise matches S1, S2, S7. The 4-point friendly-lord variant mentioned by some pages (only a search-snippet mention) is not implemented; no matching table found. Nadi: engine's 27 nadi assignments match S1 and S7 exactly (Adi: Ashwini, Ardra, Punarvasu, Uttara Phalguni, Hasta, Jyeshtha, Mula, Shatabhisha, Purva Bhadrapada; Madhya: Bharani, Mrigashira, Pushya, Purva Phalguni, Chitra, Anuradha, Purva Ashadha, Dhanishta, Uttara Bhadrapada; Antya: the remaining nine). Same nadi gives 0, different gives 8.

## Total bands

Engine `_verdict`: 33 and above excellent, 25 to 32 good, 18 to 24 average, below 18 below_average. Matches the RoxyAPI and VedicRishi style. Alternative bands (AstroGiva and AnytimeAstro: 18 to 24, 24 to 32, 32 to 36; S4: 18, 22, 25, 28 cut-offs) differ only in labelling thresholds.

## Open questions and suggested fixtures

1. Obtain a few Prokerala (or Drik) kundali-matching outputs with all eight koota scores for pairs that discriminate the variants: a Chatushpada/Manava pair (Aries bride with Gemini groom: engine 0, matrix B 1); a Deva bride/Manushya groom pair (engine 6, S2 3); a Deer bride/Horse groom pair (Ashwini groom with Anuradha bride: engine 1, S5 3); and a pair with Tara remainder 1.
2. Decide Varna sign assignment explicitly in the spec (engine matches the majority, not S1).
3. Replace the engine's asymmetric Horse/Deer and Lion/Buffalo cells only if the fixtures say so.
4. Decide whether `gana_dosha` should still be `<= 1` if the Gana matrix changes.
