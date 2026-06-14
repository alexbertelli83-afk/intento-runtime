from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .errors import IntentoError, IntentoRuntimeError, IntentoSyntaxError
from .project import read_source, resolve_target
from .runtime import IntentoRuntime


@dataclass
class IntentoTestCase:
    path: Path
    name: str
    program: str
    mode: str = 'run'
    workspace: str | None = None
    yes: bool = False
    show_logs: bool = False
    trace: bool = False
    strict: bool = False
    expected_output: list[str] | None = None
    expected_error: str | None = None


@dataclass
class IntentoTestResult:
    name: str
    passed: bool
    expected: str
    got: str
    error: str | None = None


@dataclass
class IntentoTestReport:
    results: list[IntentoTestResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for result in self.results if not result.passed)


def _strip_comment(line: str) -> str:
    in_string = False
    escape = False
    result: list[str] = []
    for ch in line:
        if escape:
            result.append(ch)
            escape = False
            continue
        if ch == '\\':
            result.append(ch)
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if ch == '#' and not in_string:
            break
        result.append(ch)
    return ''.join(result)


def _parse_bool(value: str, key: str, line_no: int) -> bool:
    normalized = value.strip().lower()
    if normalized in {'true', 'yes', '1'}:
        return True
    if normalized in {'false', 'no', '0'}:
        return False
    raise IntentoSyntaxError(f'invalid boolean value for `{key}` in test file: {value}', line_no)


def parse_intento_test(path: str | Path) -> IntentoTestCase:
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise IntentoRuntimeError(f'test file not found: {file_path}')
    if file_path.suffix != '.intentotest':
        raise IntentoRuntimeError('INTENTO test files must use the .intentotest extension')

    data: dict[str, object] = {
        'mode': 'run',
        'yes': False,
        'show_logs': False,
        'trace': False,
        'strict': False,
    }
    section: str | None = None
    section_lines: list[str] = []
    section_start_line: int | None = None

    def finish_section(line_no: int) -> None:
        nonlocal section, section_lines, section_start_line
        if section is None:
            return
        if section == 'expect output':
            data['expected_output'] = list(section_lines)
        elif section == 'expect error':
            data['expected_error'] = '\n'.join(section_lines).strip()
        else:
            raise IntentoSyntaxError(f'unknown section `{section}` in test file', section_start_line or line_no)
        section = None
        section_lines = []
        section_start_line = None

    for line_no, raw in enumerate(file_path.read_text(encoding='utf-8').splitlines(), start=1):
        stripped_raw = raw.rstrip('\n')
        if section is not None:
            if stripped_raw.strip() == 'end':
                finish_section(line_no)
            else:
                section_lines.append(stripped_raw)
            continue

        text = _strip_comment(stripped_raw).strip()
        if not text:
            continue
        lower = text.lower()
        if lower in {'expect output:', 'expect error:'}:
            section = lower[:-1]
            section_start_line = line_no
            section_lines = []
            continue
        if ':' not in text:
            raise IntentoSyntaxError(f'invalid test metadata line: {text}', line_no)
        key, value = text.split(':', 1)
        key = key.strip().lower().replace('-', '_')
        value = value.strip()
        if key in {'name', 'program', 'mode', 'workspace'}:
            data[key] = value
        elif key in {'yes', 'show_logs', 'trace', 'strict'}:
            data[key] = _parse_bool(value, key, line_no)
        else:
            raise IntentoSyntaxError(f'unknown test metadata key `{key}`', line_no)

    if section is not None:
        raise IntentoSyntaxError(f'missing `end` for `{section}` section', section_start_line)

    name = str(data.get('name') or file_path.stem)
    program = str(data.get('program') or '').strip()
    if not program:
        raise IntentoSyntaxError('test file needs `program: path`')
    mode = str(data.get('mode') or 'run').strip().lower()
    if mode not in {'run', 'dry-run', 'check'}:
        raise IntentoSyntaxError(f'unsupported test mode `{mode}`')
    expected_output = data.get('expected_output')
    expected_error = data.get('expected_error')
    if expected_output is None and expected_error is None:
        raise IntentoSyntaxError('test file needs `expect output:` or `expect error:` section')
    if expected_output is not None and expected_error is not None:
        raise IntentoSyntaxError('test file cannot have both `expect output:` and `expect error:` sections')

    return IntentoTestCase(
        path=file_path,
        name=name,
        program=program,
        mode=mode,
        workspace=str(data.get('workspace')) if data.get('workspace') else None,
        yes=bool(data.get('yes')),
        show_logs=bool(data.get('show_logs')),
        trace=bool(data.get('trace')),
        strict=bool(data.get('strict')),
        expected_output=expected_output if isinstance(expected_output, list) else None,
        expected_error=expected_error if isinstance(expected_error, str) else None,
    )


