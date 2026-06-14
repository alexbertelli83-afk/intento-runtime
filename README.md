# INTENTO Runtime

**Human-readable code. Controlled syntax. Real execution.**

INTENTO is an experimental human-readable programming language designed to express software instructions in a form that is close to human intention while remaining structured, deterministic, and executable.

This repository contains **INTENTO Runtime v1.0.0**, the first validated experimental release of the INTENTO interpreter.

## What is INTENTO?

INTENTO is not a toy syntax experiment and it is not a replacement for mature programming languages such as Python.

It is an experimental language layer focused on a simple idea:

> programming should become more readable without becoming ambiguous.

INTENTO source code is written in `.intento` files and executed by a controlled Runtime. The language favors readable instructions such as `show`, `remember`, `ask`, `if`, `repeat`, `for each`, `use library`, and `use action`.

The goal is to make code easier to read, write, explain, and audit, while preserving clear execution rules.

## Example

```intento
remember "Alessandro" as name
show "Hello, " plus name
```

Expected output:

```text
Hello, Alessandro
```

Another example:

```intento
remember 5 as number

if number is greater than 3
    show "The number is greater than 3"
else
    show "The number is small"
```

Expected output:

```text
The number is greater than 3
```

## Main Features

INTENTO Runtime v1.0.0 includes:

* execution of `.intento` programs
* readable instructions for memory, output, input, conditions, loops, and lists
* word-based operators such as `plus`, `minus`, `times`, and `divided by`
* optional symbolic operator aliases
* controlled filesystem operations
* workspace safety rules
* standard libraries
* registered actions
* custom actions
* modules
* project structure support
* `.intentotest` testing files
* project initialization
* project packaging
* runtime diagnostics with `version` and `doctor`
* trace and strict check modes

## Installation

Clone the repository:

```bash
git clone https://github.com/alexbertelli83-afk/intento-runtime.git
cd intento-runtime
```

Optional: create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the Runtime locally:

```bash
pip install -e .
```

Check the installation:

```bash
python3 -m intento_runtime version
python3 -m intento_runtime doctor
```

## Run an INTENTO Program

Create a file named `hello.intento`:

```intento
show "Hello from INTENTO"
```

Run it:

```bash
python3 -m intento_runtime run hello.intento
```

Expected output:

```text
Hello from INTENTO
```

## Run Tests

Run the Python test suite:

```bash
python3 run_tests.py
```

Run INTENTO test files:

```bash
python3 -m intento_runtime test tests/intentotests
```

## Project Workflow

INTENTO Runtime can initialize and package projects.

Create a new project:

```bash
python3 -m intento_runtime init my_project
```

Run the project:

```bash
python3 -m intento_runtime run my_project
```

Check the project:

```bash
python3 -m intento_runtime check my_project
```

Package the project:

```bash
python3 -m intento_runtime package my_project --output my_project.zip
```

## Official Manual

The official manual is included in this repository and in the v1.0.0 release assets:

* `INTENTO_Official_Manual_corrected.pdf`
* `INTENTO_Official_Manual_corrected.docx`

The manual explains the language idea, execution model, syntax, runtime behavior, standard library, project format, and implementation rules.

## Release

The first experimental release is available here:

```text
INTENTO Runtime v1.0.0 — Experimental Prototype
```

It includes:

* Runtime source code
* `intento-runtime-v10.zip`
* official manual in PDF format
* official manual in DOCX format

## Status

INTENTO Runtime v1.0.0 is an experimental prototype.

It has been validated locally on Ubuntu and is suitable for study, experimentation, language design exploration, and controlled prototyping.

It is not production-ready.

## Ideator and Authorship

INTENTO was ideated by **Alessandro Bertelli**.

The project has been developed with AI-assisted support for prototyping, documentation, and implementation, while the original concept, direction, and authorship belong to Alessandro Bertelli.

## License and Copyright

The Runtime source code is released under the MIT License.

The official manual, project identity, language name, documentation, and related written materials are protected by copyright.

Copyright © 2026 Alessandro Bertelli. All rights reserved.
