# Nakshion Astrology Engine Specification

**Status:** Build spec · **Version:** engine 2.0.0 (unknown-time output per accuracy rules section 6; compatibility `score_breakdown`) · **Date:** 2026-10-01
**Module:** `backend/app/astro/` (pure Python, no DB/Redis/LLM imports). Services call it, and it never calls services.

This engine is the single source of astrological truth. The LLM never computes or "remembers" a position. It only narrates the facts this engine emits (`llm-integration.md` §5).

---

## 1. Build vs buy decision

| Capability | Decision | Rationale |
|---|---|---|
| Planet, node and angle positions, houses, ayanamsa | **Build on pyswisseph 2.10.3.2** with the Swiss Ephemeris data files | Same core as astro.com and most professional software. Sub-arcsecond precision, 0 ms network, $0 per call. Every paid API (Prokerala, AstrologyAPI.com, FreeAstrologyAPI, VedicAstroAPI) also wraps Swiss Ephemeris, so buying adds latency, cost and a vendor outage risk with no accuracy gain. |
| Nakshatra, pada, Vimshottari dasha, D9/D10, dignities, yogas, doshas, Panchang | **Build** (deterministic tables in §2–§5) | These are pure arithmetic on sidereal longitudes, so they're cheap and fully testable. API pricing (Prokerala free tier: 5,000 credits/mo, an advanced kundli at 300 credits ≈ 16 charts/mo) can't support our volume. |
| Ashtakoota (Guna Milan) | **Build**, with golden tests generated from **Prokerala's free tier** offline | Runtime stays local. The paid API is used only to build fixtures (≈ 100 matches/month at 50 credits each). |
| Kerykeion | **Don't adopt** as a dependency (AGPL-3.0, like pyswisseph). Use it as a *reference* for SVG/aspect conventions | It adds an abstraction we'd have to work around for Vedic, and brings no licence advantage. |
| flatlib | **Don't adopt** | Unmaintained for Vedic; thin wrapper. |
| Hosted astrology APIs | **Don't adopt** for runtime | See above. Revisit only for features we choose not to build, such as KP sub-lords or a full Shadbala report. |

### 1.1 Licensing (blocking for a paid launch)

pyswisseph ≥ 2.10.1 and Swiss Ephemeris are dual-licensed: **AGPL-3.0**, or the **Swiss Ephemeris Professional License** (CHF 750 one-off for the first licence, 99-year term). A network service on AGPL code must offer its complete corresponding source to its users.

**Decision:**

- **Before monetisation (MVP / beta):** comply with AGPL. Publish the backend repository (secrets live in env vars, never in the repo) and add a "Source code" link in the footer and the API `/health/live` response.
- **Before the premium tier launches:** buy the Professional License (CHF 750 ≈ USD 830, one-off). That lets the backend go closed-source if wanted.

