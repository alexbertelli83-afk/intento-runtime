from __future__ import annotations

import argparse
import sys
from pathlib import Path

import intento_runtime

from .errors import IntentoError, IntentoRuntimeError
from .project import init_project, package_project, parse_project_file, read_source, resolve_target
from .runtime import IntentoRuntime
from .stdlib import get_action, list_actions, list_libraries
from .testrunner import format_test_report, run_intento_tests


VERSION = "1.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="intento", description=f"INTENTO Runtime {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version", help="Show Runtime version")
    sub.add_parser("doctor", help="Show Runtime diagnostics")

    init = sub.add_parser("init", help="Create a new INTENTO project folder")
    init.add_argument("name", help="Project folder to create")
    init.add_argument("--force", action="store_true", help="Overwrite generated files if they already exist")

    package = sub.add_parser("package", help="Package an INTENTO project folder as a zip archive")
    package.add_argument("folder", help="Project folder containing intento.project")
    package.add_argument("--output", help="Output zip path. Defaults to <project_name>.zip next to the project folder")
    package.add_argument("--include-output", action="store_true", help="Include the project output/ folder in the archive")

    run = sub.add_parser("run", help="Run an .intento source file or project folder")
    run.add_argument("file", help="Path to an .intento file or project folder")
    run.add_argument("--workspace", help="Allowed workspace folder for file operations")
    run.add_argument("--yes", action="store_true", help="Automatically confirm confirmation-required operations")
    run.add_argument("--show-logs", action="store_true", help="Print Runtime log entries after program output")
    run.add_argument("--trace", action="store_true", help="Add statement-level trace entries to Runtime logs")

    check = sub.add_parser("check", help="Parse/check an .intento source file or project folder without showing program output")
    check.add_argument("file", help="Path to an .intento file or project folder")
    check.add_argument("--workspace", help="Allowed workspace folder for module resolution")
    check.add_argument("--strict", action="store_true", help="Run a dry semantic check with safe defaults instead of parse-only check")
    check.add_argument("--show-logs", action="store_true", help="Print Runtime log entries for strict checks")
    check.add_argument("--trace", action="store_true", help="Add statement-level trace entries during strict checks")

    dry_run = sub.add_parser("dry-run", help="Show confirmation-required operations without modifying files")
    dry_run.add_argument("file", help="Path to an .intento file or project folder")
    dry_run.add_argument("--workspace", help="Allowed workspace folder for file operations")
    dry_run.add_argument("--show-logs", action="store_true", help="Print Runtime log entries after program output")
    dry_run.add_argument("--trace", action="store_true", help="Add statement-level trace entries to Runtime logs")

    describe = sub.add_parser("describe", help="Describe a registered action")
    describe_sub = describe.add_subparsers(dest="describe_kind", required=True)
    describe_action = describe_sub.add_parser("action", help="Describe a registered action")
    describe_action.add_argument("name", help="Action name, for example text.slugify")

    list_parser = sub.add_parser("list", help="List libraries or actions")
    list_sub = list_parser.add_subparsers(dest="list_kind", required=True)
    list_sub.add_parser("libraries", help="List available standard libraries")
    list_actions_parser = list_sub.add_parser("actions", help="List registered actions")
    list_actions_parser.add_argument("library", nargs="?", help="Optional library namespace")

    test = sub.add_parser("test", help="Run .intentotest files")
    test.add_argument("target", help="A .intentotest file or folder containing .intentotest files")
    test.add_argument("--show-details", action="store_true", help="Show expected and actual output for failed tests")

    project = sub.add_parser("project", help="Inspect an INTENTO project")
    project_sub = project.add_subparsers(dest="project_kind", required=True)
    project_info = project_sub.add_parser("info", help="Show project metadata")
    project_info.add_argument("folder", help="Project folder containing intento.project")

    return parser


def interactive_confirm(description: str) -> bool:
    answer = input(f"Confirm operation: {description}? [y/N]\n")
    return answer.strip().lower() in {"y", "yes"}


def print_result(result, show_logs: bool = False) -> None:
    for line in result.output:
        print(line)
    if show_logs and result.logs:
        print("-- Runtime log --")
        for line in result.logs:
            print(line)


def print_project_info(folder: str) -> None:
    project = parse_project_file(Path(folder).resolve() / 'intento.project')
    print(f'Project: {project.root.name}')
    print(f'Runtime: {project.runtime or "not specified"}')
    print(f'Entry: {project.entry}')
    print('Libraries: ' + (', '.join(project.libraries) if project.libraries else 'none'))
    print('Permissions: ' + (project.permissions or 'not specified'))
    print('Features: ' + (', '.join(project.features) if project.features else 'none'))


def print_doctor() -> None:
    libraries = list_libraries()
    actions = list_actions(None)
    print(f'INTENTO Runtime: {VERSION}')
    print(f'Package version: {getattr(intento_runtime, "__version__", "unknown")}')
    print(f'Python: {sys.version.split()[0]}')
    print(f'Package path: {Path(intento_runtime.__file__).resolve().parent}')
    print(f'Current folder: {Path.cwd()}')
    print(f'Libraries: {len(libraries)}')
    print(f'Actions: {len(actions)}')
    print('Doctor check passed.')



def print_intento_error(exc: IntentoError, source: str | None = None) -> None:
    print(str(exc), file=sys.stderr)
    if source is None or exc.line is None:
        return
    lines = source.splitlines()
    if 1 <= exc.line <= len(lines):
        print('Source context:', file=sys.stderr)
        print(f'{exc.line:>4} | {lines[exc.line - 1]}', file=sys.stderr)

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_for_error: str | None = None
    try:
        if args.command == "version":
            print(f'INTENTO Runtime {VERSION}')
            return 0

        if args.command == "doctor":
            print_doctor()
            return 0

        if args.command == "init":
            root = init_project(args.name, force=args.force)
            print(f'Initialized INTENTO project: {root}')
            print('Created: main.intento')
            print('Created: intento.project')
            print('Created: modules/formatting.intento')
            print('Created: tests/intentotests/project.intentotest')
            return 0

        if args.command == "package":
            output_path, count = package_project(args.folder, output=args.output, include_output=args.include_output)
            print(f'Packaged project: {output_path}')
            print(f'Files: {count}')
            return 0

        if args.command == "list":
            if args.list_kind == "libraries":
                for name in list_libraries():
                    print(name)
                return 0
            if args.list_kind == "actions":
                for name in list_actions(args.library):
                    print(name)
                return 0

        if args.command == "describe":
            if args.describe_kind == "action":
                action = get_action(args.name)
                if action is None:
                    raise IntentoRuntimeError(f"unknown registered action `{args.name}`")
                for line in action.describe():
                    print(line)
                return 0

        if args.command == "test":
            report = run_intento_tests(args.target)
            for line in format_test_report(report, show_details=args.show_details):
                print(line)
            return 0 if report.passed else 1

        if args.command == "project":
            if args.project_kind == "info":
                print_project_info(args.folder)
                return 0

        source_path, workspace, project = resolve_target(args.file, getattr(args, 'workspace', None))
        source = read_source(source_path)
        source_for_error = source

        if args.command == "check":
            runtime = IntentoRuntime(
                workspace=workspace,
                dry_run=args.strict,
                confirm_func=lambda description: True,
                input_func=lambda question: "",
                trace=args.trace,
            )
            if args.strict:
                result = runtime.run_source(source)
                print_result(result, show_logs=args.show_logs)
                print("Strict check passed.")
            else:
                runtime.check_source(source)
                print("Program check passed.")
            return 0

        if args.command == "dry-run":
            runtime = IntentoRuntime(workspace=workspace, dry_run=True, confirm_func=lambda description: True, trace=args.trace)
            result = runtime.run_source(source)
            print_result(result, show_logs=args.show_logs)
            return 0

        if args.command == "run":
            confirm_func = (lambda description: True) if args.yes else interactive_confirm
            runtime = IntentoRuntime(workspace=workspace, confirm_func=confirm_func, trace=args.trace)
            result = runtime.run_source(source)
            print_result(result, show_logs=args.show_logs)
            return 0

        raise IntentoRuntimeError(f"unknown command: {args.command}")
    except StopIteration:
        return 0
    except IntentoError as exc:
        print_intento_error(exc, source_for_error)
        return 1
    except KeyboardInterrupt:
        print("Runtime error: interrupted by user", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
