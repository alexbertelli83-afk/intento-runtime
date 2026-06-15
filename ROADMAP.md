# INTENTO Runtime Roadmap

## Completed through v1.0

INTENTO Runtime v1.0 completed the first coherent experimental baseline:

- core syntax;
- values and expressions;
- conditions and loops;
- file operations with workspace safety;
- Standard Library actions;
- modules and custom actions;
- project metadata;
- tests and intentotests;
- project initialization and packaging.

## Completed in v1.1

Runtime v1.1 adds the first controlled Python extension layer:

- project-local Python registered actions;
- `local.` action namespace;
- explicit `--allow-python-actions` permission;
- metadata validation;
- return-value validation;
- conservative static safety checks;
- Python-actions demo project.

## Candidate v1.2 work

- Better project-action documentation.
- Optional permission levels for local Python actions.
- More precise action return types.
- More example projects.
- Improved error messages for action metadata.
- Optional `.intentotest` support for projects requiring Python actions.
- A safer long-term plugin format.

## Long-term ideas

- VS Code syntax highlighting.
- More Standard Library namespaces.
- Better package/install workflow.
- Website or GitHub Pages documentation.
- Manual examples synchronized with runtime tests.
- Controlled AI-backed actions.
- Records/dictionaries as first-class INTENTO values.
- Custom actions with returned values usable in expressions.
