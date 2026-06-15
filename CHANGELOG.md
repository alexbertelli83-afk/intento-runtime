# Changelog

## v1.1

Runtime v1.1 adds the first controlled Python-backed extension layer.

### Added

- Project-local Python registered actions from `actions/intento_actions.py`.
- New `local.` namespace for project-defined Python actions.
- New CLI flag: `--allow-python-actions` for `run`, `check --strict`, and `dry-run`.
- Python action metadata validation: accepted types, return type, safety level, description, callable function.
- Return-value validation for Python-backed actions.
- Conservative static safety checks before loading local Python action files.
- New example project: `examples/python_actions_demo`.
- Runtime version updated to `1.1.0`.
- Project metadata support updated to `INTENTO 1.1` while keeping `INTENTO 1.0` project compatibility.

### Safety

- Raw Python inside `.intento` source remains blocked.
- Raw shell execution remains blocked.
- Local Python actions require explicit user permission through `--allow-python-actions`.
- Local Python actions must use the `local.` namespace.
- Dangerous imports such as `os`, `subprocess`, `socket`, `shutil`, `sys`, `urllib`, and similar modules are blocked by default.
- Dangerous calls such as `eval`, `exec`, `compile`, `open`, `input`, and `__import__` are blocked by default.

## v1.0

This release stabilized the full v0.1-v0.9 prototype chain and updated the project/runtime metadata to `INTENTO 1.0`.

### Stabilized in v1.0

- Version updated to `1.0.0`.
- Runtime reports `INTENTO Runtime 1.0`.
- Project metadata uses `runtime: INTENTO 1.0`.
- Generated projects use `INTENTO 1.0` metadata.
- Release notes added.
- Roadmap added.
- README rewritten as a complete v1.0 baseline document.
- Existing test suite validated against the 1.0 metadata.

### Included from previous prototype steps

- v0.1: basic execution, values, memory, expressions, CLI.
- v0.2: conditions, loops, stop, indentation.
- v0.3: filesystem operations and workspace safety.
- v0.4: Standard Library and registered actions.
- v0.5: custom actions, modules, project metadata.
- v0.6: date, JSON, and CSV libraries.
- v0.7: conversion, version, doctor, trace, strict check.
- v0.8: `.intentotest` runner and source-context errors.
- v0.9: project initialization and packaging.
