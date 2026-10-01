# Astrology Accuracy Rules - Ephemeris / Houses / Ayanamsa / Time

Owner: `astrology-domain-expert` agent. Any change to chart calculation is **T2** (see
`CLAUDE.md` verification tiers). A wrong planet position is a data-corruption bug: it is
stored in `birth_charts.chart_data`, fed to every AI answer, and silently wrong forever.

## 1. Positions come from Swiss Ephemeris. Never from the LLM.

- Every planetary longitude, sign, house cusp, aspect, nakshatra, dasha date, and transit is
  computed by `pyswisseph` in `backend/app/services/astro/` (target layout). The LLM only
  **interprets** numbers it is handed. It never computes, guesses, or "corrects" a position.
- A prompt that asks the model "what sign is Mars in for 1990-05-01?" is a bug. Compute it,
  then pass it in.
- If computation fails, the feature fails visibly. Never fall back to an LLM-generated chart.

## 2. Ephemeris files, not the silent fallback

- Call `swe.set_ephe_path(settings.EPHE_PATH)` once at startup, before any calculation.
  Ship the `.se1` files the date range needs (`sepl_18.se1`, `semo_18.se1`, `seas_18.se1`
  cover 1800-2399) and commit them or download them in the build step.
- Without the files, pyswisseph silently falls back to the Moshier model. Detect it: the
  return flag of `calc_ut` tells you which engine actually ran. On 2026-10-01 the local
  `backend/venv` returned `retflag=260` (`FLG_SPEED | FLG_MOSEPH`): **no ephemeris files are
  installed yet**, so every chart computed so far used Moshier.

```python
xx, retflag = swe.calc_ut(jd_ut, swe.MARS, swe.FLG_SWIEPH | swe.FLG_SPEED)
if not retflag & swe.FLG_SWIEPH:
    logger.warning("ephemeris_fallback", extra={"body": "mars", "retflag": retflag})
    # dev: raise. prod: allowed only if the startup self-check already warned.
```

- Startup self-check: compute one known position and log the engine in use. Fail startup in
  production if the ephemeris path is missing.
- `calc_ut` takes **UT**. Use `swe.julday(y, m, d, hour_ut)` from a UTC datetime, or
  `swe.utc_to_jd(...)` and use its UT value. Never pass local clock time.
- pyswisseph keeps global state (`set_ephe_path`, `set_sid_mode`, `set_topo`). Set sidereal
  mode per calculation, not once globally, so a tropical request cannot inherit a sidereal mode
  left behind by another request. Ephemeris math is CPU-bound: run it with
  `run_in_threadpool`, and keep all swe state changes and the calculation in the same call.

## 3. Time and place: the most common source of wrong charts

1. Resolve the place to `(lat, lon)` (LocationIQ, cached), then to an **IANA time zone**
   with `timezonefinder` (for example `Asia/Kolkata`, never `+05:30`, never `IST`).
2. Build the local datetime with `zoneinfo.ZoneInfo(tz)`. The IANA database carries historical
   offsets and DST rules, including pre-standard local mean time. Never apply today's offset
   to a 1962 birth.
3. Handle ambiguous and nonexistent local times (DST fall-back and spring-forward). Detect
   them and ask the user, or pick a documented default (`fold=0`) and store that choice.

```python
local = datetime.combine(dob, tob).replace(tzinfo=ZoneInfo(tz))
utc_offset_a = local.replace(fold=0).utcoffset()
utc_offset_b = local.replace(fold=1).utcoffset()
ambiguous_or_gap = utc_offset_a != utc_offset_b   # flag it, do not silently choose
utc = local.astimezone(timezone.utc)
```

4. Store what the user entered (`date_of_birth`, `time_of_birth`, `birth_place_name`,
   `latitude`, `longitude`, `timezone`) plus the resolved UTC instant and offset used in
   `chart_data.meta`, so a chart can be recomputed and audited.
5. Keep `tzdata` pinned and current. Old tz data gives wrong offsets for some historical
   dates and regions.
6. Validate inputs before calculating: latitude -90..90, longitude -180..180, date within
   the ephemeris range you ship, no future birth dates.

## 4. Zodiac system: tropical and sidereal, always labelled

- Support **Western tropical** and **Vedic sidereal**. The default sidereal ayanamsa is
  **Lahiri** (`swe.SIDM_LAHIRI`). The system and ayanamsa are part of every chart, cache key
  and prompt.

