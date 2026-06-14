# INTENTO Runtime v1.0 Release Notes

INTENTO Runtime v1.0 is the first complete experimental baseline of the INTENTO language implementation.

It is suitable for local experimentation, documentation, demos, and careful public sharing as an early open-source prototype.

It should not yet be presented as production software.

## Highlights

- Human-readable `.intento` programs execute from the CLI.
- Programs support memory, values, expressions, conditions, loops, files, modules, libraries, and projects.
- The Runtime includes a controlled Standard Library and registered action system.
- File writes are protected by confirmation and workspace rules.
- Projects can be initialized, checked, tested, run, and packaged.
- Native `.intentotest` files allow expected output and expected error checks.
- Diagnostics include trace logs, doctor output, strict check mode, and source context for errors.

## Recommended GitHub status

Publish as:

```text
INTENTO Runtime v1.0 — experimental prototype
```

Recommended labels:

```text
experimental
prototype
human-readable programming language
safe execution
python runtime
```

## Before public release

Run:

```bash
python3 run_tests.py
python3 -m intento_runtime doctor
python3 -m intento_runtime test tests/intentotests
python3 -m intento_runtime init aurora_demo
python3 -m intento_runtime run aurora_demo --show-logs
python3 -m intento_runtime package aurora_demo --output aurora_demo.zip
```

If all commands pass, the local release is ready to archive or publish.
