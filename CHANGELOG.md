# Changelog

## [0.1.0] — Unreleased

### Added
- `parse_metar()` — parses METAR and SPECI messages into typed dataclasses
- `parse_taf()` — parses TAF messages including BECMG, TEMPO, PROB30/40, FM change groups
- `ParseError` — raised with token and position on malformed input
- Full RVR support: fixed, variable range, M/P operators
- Zero runtime dependencies (stdlib only)
- GitHub Actions CI: lint, tests, secret scanning, TestPyPI dry-run, PyPI publish, release notes