```python
if system == "sidereal":
    swe.set_sid_mode(swe.SIDM_LAHIRI)            # or the user's chosen ayanamsa
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
else:
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
```

- Never mix the two in one output: a sidereal Moon with tropical houses is wrong.
- The UI and the AI must say which system a sign belongs to ("Sun in Leo (tropical)",
  "Moon in Rohini, Taurus (sidereal, Lahiri)"). Sun signs differ between systems for most
  people. An unlabelled sign reads as a bug to half the audience.
- `daily_horoscopes` is unique on `(zodiac_sign, date)` with no system column. Sidereal daily
  readings need a migration that adds `zodiac_system` to the row and to the unique key first.
  See PITFALLS.

## 5. House system is explicit

- Default house systems: Placidus (`b'P'`) for Western and Whole Sign (`b'W'`) for Vedic.
  Store the house system in `chart_data.meta.house_system`. Never assume it.
- For sidereal houses use `swe.houses_ex(jd_ut, lat, lon, hsys, swe.FLG_SIDEREAL)`.
- Placidus and Koch fail near the poles (above about 66 degrees latitude): `swe.houses`
  raises `swisseph.Error` (verified 2026-10-01 at lat 75). Catch it, fall back to Porphyry or
  Whole Sign, and record the fallback in meta. Never let it 500 the request.
- Lunar nodes: true or mean node is a choice. Label it. Vedic Rahu/Ketu commonly uses
  the mean node, and Ketu is Rahu + 180 degrees.

## 6. Unknown or approximate birth time

`birth_charts.has_exact_time = false` or `time_of_birth IS NULL`:
- Calculate for 12:00 local time and flag the chart `time_unknown`.
- Do **not** compute or show the Ascendant, MC, house cusps, house placements, or anything
  time-sensitive (dasha start dates, divisional charts).
- The Moon moves about 12-15 degrees a day. If its sign (or nakshatra) changes within the
  birth date, show both candidates and say so. Do not pick one.
- The LLM context block carries `time_unknown: true`, and the prompt forbids house-based
  interpretation.

## 7. Derived values

- Sign = `int(lon // 30) % 12`, degree in sign = `lon % 30`. Normalise longitudes to [0, 360).
- Retrograde = longitude speed < 0 (requires `FLG_SPEED`).
- Aspects: one orb table in one module, applied by angular distance on the circle
  (`min(d, 360 - d)`). Never use duplicated orb constants.
- Nakshatra = `int(sidereal_lon // (360/27))`, pada = `int((sidereal_lon % (360/27)) // (360/108))`.
  Nakshatras are only valid on **sidereal** longitudes.
- Vimshottari dasha starts from the Moon's sidereal position, so it needs an exact birth time.

## 8. Versioning and recomputation

- `chart_data.meta.engine_version` (your calculation code version) plus `swe.version` plus
  system, ayanamsa and house system. Bump `engine_version` on any calculation change.
- Cached interpretations and summaries are keyed on the chart's `engine_version`. A bump
  invalidates them (see `caching_rules.md`).
- When birth data is edited, recompute `chart_data` in the same transaction and invalidate
  every cache derived from that chart.

## 9. Golden tests (required before any calculation change merges)

- `backend/tests/golden/` holds reference charts as fixtures: input (date, time, place, tz) plus
  expected longitudes, Ascendant/MC, house cusps for both systems, and the **source** of each
  expected value (for example `swetest` CLI output or astro.com, which runs the same engine).
  Never generate expected values with the code under test.
- Cover: a modern chart, a pre-1970 DST-era chart, a southern-hemisphere chart, a high-latitude
  chart (house fallback), an unknown-time chart, a DST-ambiguous local time, a Moon sign change
  on the birth date, and a date near the ephemeris range edge.
- Tolerance: 0.01 degrees for planets, 0.05 degrees for angles and cusps. A tolerance widened
  to make a test pass needs `astrology-domain-expert` sign-off.

## Checklist (calculation changes)

- [ ] No position, sign or date originates from LLM output
- [ ] Ephemeris path set, Swiss Ephemeris engine confirmed (not Moshier)
- [ ] UT conversion through IANA zone; ambiguous/gap times handled
- [ ] System, ayanamsa, house system, and node type stored and shown
- [ ] Unknown-time charts omit houses and angles
- [ ] `engine_version` bumped if any output can change, dependent caches invalidated
- [ ] Golden tests pass for both systems
