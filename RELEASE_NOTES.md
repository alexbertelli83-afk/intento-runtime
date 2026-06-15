# INTENTO Runtime v1.1 Release Notes

INTENTO Runtime v1.1 is the first experimental extension release after the validated v1.0 baseline.

The main feature is **project-local Python registered actions**.

## Main idea

INTENTO should remain readable and controlled. Python should be a backend power layer, not free code embedded in `.intento` files.

Runtime v1.1 follows this rule:

```text
INTENTO does not execute arbitrary Python.
INTENTO calls named, registered, project-local Python actions.
```

## New feature

A project may define actions in:

```text
actions/intento_actions.py
```

The INTENTO source can then use them through the `local.` namespace:

```intento
use library "local"
use action "local.clean_title" with title and call the result clean_title
```

The Runtime must be started with explicit permission:

```bash
python3 -m intento_runtime run project_folder --allow-python-actions
```

## Safety behavior

Runtime v1.1 blocks project-local Python actions unless `--allow-python-actions` is present.

It also applies conservative static checks before loading the Python file. This helps keep v1.1 actions small, explicit, and controlled.

This is not a full Python sandbox and should not be treated as production-grade isolation.

## Validation

The full test suite passes, including:

- existing v1.0 behavior;
- local Python action loading;
- required explicit permission;
- blocked forbidden import test;
- CLI demo execution.

## Status

INTENTO Runtime v1.1 — experimental prototype.
