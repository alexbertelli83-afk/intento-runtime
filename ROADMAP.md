# INTENTO Runtime Roadmap

## Completed through v1.0

INTENTO Runtime v1.0 includes the full experimental baseline:

- Core execution
- Values and expressions
- Word operators and symbol aliases
- Conditions and comparisons
- Repetition and list iteration
- Explicit conversion
- File read/write operations with safety rules
- Workspace sandbox
- Confirmation and dry-run
- Standard Library registry
- Registered actions and metadata
- Text, number, list, file, log, date, JSON, and CSV libraries
- Custom actions
- Modules and aliases
- Project metadata
- Project initialization
- Project packaging
- Native `.intentotest` testing
- Runtime diagnostics with `version`, `doctor`, `--trace`, and source-context errors

## Next releases

### v1.1 — Language completeness

Possible additions:

- return values from custom actions usable in expressions
- `and`, `or`, `not`
- `while` or `repeat until`
- dictionary / record values
- stronger type declarations for custom actions

### v1.2 — Standard Library expansion

Possible additions:

- safer network actions
- richer file utilities
- path helpers
- better date/time handling
- CSV writing
- JSON object construction

### v1.3 — Tooling and distribution

Possible additions:

- formatted error reports
- project templates
- package metadata validation
- better install workflow
- GitHub Actions CI template
- documentation site skeleton

## Guiding rule

INTENTO should grow carefully. Every feature must stay readable, parseable, predictable, and safe.
