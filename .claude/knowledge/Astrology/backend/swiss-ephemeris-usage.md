# Swiss Ephemeris (pyswisseph) Usage

## Basic calculation
```python
import swisseph as swe
jd = swe.julday(year, month, day, hour_decimal)  # Julian Day
result = swe.calc_ut(jd, swe.SUN)  # Calculate planet position
```

## Return structure
- `result[0][0]` = ecliptic longitude (0-360°)
- `result[0][3]` = daily speed (negative = retrograde)

## House calculation
```python
houses, ascmc = swe.houses(jd, lat, lon, b'P')  # 'P' = Placidus
# houses = tuple of 12 house cusps
# ascmc[0] = Ascendant, ascmc[1] = MC (Midheaven)
```

## Planet IDs
swe.SUN=0, swe.MOON=1, swe.MERCURY=2, swe.VENUS=3, swe.MARS=4,
swe.JUPITER=5, swe.SATURN=6, swe.URANUS=7, swe.NEPTUNE=8, swe.PLUTO=9,
swe.TRUE_NODE (North Node)

## Longitude to sign
```python
sign_index = int(longitude / 30) % 12
degree_in_sign = longitude % 30
```

## Timezone handling
Always convert birth time to UTC before calculating:
```python
from zoneinfo import ZoneInfo
local_dt = datetime(..., tzinfo=ZoneInfo(tz_string))
utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
```