def discover_test_files(target: str | Path) -> list[Path]:
    path = Path(target).resolve()
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(path.rglob('*.intentotest'))
    raise IntentoRuntimeError(f'test target not found: {path}')


def _resolve_relative_path(raw: str, test_path: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    relative_to_test = (test_path.parent / candidate).resolve()
    if relative_to_test.exists():
        return relative_to_test
    return (Path.cwd() / candidate).resolve()


def _render_lines(lines: list[str]) -> str:
    return '\n'.join(lines)


def run_test_case(case: IntentoTestCase) -> IntentoTestResult:
    try:
        program_path = _resolve_relative_path(case.program, case.path)
        workspace_path = _resolve_relative_path(case.workspace, case.path) if case.workspace else None
        source_path, workspace, _project = resolve_target(program_path, workspace_path)
        source = read_source(source_path)

        if case.mode == 'check':
            runtime = IntentoRuntime(
                workspace=workspace,
                dry_run=case.strict,
                confirm_func=lambda description: True,
                input_func=lambda question: '',
                trace=case.trace,
            )
            if case.strict:
                result = runtime.run_source(source)
                output = list(result.output)
                if case.show_logs and result.logs:
                    output.append('-- Runtime log --')
                    output.extend(result.logs)
                output.append('Strict check passed.')
            else:
                runtime.check_source(source)
                output = ['Program check passed.']
        else:
            runtime = IntentoRuntime(
                workspace=workspace,
                dry_run=(case.mode == 'dry-run'),
                confirm_func=(lambda description: True) if case.yes or case.mode == 'dry-run' else (lambda description: False),
                input_func=lambda question: '',
                trace=case.trace,
            )
            result = runtime.run_source(source)
            output = list(result.output)
            if case.show_logs and result.logs:
                output.append('-- Runtime log --')
                output.extend(result.logs)

        if case.expected_error is not None:
            return IntentoTestResult(
                name=case.name,
                passed=False,
                expected=case.expected_error,
                got=_render_lines(output),
                error='expected error but program succeeded',
            )
        expected = case.expected_output or []
        passed = output == expected
        return IntentoTestResult(case.name, passed, _render_lines(expected), _render_lines(output))
    except IntentoError as exc:
        got_error = str(exc)
        if case.expected_error is not None:
            passed = got_error == case.expected_error
            return IntentoTestResult(case.name, passed, case.expected_error, got_error)
        return IntentoTestResult(case.name, False, _render_lines(case.expected_output or []), got_error, error='program failed')


def run_intento_tests(target: str | Path) -> IntentoTestReport:
    files = discover_test_files(target)
    if not files:
        raise IntentoRuntimeError(f'no .intentotest files found in {Path(target).resolve()}')
    report = IntentoTestReport()
    for file_path in files:
        case = parse_intento_test(file_path)
        report.results.append(run_test_case(case))
    return report


def format_test_report(report: IntentoTestReport, show_details: bool = False) -> list[str]:
    lines: list[str] = []
    for result in report.results:
        if result.passed:
            lines.append(f'OK   {result.name}')
        else:
            lines.append(f'FAIL {result.name}')
            if result.error:
                lines.append(f'     {result.error}')
            if show_details:
                lines.append('     Expected:')
                lines.extend(f'       {line}' for line in result.expected.splitlines() or [''])
                lines.append('     Got:')
                lines.extend(f'       {line}' for line in result.got.splitlines() or [''])
    if report.passed:
        lines.append('All intentotests passed.')
    else:
        lines.append(f'Intentotests failed: {report.failed_count} failed, {report.passed_count} passed.')
    return lines