This is **Open Question OQ-1** in the PRD (the owner's call on open-sourcing vs paying).

---

## 2. Reference tables

All of these live in `backend/app/astro/data/*.py` as frozen constants. Any change bumps the engine **minor** version (§10).

### 2.1 Signs

| idx | Western | Rashi (emit exactly) | Devanagari | Element | Modality | Lord |
|---|---|---|---|---|---|---|
| 0 | Aries | Mesha | मेष | fire | cardinal | Mars |
| 1 | Taurus | Vrishabha | वृषभ | earth | fixed | Venus |
| 2 | Gemini | Mithuna | मिथुन | air | mutable | Mercury |
| 3 | Cancer | Karka | कर्क | water | cardinal | Moon |
| 4 | Leo | Simha | सिंह | fire | fixed | Sun |
| 5 | Virgo | Kanya | कन्या | earth | mutable | Mercury |
| 6 | Libra | Tula | तुला | air | cardinal | Venus |
| 7 | Scorpio | Vrishchika | वृश्चिक | water | fixed | Mars (Western co-ruler Pluto, not used for lordship) |
| 8 | Sagittarius | Dhanu | धनु | fire | mutable | Jupiter |
| 9 | Capricorn | Makara | मकर | earth | cardinal | Saturn |
| 10 | Aquarius | Kumbha | कुम्भ | air | fixed | Saturn |
| 11 | Pisces | Meena | मीन | water | mutable | Jupiter |

Element and modality strings are lower-case in the output.

### 2.2 Bodies

| Key (english) | Vedic `name` | SE constant | Western | Vedic |
|---|---|---|---|---|
| Sun | Surya | `SUN` | ✓ | ✓ |
| Moon | Chandra | `MOON` | ✓ | ✓ |
| Mercury | Budha | `MERCURY` | ✓ | ✓ |
| Venus | Shukra | `VENUS` | ✓ | ✓ |
| Mars | Mangala | `MARS` | ✓ | ✓ |
| Jupiter | Guru | `JUPITER` | ✓ | ✓ |
| Saturn | Shani | `SATURN` | ✓ | ✓ |
| Uranus | Uranus | `URANUS` | ✓ | emitted; frontend filters it out |
| Neptune | Neptune | `NEPTUNE` | ✓ | emitted; filtered |
| Pluto | Pluto | `PLUTO` | ✓ | emitted; filtered |
| Rahu (Western label "North Node") | Rahu | `MEAN_NODE` for Vedic, `TRUE_NODE` for Western | ✓ | ✓ |
| Ketu (Western label "South Node") | Ketu | Rahu + 180° | ✓ | ✓ (**always emitted**; gap G-09) |
| Chiron | — | `CHIRON` (needs `seas_18.se1`) | ✓ (v1) | — |

The node type is configurable (`NODE_TYPE_VEDIC=mean`, `NODE_TYPE_WESTERN=true`). Mean node for Parashari work is the common default in Indian software. Golden tests (§11) pin whichever setting the reference tool used.

### 2.3 Nakshatras (27 × 13°20′; pada = 3°20′)

| # | Name | Lord | Deity | Symbol | Nature | Gana | Nadi | Yoni |
|---|---|---|---|---|---|---|---|---|
| 1 | Ashwini | Ketu | Ashwini Kumaras | Horse's head | Kshipra (swift) | Deva | Adi | Horse ♂ |
| 2 | Bharani | Venus | Yama | Yoni | Ugra (fierce) | Manushya | Madhya | Elephant ♂ |
| 3 | Krittika | Sun | Agni | Razor / flame | Mishra (mixed) | Rakshasa | Antya | Sheep ♀ |
| 4 | Rohini | Moon | Brahma (Prajapati) | Chariot | Dhruva (fixed) | Manushya | Antya | Serpent ♂ |
| 5 | Mrigashira | Mars | Soma | Deer's head | Mridu (soft) | Deva | Madhya | Serpent ♀ |
| 6 | Ardra | Rahu | Rudra | Teardrop | Tikshna (sharp) | Manushya | Adi | Dog ♀ |
| 7 | Punarvasu | Jupiter | Aditi | Quiver of arrows | Chara (movable) | Deva | Adi | Cat ♀ |
| 8 | Pushya | Saturn | Brihaspati | Cow's udder | Kshipra (swift) | Deva | Madhya | Sheep ♂ |
| 9 | Ashlesha | Mercury | Nagas | Coiled serpent | Tikshna (sharp) | Rakshasa | Antya | Cat ♂ |
| 10 | Magha | Ketu | Pitris | Throne | Ugra (fierce) | Rakshasa | Antya | Rat ♂ |
| 11 | Purva Phalguni | Venus | Bhaga | Front legs of a bed | Ugra (fierce) | Manushya | Madhya | Rat ♀ |
| 12 | Uttara Phalguni | Sun | Aryaman | Back legs of a bed | Dhruva (fixed) | Manushya | Adi | Cow ♂ |
| 13 | Hasta | Moon | Savitar | Hand | Kshipra (swift) | Deva | Adi | Buffalo ♀ |
| 14 | Chitra | Mars | Vishwakarma | Bright jewel | Mridu (soft) | Rakshasa | Madhya | Tiger ♀ |
| 15 | Swati | Rahu | Vayu | Young shoot in the wind | Chara (movable) | Deva | Antya | Buffalo ♂ |
| 16 | Vishakha | Jupiter | Indra-Agni | Triumphal arch | Mishra (mixed) | Rakshasa | Antya | Tiger ♂ |
| 17 | Anuradha | Saturn | Mitra | Lotus | Mridu (soft) | Deva | Madhya | Deer ♀ |
| 18 | Jyeshtha | Mercury | Indra | Earring / umbrella | Tikshna (sharp) | Rakshasa | Adi | Deer ♂ |
| 19 | Mula | Ketu | Nirriti | Bundle of roots | Tikshna (sharp) | Rakshasa | Adi | Dog ♂ |
| 20 | Purva Ashadha | Venus | Apas | Elephant tusk / fan | Ugra (fierce) | Manushya | Madhya | Monkey ♂ |
| 21 | Uttara Ashadha | Sun | Vishvedevas | Planks of a bed | Dhruva (fixed) | Manushya | Antya | Mongoose ♂ |
| 22 | Shravana | Moon | Vishnu | Ear / three footprints | Chara (movable) | Deva | Antya | Monkey ♀ |
| 23 | Dhanishta | Mars | Eight Vasus | Drum | Chara (movable) | Rakshasa | Madhya | Lion ♀ |
| 24 | Shatabhisha | Rahu | Varuna | Empty circle | Chara (movable) | Rakshasa | Adi | Horse ♀ |
| 25 | Purva Bhadrapada | Jupiter | Aja Ekapada | Front of a funeral cot / swords | Ugra (fierce) | Manushya | Adi | Lion ♂ |
| 26 | Uttara Bhadrapada | Saturn | Ahir Budhnya | Back of a funeral cot / twins | Dhruva (fixed) | Manushya | Madhya | Cow ♀ |
| 27 | Revati | Mercury | Pushan | Fish / drum | Mridu (soft) | Deva | Antya | Elephant ♀ |

Computation: `idx = floor(sid_lon / (40/3))` (0-based), `pada = floor((sid_lon mod (40/3)) / (10/3)) + 1`.

`MoonNakshatra.nature` emits the English part only ("Swift", "Fierce", "Mixed", "Fixed", "Soft", "Sharp", "Movable"). `gana` emits `"Deva" | "Manushya" | "Rakshasa"`, and `nadi` emits `"Adi" | "Madhya" | "Antya"`.

### 2.4 Vedic dignities

| Planet | Exaltation (deep °) | Debilitation | Mooltrikona | Own signs |
|---|---|---|---|---|
| Sun | Aries 10° | Libra 10° | Leo 0–20° | Leo |
| Moon | Taurus 3° | Scorpio 3° | Taurus 3–30° | Cancer |
| Mars | Capricorn 28° | Cancer 28° | Aries 0–12° | Aries, Scorpio |
| Mercury | Virgo 15° | Pisces 15° | Virgo 15–20° | Gemini, Virgo |
| Jupiter | Cancer 5° | Capricorn 5° | Sagittarius 0–10° | Sagittarius, Pisces |
| Venus | Pisces 27° | Virgo 27° | Libra 0–15° | Taurus, Libra |
| Saturn | Libra 20° | Aries 20° | Aquarius 0–20° | Capricorn, Aquarius |
| Rahu | Taurus | Scorpio | — | — (configurable school; default Taurus/Scorpio) |
| Ketu | Scorpio | Taurus | — | — |

`dignity` precedence: `exalted` (whole sign) > `debilitated` > `mooltrikona` (within range) > `own` > `friendly` / `neutral` / `enemy`, by the natural relationship of the planet to the sign lord (table §2.5). Emit exactly: `exalted`, `debilitated`, `mooltrikona`, `own`, `friendly`, `neutral`, `enemy`. Uranus, Neptune and Pluto emit `neutral`.

### 2.5 Natural (naisargika) relationships

| Planet | Friends | Neutral | Enemies |
|---|---|---|---|
| Sun | Moon, Mars, Jupiter | Mercury | Venus, Saturn |
| Moon | Sun, Mercury | Mars, Jupiter, Venus, Saturn | — |
| Mars | Sun, Moon, Jupiter | Venus, Saturn | Mercury |
| Mercury | Sun, Venus | Mars, Jupiter, Saturn | Moon |
| Jupiter | Sun, Moon, Mars | Saturn | Mercury, Venus |
| Venus | Mercury, Saturn | Mars, Jupiter | Sun, Moon |
| Saturn | Mercury, Venus | Jupiter | Sun, Moon, Mars |

Rahu and Ketu use Saturn's and Mars's rows respectively (configurable).

### 2.6 Combustion orbs (angular distance from the Sun, sidereal)

Moon 12°, Mars 17°, Mercury 14° (12° when retrograde), Jupiter 11°, Venus 10° (8° when retrograde), Saturn 15°. The Sun, nodes and outer planets are never combust.

---

## 3. Core calculation

### 3.1 Inputs → UTC → Julian Day

1. Combine `date_of_birth` + `time_of_birth` (or `12:00` if unknown) into a naive local datetime.
2. Resolve the IANA zone server-side: `TimezoneFinder().timezone_at(lng=lon, lat=lat)`. Fallbacks: `certain_timezone_at`, then the closest zone. Store it in `birth_charts.timezone`.
3. `ZoneInfo(zone)`, with **historical** rules. The bundled `tzdata` package is pinned in requirements, so results don't depend on the host OS.
   - Detect a non-existent time: round-tripping `local → UTC → local` changes the wall time. Reject with `BIRTH_TIME_NONEXISTENT`.
   - Detect an ambiguous time: `fold=0` and `fold=1` give different offsets. Use `fold=0` (or the user's `dst_fold`) and set `metadata.ambiguous_time`.
   - A `utc_offset_override` replaces all of this (`metadata.tz_source="user_override"`).
   - **Pre-1970 caveat:** IANA data before 1970 is best-effort for some regions. For India it encodes LMT, Calcutta/Bombay time and IST (+05:30), including the 1942–45 War Time (+06:30). Emit `metadata.tz_confidence = "high"` (≥ 1970), `"medium"` (1900–1969), or `"low"` (< 1900 or an LMT offset). The UI shows a hint and offers the override for medium/low.
4. `jd_ut = swe.julday(y, m, d, hour_decimal_utc, swe.GREG_CAL)`. Dates before 1582-10-15 are rejected by validation (the floor is 1800-01-01 anyway).

### 3.2 Ephemeris setup

- Ship `sepl_18.se1`, `semo_18.se1` and `seas_18.se1` (years 1800–2399, ≈ 2 MB total) in `backend/ephe/`, and call `swe.set_ephe_path(EPHE_DIR)` once at startup.
- Flags: `FLG_SWIEPH | FLG_SPEED`. At startup, assert that the returned flag doesn't fall back to Moshier (`retflag & FLG_SWIEPH`). If it does, fail the readiness probe, because accuracy would silently degrade.
- **Thread-safety:** pyswisseph keeps global state (ephe path, sidereal mode, topocentric). The engine:
  - never calls `set_sid_mode` per request;
  - computes sidereal positions as `sid = (trop − ayanamsa) mod 360`, with `ayanamsa = swe.get_ayanamsa_ex_ut(jd_ut, FLG_SWIEPH | FLG_SIDEREAL)[1]` under the fixed process-wide `set_sid_mode(SIDM_LAHIRI)` set at startup. A different ayanamsa (v2) runs in the **dedicated engine thread** (below);
  - runs all `swe.*` calls on a single-worker `ThreadPoolExecutor` (`astro_executor`), so calls are serialised and the event loop is never blocked. A natal chart is roughly 5 ms of CPU; even on 0.1 vCPU (Render free) it stays under 100 ms.

### 3.3 Positions

For each body: `xx, ret = swe.calc_ut(jd_ut, body, flags)` → `lon = xx[0]`, `lat = xx[1]`, `speed = xx[3]` (deg/day). `retrograde = speed < 0` (never for the Sun or Moon; the mean node is always retrograde, so for nodes `retrograde` is emitted as `true` by convention).

### 3.4 Houses and angles

- `cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b'P')`. ASC = `ascmc[0]`, MC = `ascmc[1]`.
- **Western default: Placidus.** At |lat| > 66° Placidus is undefined; fall back to **Porphyry** and set `metadata.house_system = "porphyry_fallback"`. [v1-add] user choice: Placidus, Whole Sign, Equal, Koch.
- **Vedic: Whole Sign from the sidereal ascendant** (house n = sign (lagna_idx + n − 1) mod 12). [v2] Bhava Chalit (Sripati) as an optional view.
- A planet's house:
  - Western: find the cusp interval containing its longitude (handle the wrap at 360°).
  - Vedic: `((sign_idx − lagna_idx) mod 12) + 1`.

### 3.5 Unknown birth time (`time_of_birth=null`) - engine 2.0.0

Follows `astrology_accuracy_rules.md` section 6: **nothing time-sensitive is presented as fact.**

1. Compute positions at local 12:00 (`metadata.time_basis = "local_noon"`).
2. Probe **every body** (tropical and sidereal) at local 00:00 and 23:59. A sign change sets `approximate: true` and `candidates: [...]` on that planet (Western and Vedic entries) and on `sun_sign` / `moon_sign`. `moon_nakshatra` carries `approximate`, `candidates`, `rashi_changes`.
3. **Removed from the output:**
   - `houses` is `[]`; every `planets[].house` is `null`; `sun_sign` / `moon_sign` have no `house`; `mc` is omitted; `rising_sign = {sign: "Unknown", degree: 0, approximate: true}`. `metadata.house_system = "none"`, `metadata.houses_available = false`, `metadata.lagna_basis = "none"`. Angles are excluded from aspects. (The earlier solar whole-sign / Chandra-lagna pseudo-houses are gone.)
   - `vedic.lagna = null`, `vedic.houses_available = false`, every `vedic.planets[].house` is `null`, `house_lords = []`, `functional_benefics = functional_malefics = []`, `yogakaraka = null`, `navamsa_d9` / `dashamsa_d10` are omitted, graha-drishti entries have `to_house = null` (signs and occupants kept).
   - Lagna-dependent yogas are not computed: Ruchaka, Bhadra, Hamsa, Malavya, Sasa, Raja, Dhana, Viparita Raja, Neecha Bhanga. Moon- and sign-based yogas (Gajakesari, Budhaditya, Chandra-Mangala, Kemadruma, Kaal Sarp) and Mangal Dosha **from the Moon only** (`manglik.from_lagna = null`) remain, each with `approximate: true`. Yoga strength ignores house placement.
   - `vedic.suppressed = {reason, items[]}` and `metadata.suppressed_when_time_unknown` list what was withheld; `vedic.moon_range_sidereal = [lo, hi]` is the Moon's sidereal longitude at local 00:00 and 23:59.
4. **Dasha stays** (Moon-based) but `dasha.approximate = true`, `maha_dasha` / `antar_dasha` / `pratyantar_dasha`, every `timeline[]` period and every `antar[]` entry carry `approximate: true`, and `dasha.approximate_note` states the uncertainty. The Moon moves ~13 deg/day (about one whole nakshatra), so the balance at birth can shift by up to the starting lord's whole period (7-20 years) and even the running Mahadasha lord can differ. `dasha.candidates = [{moon_longitude, maha_dasha, antar_dasha, balance_at_birth_years}]` gives the two day-end extremes. The LLM must not quote dasha dates as exact.
5. `metadata.approximate_time = true`.

When `has_exact_time=false` but a time is given, compute normally and set `approximate` on the angles, houses and lagna only.

---

## 4. Western layer

### 4.1 Aspects

| Aspect | Angle | Orb (default) | Orb with Sun/Moon involved | Included |
|---|---|---|---|---|
| conjunction | 0 | 8 | 10 | ✓ |
| opposition | 180 | 8 | 10 | ✓ |
| trine | 120 | 7 | 8 | ✓ |
| square | 90 | 7 | 8 | ✓ |
| sextile | 60 | 5 | 6 | ✓ |
| quincunx | 150 | 3 | 3 | v1 (off by default) |
| semi-sextile | 30 | 2 | 2 | v1 (off) |

- Points: the 10 planets + North Node + ASC and MC (angles only when the time is known; for angles, orb = default − 2).
- `orb = |separation − angle|`, rounded to 2 decimals. Within ±0.01° counts as exact.
- `applying`: the orb decreases over the next hour, computed from `speed`.
- Output is sorted by orb ascending. The pair order is canonical (body list order).

### 4.2 Chart signature (feeds the rules layer)

These are computed and stored under `chart_data.western_summary` [v1-add]:

- element and modality balance (Sun, Moon and ASC weighted 2, the other planets 1)
- dominant planet (most aspects within 3° + angular + dignity)
- chart ruler (lord of the ASC sign, traditional rulers)
- stelliums (≥ 3 planets in a sign or house)
- aspect patterns: grand trine, T-square, yod (v1)

---

## 5. Vedic layer

### 5.1 Planets

`VedicPlanet` per §9. `degree` is the **within-rashi** degree (0–30). `speed` is in deg/day.

### 5.2 Vimshottari dasha

- Order and years: Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17 (total 120).
- Moon sidereal longitude → nakshatra index `n`. Starting lord = the lord of `n`. `elapsed_frac = (moon_sid mod 13.3333…) / 13.3333…`. Balance at birth = `(1 − elapsed_frac) × years[lord]`.
- Mahadasha start (virtual) = `birth − elapsed_frac × years[lord]`. Every following MD starts where the previous one ends.
- Antardasha within an MD of lord L: the sequence starts at L and cycles. Duration = `years[MD] × years[AD] / 120`. Pratyantardasha recurses one level further.
- **Year length:** `DASHA_YEAR_DAYS = 365.25` (configurable; golden tests pin it to match the reference tool's setting).
- Output for `dasha` (MVP shape): the current MD and AD as of **now (UTC)**, with dates as `YYYY-MM-DD` (UTC date of the boundary instant) and `duration_years` as the MD's full years. [v1-add] `pratyantar_dasha` and `timeline: [{lord, start, end, antar: [...]}]` (all 9 MDs × 9 ADs). `chart_data` is static, but "current" moves on, so the **API layer recomputes the `current` pointers on read** from `timeline` (cheap). Don't trust a stored `current`.

### 5.3 Divisional charts

- **D9 Navamsa:** `d9_sign = floor(sid_lon × 9 / 30) mod 12`. (Equivalent to the classical rule: movable signs start from the same sign, fixed from the 9th, dual from the 5th.) `d9_degree = (sid_lon × 9) mod 30`.
- **D10 Dashamsa:** `part = floor((sid_lon mod 30) / 3)`, `s = sign_idx`. `start = s` if `s` is even (odd signs: Aries=0, Gemini=2, …), else `s + 8`. `d10_sign = (start + part) mod 12`.
- Lagna is transformed the same way. Planet houses in a varga are counted from the varga lagna.
- [v2] D2, D3, D4, D7, D12, D16, D20, D24, D30, D60 via a generic varga table.

### 5.4 House lords, functional nature, yogakaraka

- `house_lords`: for each house 1–12 (whole sign), the lord of that sign, the house the lord occupies, and the lord's rashi.
- **Functional nature** (simplified Parashari, per lagna). For each of the 7 classical planets, sum over the houses it owns:
  - trikona (1, 5, 9): +2. The 1st house is both kendra and trikona: count +2 once.
  - kendra (4, 7, 10): natural benefics (Jupiter, Venus, Mercury, waxing Moon) score −1 (kendradhipati dosha); natural malefics (Sun, Mars, Saturn) score +1.
  - 3, 6, 11: −1 each. 6 and 8 (and 12): −2 each. The 8th-lord penalty is waived when the planet is also the lagna lord.
  - 2 and 12 alone: 0 (neutral; "takes the result of its other house").

  Score > 0 → `functional_benefics`; score < 0 → `functional_malefics`. A planet owning both a kendra and a trikona (excluding the 1st house) is flagged as `yogakaraka` [v1-add]. Rahu and Ketu are excluded.
  > This must be reviewed by a practising astrologer against the standard per-lagna tables. A fixed table of 12 expected outputs is kept in `tests/astro/fixtures/functional_nature.json`.

### 5.5 Graha drishti (Vedic aspects, whole-sign)

All planets aspect the 7th sign from themselves. Mars also aspects the 4th and 8th, Jupiter the 5th and 9th, Saturn the 3rd and 10th. Rahu and Ketu: none by default (school-dependent; config `NODE_ASPECTS="none"|"5_7_9"`). Emitted in `chart_data.vedic.aspects` [v1-add] so the frontend's `calculateVedicAspects` can be deleted.

### 5.6 Yogas and doshas (MVP set)

Each yoga is emitted as `{name, present, strength: "strong"|"moderate"|"weak", description, factors: [...] }` (`factors` is [v1-add]). Strength combines the dignity of the participating planets, combustion (−1 level), and house placement (kendra/trikona +1 level).

| Name (emit exactly) | Rule |
|---|---|
| Gajakesari Yoga | Jupiter in a kendra (1/4/7/10) from the Moon |
| Budhaditya Yoga | Sun and Mercury in the same sign. Strength is weak if Mercury is combust within 4° |
| Ruchaka Yoga / Bhadra Yoga / Hamsa Yoga / Malavya Yoga / Sasa Yoga | Mars / Mercury / Jupiter / Venus / Saturn in own or exaltation sign **and** in a kendra from the lagna |
| Raja Yoga | A kendra lord and a trikona lord (different planets) conjunct, in mutual graha drishti, or in sign exchange. One entry per pair in `factors` |
| Dhana Yoga | The lord of the 2nd or 11th conjunct with or exchanging with the lord of the 1st, 5th or 9th |
| Viparita Raja Yoga | The lord of the 6th, 8th or 12th placed in the 6th, 8th or 12th (different from its own) |
| Neecha Bhanga Raja Yoga | A debilitated planet whose debilitation-sign lord, or exaltation-sign lord, is in a kendra from the lagna or Moon |
| Chandra-Mangala Yoga | Moon and Mars conjunct |
| Kemadruma Yoga | No planet (excluding Sun, Rahu, Ketu) in the 2nd or 12th from the Moon, **and** none in a kendra from the Moon (the cancellation is built in) |
| Kaal Sarp Dosha | All seven classical planets on one side of the Rahu–Ketu axis (strictly between them). `strength` = "strong" if none is conjunct a node within 1° |
| Mangal Dosha | Mars in the 1st, 2nd, 4th, 7th, 8th or 12th house from the lagna (and, separately, from the Moon). `description` lists which references. [v2] classical cancellations |

`sade_sati`:

- `active` if transiting sidereal Saturn is in the 12th, 1st or 2nd sign from the natal Moon sign at *request time*. Like the dasha pointers, this is recomputed on read.
- `phase` ∈ `"rising" | "peak" | "setting" | "none"`.
- [v1-add] `start` and `end` dates of the current or next period, found by scanning Saturn sign ingresses (§6.2).

### 5.7 Panchang (v1)

For a date and location, using sunrise as the day boundary (Hindu civil day):

- Sunrise/sunset: `swe.rise_trans(jd, SUN, rsmi=CALC_RISE|BIT_DISC_CENTER, geopos, atpress=1013.25, attemp=15)`. (Disc centre with refraction; document the convention and pin it in golden tests against Drik-style outputs.)
- **Tithi:** `floor(((moon_sid − sun_sid) mod 360) / 12) + 1` (1–30). 1–15 is Shukla and 16–30 is Krishna paksha. End time is found by root-finding (§6.2).
- **Nakshatra:** the Moon's (§2.3). **Yoga:** `floor(((sun_sid + moon_sid) mod 360) / (40/3)) + 1` (27 names). **Karana:** `k = floor(((moon − sun) mod 360) / 6)` (0–59). k=0 is Kimstughna; k=1…56 cycle Bava, Balava, Kaulava, Taitila, Garaja, Vanija, Vishti; k=57, 58, 59 are Shakuni, Chatushpada, Naga.
- **Vara:** the weekday at sunrise.
- **Rahu Kaal:** split sunrise→sunset into 8 equal parts. Use part #: Mon 2, Tue 7, Wed 5, Thu 6, Fri 4, Sat 3, Sun 8. (Gulika and Yamaganda: v2.)

---

## 6. Transits and timing (prediction facts)

### 6.1 Daily sky

Computed once per UTC date and cached as `transits:{YYYY-MM-DD}`, shared by every user:

- tropical and sidereal positions at 00:00 and 12:00 UTC
- Moon phase and illumination: `swe.pheno_ut`
- void-of-course Moon (no major Ptolemaic aspect to Sun…Saturn before its sign ingress)
- sign ingresses and stations within the day

### 6.2 Event finding

A generic root finder, `find_events(f, t0, t1, step)`: sample `f(t)` (a signed angular difference) at `step`, then bisect each sign change down to 1 minute. Steps: Moon 2 h, Sun/Mercury/Venus/Mars 1 day, Jupiter and beyond 3 days. Used for ingresses, exact transit aspects, tithi ends, and stations (sign change of `speed`).

### 6.3 Personal transit factors (per chart, per day)

**Western:** transiting Sun…Pluto make aspects (conj, opp, sq, tri, sext) to natal Sun, Moon, Mercury…Saturn, ASC and MC. Orbs: transiting Moon 3°; Sun, Mercury, Venus and Mars 2°; Jupiter and Saturn 2°; Uranus, Neptune and Pluto 1.5°. Include `applying`, `exact_at` (if within ±30 days for slow planets), `window_start` and `window_end` (when the orb enters and leaves).

**Vedic:**

- gochara of the slow planets (Jupiter, Saturn, Rahu, Ketu) by house from the natal Moon sign and from the lagna
- Moon's transit house today (from the natal Moon)
- current MD/AD/PD lords, and whether the transiting dasha lord occupies or aspects natal key houses
- [v2] Ashtakavarga bindus for the transit sign

### 6.4 Rules / scoring layer → `Factor`

Every computed fact that might be narrated becomes a `Factor` with a **stable ID**. The LLM must cite these IDs (`llm-integration.md` §5).

```python
@dataclass(frozen=True)
class Factor:
    id: str            # e.g. "N.VENUS.SIGN.LIBRA", "N.SATURN.H7", "A.MOON.SQUARE.SATURN",
                       #      "T.SATURN.CONJ.N.MOON", "V.MD.JUPITER", "V.AD.SATURN", "Y.GAJAKESARI",
                       #      "D.MANGAL", "V.SADESATI.PEAK", "P.TITHI.EKADASHI"
    kind: Literal["natal","aspect","transit","dasha","yoga","dosha","panchang","synastry"]
    label: str         # human text: "Transiting Saturn conjunct natal Moon (orb 0.8°, applying)"
    topics: tuple[str, ...]   # subset of {"self","love","career","money","health","family","spiritual","timing"}
    weight: float      # 0..1 significance
    valence: float     # -1..+1 (challenging .. supportive), heuristic
    window: tuple[str, str] | None   # ISO dates for timed factors
    kb_keys: tuple[str, ...]  # retrieval keys, e.g. ("saturn moon conjunction transit", "sade sati")
```

Weight heuristics, defined in `astro/scoring.py` and covered by unit tests:

- `base(planet)`: Sun, Moon, ASC ruler 1.0; Saturn, Jupiter 0.9; Mars, Venus, Mercury 0.7; nodes 0.8; outer planets 0.6 (Western only).
- Transit: `base(transiting) × base(natal point) × (1 − orb/max_orb)^1.5 × speed_factor`. `speed_factor` is 1.0 for slow planets, 0.4 for the Sun and inner planets, and 0.15 for the Moon, so daily Moon facts only matter for daily readings.
- Dasha: MD lord 1.0, AD lord 0.8, PD 0.4. ×1.2 when the transiting dasha lord activates its natal house.
- Topic mapping: a fixed table maps houses (1 self, 2 money, 4 home/family, 5 romance/children, 6 health/work, 7 partner, 8 shared resources/transformation, 10 career, 11 gains, 12 spiritual/loss) and planets (Venus love/money, Mars energy/conflict, Saturn career/discipline, Jupiter growth/fortune, Moon emotions/health, Mercury communication) to topics.
- `select_factors(chart, date, topic, k)` returns the top-k by `weight × topic_match`, always including the current MD/AD factors (Vedic) and the top transit.

---

## 7. Compatibility

### 7.1 Western synastry scoring (all relationship types)

Inter-aspects are chart1 planet → chart2 planet, using the natal aspect set and orbs **minus 1°**. Angles are included only when both times are known. Each pair contributes `h(aspect, p1, p2) × (1 − orb/max_orb)`:

- `h`: trine +1.0, sextile +0.8, conjunction +0.7 (−0.4 if either is Saturn, Mars or Pluto, unless the other is Venus or Moon, which gives +0.3, "magnetic but demanding"), square −0.7, opposition −0.3.

| Category key | Pairs considered (either direction) |
|---|---|
| emotional | Moon–Moon, Moon–Sun, Moon–Venus, Moon–ASC, Moon–Saturn |
| communication | Mercury–Mercury, Mercury–Sun, Mercury–Moon, Mercury–Jupiter, Mercury–Saturn |
| romance | Venus–Venus, Venus–Sun, Venus–Moon, Venus–Mars, Venus–ASC |
| passion | Mars–Mars, Mars–Venus, Mars–Sun, Mars–Pluto, Mars–ASC |
| long-term | Saturn–Sun, Saturn–Moon, Saturn–Venus, Jupiter–Sun, Jupiter–Venus, Node–Sun/Moon/Venus |

`category_score = clamp(5 + 5 × tanh(Σ / 2.0), 0, 10)`, rounded to 0.1. A small element-compatibility term is added to emotional and communication: ±0.5 for the Moon and Mercury elements (same or complementary element +, square-element −).

`overall_western = 0.25×emotional + 0.2×communication + 0.2×romance + 0.15×passion + 0.2×long-term`. For non-romantic types, the weights are 0.3, 0.3, 0.1, 0.1, 0.2.

`synastry_aspects` = the top 10 by |contribution|. `strengths` and `challenges` are seeded from the top 3 positive and top 3 negative pairs. The LLM phrases them; it doesn't choose them.

### 7.2 Ashtakoota / Guna Milan (romantic only; v1)

This is computed from both charts' **sidereal Moon** (rashi and nakshatra). Output:

```ts
AshtakootaResult {
  total: number;            // 0–36 (headline orientation)
  max: 36;
  kootas: Array<{ name: "Varna"|"Vashya"|"Tara"|"Yoni"|"Graha Maitri"|"Gana"|"Bhakoot"|"Nadi"; score: number; max: number; note: string }>;
  orientation: "self_as_groom" | "self_as_bride" | "unspecified";
  alternate_total?: number; // when unspecified: the other orientation's total
  nadi_dosha: boolean; bhakoot_dosha: boolean; gana_dosha: boolean;
  verdict: "excellent" | "good" | "average" | "below_average";  // ≥33, 25–32, 18–24, <18
  approximate: boolean;     // either Moon nakshatra uncertain (unknown time)
}
```

Maximum points: Varna 1, Vashya 2, Tara 3, Yoni 4, Graha Maitri 5, Gana 6, Bhakoot 7, Nadi 8.

These rules are fully specified here:

- **Tara (3):** count from the bride's nakshatra to the groom's (inclusive) and take `mod 9`. Remainders 3, 5 and 7 are inauspicious. Score 1.5 for each direction (bride→groom, groom→bride) that is auspicious.
- **Graha Maitri (5):** the relationship of the two Moon-sign lords (§2.5). Same lord or mutual friends 5; friend + neutral 4; both neutral 3; friend + enemy 1; neutral + enemy 0.5; mutual enemies 0.
- **Bhakoot (7):** the position of the groom's Moon sign counted from the bride's (and vice versa). Pairs 1/1, 3/11, 4/10 and 7/7 score 7. Pairs 2/12, 5/9 and 6/8 score 0, and set `bhakoot_dosha`.
- **Nadi (8):** different nadi 8; same nadi 0, and set `nadi_dosha`.
- **Varna (1):** varna by Moon rashi: Brahmin (Cancer, Scorpio, Pisces) > Kshatriya (Aries, Leo, Sagittarius) > Vaishya (Taurus, Virgo, Capricorn) > Shudra (Gemini, Libra, Aquarius). Score 1 if the groom's rank ≥ the bride's, else 0.
- **Yoni (4):** yoni from §2.3. Same animal 4. Sworn-enemy pairs score 0: Horse–Buffalo, Elephant–Lion, Sheep–Monkey, Serpent–Mongoose, Dog–Deer, Cat–Rat, Cow–Tiger. **All other pairs come from the 14×14 matrix in `data/ashtakoota.py`.**
- **Vashya (2) and Gana (6):** **from the matrices in `data/ashtakoota.py`.** Classical sources and popular software differ slightly on these matrices. The implementer must (a) transcribe the matrices from one named reference (record the citation in the file header), and (b) pass the 30 golden match fixtures generated from Prokerala's `kundli-matching` endpoint, with 0 tolerance per koota. If a fixture disagrees with the transcribed table, the fixture's provider convention wins and the deviation is documented.

**Orientation.** The kootas are classically gendered (bride/groom). The product doesn't ask for gender. Rules:

1. If the request supplies roles (`self_ashtakoota_role`), use them.
2. Otherwise compute both orientations. The headline `total` is the **lower** of the two (conservative), and `alternate_total` is the other. The UI explains that traditional matching assigns roles.

This also handles same-sex couples without a forced binary choice. It's **OQ-4**.

**Framing rule:** the score is never presented as a verdict on whether a relationship "will work". Copy guidance is in PRD §6.6.

### 7.3 Blended overall score (romantic)

`overall_western` is the **weighted mean of the five category scores** (weights in 7.1; it is not an average of the headline numbers). If `ashtakoota` is available: `overall = round(0.5 × overall_western + 0.5 × (total/36 × 10), 1)`; otherwise `overall = overall_western`, so the overall can sit below or above individual categories. Every response carries `score_breakdown` (weights, category scores, weighted contributions, blend, formula, plain-language `explanation`, and `overall_range` when the Moon is ambiguous). Ashtakoota is computed for romantic pairs only; its Vashya/Gana/Yoni tables are flagged `tables_fixture_verified: false` until the Prokerala fixtures exist. With an unknown birth time all eight kootas are still Moon-based: the headline is for local noon and `total_range` spans the day.

`compatibility_data.method_version = "compat-1.0"`.

---

## 8. Daily sign horoscopes (generic, by sun sign)

### 8.1 Solar-house method

For a requested sign S, house 1 = S (whole sign). Using the daily sky (§6.1):

- the Moon's house
- the houses being transited by the Sun, Mercury, Venus and Mars
- aspects made today
- ingresses

These are turned into `transit_data.solar_house_focus` plus up to 6 `Factor`s for the LLM.

### 8.2 Vedic variant (v1 `system=vedic&basis=moon`)

The same procedure with sidereal positions and S = Moon rashi.

### 8.3 Lucky number and colour (deterministic, so they don't change on refresh)

- `lucky_number = 1 + (int(sha256(f"{sign}:{date}").hexdigest(), 16) mod 9)`.
- `lucky_color` = a lookup by **weekday ruler**: Sun→"Gold", Moon→"Silver white", Mars→"Red", Mercury→"Green", Jupiter→"Yellow", Venus→"Pink", Saturn→"Navy blue". Rotate between 2 shades per ruler using hash parity.

These are labelled "for fun" in the UI, because they have no classical derivation (honesty requirement in PRD §6.4).

---

## 9. `chart_data` JSON schema (persisted in `birth_charts.chart_data`, returned verbatim)

This satisfies `frontend/src/types/index.ts` exactly. `[v1]` marks additive fields.

```jsonc
{
  "sun_sign":    { "sign": "Cancer", "degree": 28.41, "house": 9, "element": "water", "modality": "cardinal", "approximate": false },
  "moon_sign":   { "sign": "Taurus", "degree": 3.12, "house": 7, "element": "earth", "modality": "fixed", "approximate": false },
  "rising_sign": { "sign": "Scorpio", "degree": 17.9, "element": "water", "modality": "fixed", "approximate": false },
  "mc":          { "sign": "Leo", "degree": 24.5, "element": "fire", "modality": "fixed" },
  "planets": [
    { "name": "Sun", "sign": "Cancer", "degree": 28.41, "house": 9, "retrograde": false,
      "longitude": 118.41, "speed": 0.954 }                      // [v1] longitude (0–360 tropical), speed
    // Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, North Node, South Node (Chiron v1)
  ],
  "houses": [ { "number": 1, "sign": "Scorpio", "degree": 17.9 } /* … 12 */ ],
  "aspects": [ { "planet1": "Sun", "planet2": "Saturn", "type": "square", "angle": 90, "orb": 1.24, "applying": true } ],
  "metadata": {
    "house_system": "placidus",            // | "porphyry_fallback" | "solar_whole_sign"
    "approximate_time": false,
    // [v1] provenance — required for reproducibility and golden tests
    "engine_version": "1.0.0",
    "ephemeris": "swieph",                 // never "moshier" in prod
    "zodiac_western": "tropical",
    "ayanamsa": "lahiri",
    "node_type_western": "true", "node_type_vedic": "mean",
    "utc_datetime": "1994-07-21T08:35:00Z",
    "jd_ut": 2449554.857639,   // example values are illustrative; sidereal = tropical − ayanamsa (e.g. Sun 118.41 − 23.76 = 94.65 → Karka 4.65°)
    "timezone": "Asia/Kolkata", "utc_offset_minutes": 330,
    "tz_source": "zoneinfo", "tz_confidence": "high", "ambiguous_time": false,
    "lagna_basis": "ascendant"            // | "moon"
  },
  "vedic": {
    "ayanamsa_value": 23.7613,             // degrees, decimal
    "lagna": { "rashi": "Tula", "rashi_english": "Libra", "degree": 24.14, "nakshatra": "Vishakha", "pada": 2 },
    "planets": [
      { "name": "Surya", "english": "Sun", "rashi": "Karka", "rashi_english": "Cancer", "degree": 4.65,
        "nakshatra": "Pushya", "pada": 1, "nakshatra_lord": "Saturn", "house": 10,
        "retrograde": false, "combust": false, "dignity": "neutral", "speed": 0.954,
        "longitude": 94.65 }                                    // [v1] sidereal 0–360
      // Surya, Chandra, Mangala, Budha, Guru, Shukra, Shani, Rahu, Ketu (+ Uranus, Neptune, Pluto)
    ],
    "moon_nakshatra": { "name": "Ashwini", "pada": 3, "lord": "Ketu", "deity": "Ashwini Kumaras", "symbol": "Horse's head",
                        "nature": "Swift", "gana": "Deva", "nadi": "Adi", "yoni": "Horse" /* [v1] */ },
    "dasha": {   // illustrative values only — not derived from the example Moon
      "maha_dasha":  { "current": "Saturn", "start": "2019-03-02", "end": "2038-03-02", "duration_years": 19 },
      "antar_dasha": { "current": "Mercury", "start": "2025-11-05", "end": "2028-07-14" },
      "approximate": false,                                     // [v1]
      "timeline": [ /* [v1] { lord, start, end, antar: [{lord,start,end}] } × 9 */ ]
    },
    "yogas": [ { "name": "Gajakesari Yoga", "present": true, "strength": "moderate", "description": "…", "factors": ["N.JUPITER.KENDRA_FROM_MOON"] } ],
    "house_lords": [ { "house": 1, "lord": "Venus", "lord_in_house": 9, "lord_rashi": "Mithuna" } /* × 12 */ ],
    "functional_benefics": ["Moon", "Jupiter", "Sun"],
    "functional_malefics": ["Mercury", "Venus"],
    "yogakaraka": null,                                         // [v1] e.g. "Saturn"
    "sade_sati": { "active": false, "phase": "none" },
    "aspects": [ { "from": "Saturn", "to_house": 10, "to_planets": ["Moon"] } ],   // [v1] graha drishti
    "navamsa_d9":   { "lagna": { "rashi": "Simha" }, "planets": [ /* VedicPlanet, house relative to D9 lagna, nakshatra fields = D1 values */ ] },
    "dashamsa_d10": { "lagna": { "rashi": "Tula" },  "planets": [ /* … */ ] }
  },
  "western_summary": { /* [v1] §4.2 */ }
}
```

Field rules:

- All degree fields: float, rounded to 2 decimals (4 for `ayanamsa_value`).
- `ChartSignData.degree` is the within-sign degree.
- `sun_sign`, `moon_sign`, `rising_sign` and the Western `planets` are **tropical**. Everything under `vedic` is **sidereal**.
- The planet `name` in the Western list uses the English names, with "North Node" / "South Node" for the nodes. The Vedic list uses `english: "Rahu" | "Ketu"`.
- Time-dependent pointers (`dasha.*.current`, `sade_sati` incl. `start`/`end`) are **recomputed on read** (`refresh_time_dependent`); stored values are a snapshot.
- Unknown birth time changes the shape (section 3.5): `houses = []`, `house = null`, `vedic.lagna = null`, no D9/D10. Consumers must check `metadata.houses_available`.

---

## 10. Versioning

- `ENGINE_VERSION` uses semver.
  - **Major:** a change in positions or house math, or a schema-breaking change. Triggers lazy recompute (`api-contract.md` C3).
  - **Minor:** new fields, yoga rules, or table corrections. Recomputed lazily on the next chart read; no forced migration.
  - **Patch:** text and descriptions only.
- Every stored chart carries `metadata.engine_version`. A one-off `scripts/recompute_charts.py --below 2.0.0` exists for bulk upgrades, batched at 50 rows per transaction.

---

## 11. Validation: golden tests (release gate)

Location: `backend/tests/astro/golden/`. These run in CI on every PR that touches `app/astro/`.

| Suite | Reference | Cases | Tolerance |
|---|---|---|---|
| Planet positions (tropical) | astro.com chart outputs (Swiss Ephemeris), with Astro-Databank AA-rated public birth data | 30 charts spanning 1850–2025, both hemispheres, high latitude, DST-edge times | ±0.01° (36″) planets, ±0.02° Moon |
| Angles and houses | same | 30 | ASC/MC ±0.05°; Placidus cusps ±0.1° |
| Sidereal / Lahiri | Jagannatha Hora 8 (Lahiri, mean node) exports | 30 (20 Indian births) | planets ±0.02°, ayanamsa ±0.001°, nakshatra and pada exact |
| Vimshottari | Jagannatha Hora | 30 | MD/AD boundaries ±1 day (same year-length setting) |
| D9 / D10 | Jagannatha Hora | 30 | sign exact |
| Ashtakoota | Prokerala `kundli-matching` (free tier, generated offline) | 30 pairs | each koota exact |
| Panchang | Drik-style daily panchang for 5 cities × 12 dates | 60 | tithi/nakshatra/yoga/karana names exact; sunrise ±2 min; Rahu Kaal ±2 min |
| Timezones | hand-built fixtures: India 1942–45 War Time, US DST gap 02:30, DST fold 01:30, Nepal +05:45, pre-1900 LMT | 15 | offset exact; error codes exact |
| Unknown time | 10 charts | — | Moon-change flags correct, rising "Unknown", Chandra Lagna used |

- Fixtures are JSON (`input`, `expected`, `source`, `source_settings`, `retrieved_at`). They are generated by hand or by script **outside CI**, so CI never calls external services.
- Property tests (Hypothesis): any random date or location returns 12 houses, 27-nakshatra indices, a dasha timeline totalling 120 years ±1 day, D9 consistency with the formula, and no NaNs.
- Performance test: computing a full natal chart (Western + Vedic + D9/D10 + timeline) stays under 50 ms on the CI runner, measured with `pytest-benchmark`.
