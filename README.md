# cavok

A Python library for parsing aviation weather messages.

v1 supports **METAR** and **TAF**. More message types (SIGMET, PIREP, …) are planned for future releases.

---

## Installation

```bash
pip install cavok
```

No external dependencies — stdlib only.

---

## Usage

```python
from cavok import parse_metar, parse_taf

metar = parse_metar("METAR LEMD 161230Z 23010KT 9999 FEW020 15/08 Q1013=")

metar.station          # "LEMD"
metar.wind.speed       # 10
metar.wind.unit        # "KT"
metar.temperature      # 15
metar.dewpoint         # 8
metar.qnh              # 1013
metar.sky.layers[0].cover   # "FEW"
metar.sky.layers[0].height  # 20  (× 100 ft = 2000 ft)
```

```python
taf = parse_taf("TAF LEMD 161100Z 1612/1712 23010KT 9999 FEW025=")

taf.station       # "LEMD"
taf.valid_from    # datetime(2024, ..., tzinfo=timezone.utc)
taf.base.wind.speed  # 10
```

Both functions raise `cavok.ParseError` (a `ValueError` subclass) if the message is malformed.

---

## What's parsed

### METAR / SPECI

| Field | Example |
|---|---|
| Station + time | `LEMD 161230Z` |
| AUTO / COR flags | `AUTO` |
| Wind | `23010G18KT`, `VRB05KT` |
| Prevailing visibility | `9999`, `0800` |
| RVR (fixed, variable, M/P operators) | `R28L/0600U`, `R28L/M0050V0800U` |
| Weather phenomena | `-RA`, `TSRA`, `FG` |
| Cloud layers + CB/TCU | `FEW020CB`, `BKN040` |
| CAVOK / NSC / SKC | |
| Temperature + dewpoint | `15/08` |
| QNH (hPa and inHg) | `Q1013`, `A2992` |
| RMK | preserved as raw string |

### TAF

| Field | Example |
|---|---|
| Station + issue time + validity | `LEMD 161100Z 1612/1712` |
| AMD / CNL / COR flags | |
| Base forecast group | wind, visibility, weather, clouds |
| BECMG / TEMPO / PROB30 / PROB40 / FM groups | |

---

## Values and units

Values are returned in the units as they appear in the message — knots, metres, hPa, °C. No automatic conversion in v1. All times are `datetime` objects with `timezone.utc`.

---

## Contributing

Issues and pull requests are welcome. Run the test suite with:

```bash
uv run pytest -q
```

Lint and format with:

```bash
uv run ruff check .
uv run ruff format .
```

---

## License

MIT
