# INTENTO Runtime v1.0

**INTENTO Runtime v1.0** is the first complete experimental release of INTENTO: a human-readable programming language with controlled syntax and real execution.

INTENTO has an Italian name, English syntax, and a practical goal: make programs readable to humans while remaining deterministic, parseable, testable, and safe to execute.

This release stabilizes the full v0.1–v0.9 prototype chain into a clean **1.0 experimental baseline**. It is still young, but it now has the essential pieces of a small real language: execution, control flow, filesystem safety, registered actions, modules, project metadata, a practical Standard Library, explicit conversion, developer diagnostics, native tests, project initialization, and packaging.

## What v1.0 means

Version 1.0 does not mean INTENTO is comparable to Python’s ecosystem. It means the first coherent Runtime line is complete enough to be used, tested, shared, and extended carefully.

The v1.0 goal is stability, not feature inflation. The Runtime should keep the language readable and strict instead of adding uncontrolled power.

## Implemented language features

- `show`
- `remember`
- `ask`
- `convert value to type and call it name`
- values: text, number, boolean, empty, list
- operators: `plus`, `minus`, `times`, `divided by`
- symbol aliases: `+`, `-`, `*`, `/`
- parentheses
- `if` / `else`
- comparisons: `is`, `is not`, `is empty`, `is not empty`, `is greater than`, `is less than`, `is at least`, `is at most`
- `stop`
- `repeat number times:`
- `for each item in list:`
- `read file`
- `create folder`
- `create file`
- `append to file`
- `with confirmation:`
- workspace sandbox
- `--yes`
- `dry-run`
- `use library`
- `use action`
- `describe action`
- Runtime action registry and metadata
- Standard Library namespaces: `text`, `number`, `list`, `file`, `log`, `date`, `json`, `csv`
- `to ...:` custom action definitions
- custom action calls
- `use module "path"`
- `use module "path" as alias`
- strict imported modules: no top-level executable instructions
- `intento.project` metadata
- running a project folder with `intento run project_folder`
- `intento project info project_folder`
- `version`
- `doctor`
- strict check mode
- trace logs
- `.intentotest` files
- `intento test`
- CLI source-context error reports
- `intento init`
- `intento package`

## Quick start

From the project folder:

```bash
python3 run_tests.py
python3 -m intento_runtime version
python3 -m intento_runtime doctor
python3 -m intento_runtime test tests/intentotests
```

Run simple examples:

```bash
python3 -m intento_runtime run examples/hello.intento
python3 -m intento_runtime run examples/if_else.intento
python3 -m intento_runtime run examples/stdlib_text.intento
python3 -m intento_runtime run examples/project_demo --show-logs
```

Create, test, and package a new project:

```bash
python3 -m intento_runtime init aurora_demo
python3 -m intento_runtime project info aurora_demo
python3 -m intento_runtime run aurora_demo --show-logs
python3 -m intento_runtime check aurora_demo
python3 -m intento_runtime test aurora_demo/tests/intentotests
python3 -m intento_runtime package aurora_demo --output aurora_demo.zip
```

## Optional editable install

The Runtime can also be installed in editable mode from this folder:

```bash
python3 -m pip install -e .
```

Then the CLI command becomes available as:

```bash
intento version
intento doctor
intento run examples/hello.intento
```

Using `python3 -m intento_runtime ...` remains fully supported.

## Project metadata

A standard INTENTO project contains an `intento.project` file:

```text
runtime: INTENTO 1.0
entry: main.intento
libraries: text
permissions: read project files, write project files with confirmation
features: modules, symbol operators, intentotests
```

The Runtime validates the entry point, required libraries, and project structure before execution.

## Safety model

The Runtime enforces the workspace sandbox. File writes require `with confirmation:` unless running in `dry-run`, and `--yes` may be used for non-interactive confirmation. Paths outside the workspace are blocked.

Raw shell execution and raw Python code inside INTENTO source remain blocked.

Registered backend actions may be implemented in Python, but they must be exposed through documented INTENTO action metadata: name, accepted types, return type, safety level, and description.

## Current limitation

Runtime v1.0 supports custom actions as executable statements. It parses `return`, but returned values are not yet consumable inside expressions such as `remember result as action with value`. That belongs to a future release.

INTENTO v1.0 is the first complete experimental baseline. The next work should focus on improving correctness, adding missing language primitives carefully, and keeping the Runtime small, readable, and safe.
