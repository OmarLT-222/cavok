# Changelog

## [0.2.0] — Unreleased

### Added
- `Metar.type` field — surfaces `"METAR"` or `"SPECI"` on the parsed object (was consumed but not stored in 0.1.0)
- `TrendForecast` dataclass — represents NOSIG, BECMG, and TEMPO trend forecasts appended to METARs
- `Metar.trend` field — `TrendForecast | None`, parses trend forecast after QNH
- `FM`, `TL`, `AT` time indicators in METAR trends (e.g. `FM161300`, `TL161500`, `AT161400`)

---

## [0.1.0] — Unreleased

### Added
- `parse_metar()` — parses METAR and SPECI messages into typed dataclasses
- `parse_taf()` — parses TAF messages including BECMG, TEMPO, PROB30/40, FM change groups
- `ParseError` — raised with token and position on malformed input
- Full RVR support: fixed, variable range, M/P operators
- Zero runtime dependencies (stdlib only)
- GitHub Actions CI: lint, tests, secret scanning, TestPyPI dry-run, PyPI publish, release notes
