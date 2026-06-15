# INTENTO Runtime v1.1

**Human-readable code. Controlled syntax. Real execution.**

INTENTO is an experimental human-readable programming language with an Italian name, English syntax, and a practical goal: express software instructions in a form that is close to human intention while remaining deterministic, parseable, testable, and safe to execute.

**INTENTO Runtime v1.1** extends the validated v1.0 baseline with **project-local Python registered actions**. This means INTENTO can now use Python as a backend power layer without allowing raw Python code inside `.intento` source files.

The rule is simple:

```text
INTENTO source stays readable and controlled.
Python power is exposed only through registered actions.
```

## What v1.1 adds

Runtime v1.1 adds an explicit bridge between INTENTO and Python:

- project-local Python action file: `actions/intento_actions.py`
- `local.` namespace for project actions
- explicit CLI permission: `--allow-python-actions`
- action metadata: accepted types, return type, safety level, description, function
- return-value validation for Python-backed actions
- conservative static safety checks before importing project action files
- blocking of dangerous imports such as `os`, `subprocess`, `socket`, `shutil`, `sys`, and similar modules
- blocking of dangerous calls such as `eval`, `exec`, `compile`, `open`, `input`, and `__import__`

This is not a full Python sandbox. It is a controlled Runtime layer designed for small, explicit, project-local actions.

## What v1.0 already included

The v1.0 baseline remains intact:

- execution of `.intento` programs
- `show`, `remember`, `ask`
- values: text, number, boolean, empty, list
- word operators: `plus`, `minus`, `times`, `divided by`
- optional symbol aliases: `+`, `-`, `*`, `/`
- conditions, comparisons, `if` / `else`
- `repeat` and `for each`
- controlled file operations
- workspace sandbox
- confirmation-required writes
- dry-run mode
- Standard Library namespaces: `text`, `number`, `list`, `file`, `log`, `date`, `json`, `csv`
- registered actions with metadata
- custom INTENTO actions
- modules
- project metadata with `intento.project`
- `.intentotest` files
- project initialization and packaging
- `version`, `doctor`, `check`, `trace`, and source-context errors

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

Run the v1.1 Python-actions demo:

```bash
python3 -m intento_runtime run examples/python_actions_demo --allow-python-actions
```

Expected output:

```text
INTENTO Runtime v1.1
INTENTO RUNTIME V1.1!
```

## Python-backed actions

A project-local Python action lives in:

```text
actions/intento_actions.py
```

Example Python action file:

```python
def clean_title(value):
    return value.strip().replace('!!!', '').strip()


ACTIONS = {
    'local.clean_title': {
        'accepts': ['text'],
        'returns': 'text',
        'safety': 'project-python',
        'description': 'Cleans an INTENTO project title using project-local Python.',
        'function': clean_title,
    },
}
```

The INTENTO program stays readable:

```intento
use library "local"

remember title as "  INTENTO Runtime v1.1 !!!  "
use action "local.clean_title" with title and call the result clean_title

show clean_title
```

Run it with explicit permission:

```bash
python3 -m intento_runtime run project_folder --allow-python-actions
```

Without `--allow-python-actions`, the `local` library is not available.

## Safety model

Raw shell execution and raw Python code inside `.intento` source are still blocked.

Python-backed power is allowed only when all of these are true:

1. the action is declared in `actions/intento_actions.py`;
2. the action name uses the `local.` namespace;
3. the INTENTO program loads `use library "local"`;
4. the user runs the Runtime with `--allow-python-actions`;
5. the action file passes conservative static safety checks;
6. the action returns an INTENTO-compatible value.

This keeps INTENTO human-readable while allowing controlled access to Python-backed capability.

## Project metadata

A standard INTENTO v1.1 project contains an `intento.project` file:

```text
runtime: INTENTO 1.1
entry: main.intento
libraries: text
permissions: read project files, write project files with confirmation
features: modules, symbol operators, intentotests
```

A project that uses local Python actions may declare:

```text
runtime: INTENTO 1.1
entry: main.intento
libraries: local
permissions: project-local Python actions only when explicitly enabled
features: local python actions, registered actions
```

## Optional editable install

The Runtime can be installed in editable mode from this folder:

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

## Current limitation

Runtime v1.1 can call registered Python-backed actions, but it does not execute arbitrary Python source from INTENTO programs. That is intentional.

Custom INTENTO actions are executable statements. The Runtime parses `return`, but returned values from custom INTENTO actions are not yet consumable inside expressions. That belongs to a future release.

## Status

INTENTO Runtime v1.1 is an experimental prototype. It is suitable for study, controlled prototyping, language design exploration, and small local automation experiments.

It is not production-ready.

## Ideator and copyright

INTENTO was ideated by **Alessandro Bertelli**.

The Runtime source code is released under the MIT License. The manual, project identity, language name, documentation, and related written materials are protected by copyright.

Copyright © 2026 Alessandro Bertelli. All rights reserved.
