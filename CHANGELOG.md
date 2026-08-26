# Changelog

## [Unreleased]

## [0.1.0] - 2026-08-25

### Added

- Initial rule catalog covering render identity, effect dependencies, saga
  concurrency, store shape, bundle size, DOM cost, plain JavaScript
  performance, and React 16 compatibility (53 rules across 8 categories).
- `references/legacy-constraints.md`, a React 16.14 capability matrix with
  supported substitutes for each unavailable API.
- `references/severity.md`, the impact taxonomy and accept-when policy.
- `scripts/check_rules.py`, a catalog validator with a `--json` output mode.
- Example files under `examples/` illustrating the corrected pattern for
  render identity, effect dependencies, parallel sagas, store shape, and
  route-level code splitting.
- GitHub Actions CI running lint, format check, tests, and catalog
  validation across Python 3.11-3.13 on Ubuntu and Windows.
