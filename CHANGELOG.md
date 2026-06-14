# Changelog

## v1.0

First complete experimental release baseline.

This release stabilizes the full v0.1-v0.9 prototype chain and updates the project/runtime metadata to `INTENTO 1.0`.

### Stabilized in v1.0

- Version updated to `1.0.0`.
- Runtime reports `INTENTO Runtime 1.0`.
- Project metadata now uses `runtime: INTENTO 1.0`.
- Generated projects now use `INTENTO 1.0` metadata.
- Added `pyproject.toml` for optional editable installation and console command support.
- Added release checklist and first-release notes.
- README rewritten as a complete v1.0 baseline document.
- Existing test suite validated against the 1.0 metadata.

### Included from previous milestones

- v0.1: basic execution, values, memory, expressions, CLI.
- v0.2: conditions, comparisons, repeat, for each, blocks.
- v0.3: filesystem, workspace sandbox, confirmation, dry-run.
- v0.4: Standard Library and registered actions.
- v0.5: custom actions, modules, project format.
- v0.6: date, JSON, CSV libraries.
- v0.7: conversion, trace, strict check, version, doctor.
- v0.8: `.intentotest` runner and source-context errors.
- v0.9: project init and packaging.

## v0.9

- Added `intento init`.
- Added project skeleton generation.
- Added `intento package`.
- Updated project metadata support to `INTENTO 0.9`.
