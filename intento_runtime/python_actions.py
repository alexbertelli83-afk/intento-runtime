from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from .errors import IntentoActionError, IntentoSafetyError, IntentoTypeError
from .stdlib import RegisteredAction
from .values import is_number, type_name

ActionSpec = dict[str, Any]

PYTHON_ACTIONS_RELATIVE_PATH = Path('actions') / 'intento_actions.py'
_ALLOWED_TYPES = {'any', 'text', 'number', 'list', 'boolean', 'nothing'}
_FORBIDDEN_IMPORT_ROOTS = {
    'builtins',
    'ctypes',
    'importlib',
    'os',
    'pathlib',
    'requests',
    'shutil',
    'socket',
    'subprocess',
    'sys',
    'urllib',
}
_FORBIDDEN_CALLS = {'eval', 'exec', 'compile', 'open', 'input', '__import__'}


def _line(line_no: int | None) -> int | None:
    return line_no


def _validate_python_action_source(source: str, path: Path, line_no: int | None) -> None:
    """Apply a conservative static safety check before importing a project action file.

    This is not a Python sandbox. It is a practical guardrail for INTENTO v1.1 so
    local Python actions remain intentionally small and pure by default.
    """
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise IntentoActionError(f'Python action file has invalid syntax: {exc.msg}', _line(line_no)) from None

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split('.', 1)[0]
                if root in _FORBIDDEN_IMPORT_ROOTS:
                    raise IntentoSafetyError(f'Python action file imports forbidden module `{root}`', _line(line_no))
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or '').split('.', 1)[0]
            if root in _FORBIDDEN_IMPORT_ROOTS:
                raise IntentoSafetyError(f'Python action file imports forbidden module `{root}`', _line(line_no))
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _FORBIDDEN_CALLS:
                raise IntentoSafetyError(f'Python action file calls forbidden function `{func.id}`', _line(line_no))
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith('__'):
                raise IntentoSafetyError('Python action file uses forbidden dunder attribute access', _line(line_no))


def _import_module_from_path(path: Path, line_no: int | None) -> ModuleType:
    source = path.read_text(encoding='utf-8')
    _validate_python_action_source(source, path, line_no)
    module_name = f'_intento_project_actions_{abs(hash(path.resolve()))}'
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise IntentoActionError(f'cannot load Python action file: {path}', _line(line_no))
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - tested through public error shape
        raise IntentoActionError(f'Python action file failed to load: {exc}', _line(line_no)) from None
    return module


def _expect_spec_list(value: Any, field: str, action_name: str, line_no: int | None) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise IntentoActionError(f'Python action `{action_name}` field `{field}` must be a list of type names', _line(line_no))
    for item in value:
        if item not in _ALLOWED_TYPES or item == 'nothing':
            raise IntentoActionError(f'Python action `{action_name}` has invalid accepted type `{item}`', _line(line_no))
    return tuple(value)


def _validate_action_name(name: str, line_no: int | None) -> None:
    parts = name.split('.')
    if len(parts) != 2 or parts[0] != 'local':
        raise IntentoActionError('Python action names must use the `local.` namespace', _line(line_no))
    for part in parts:
        if not part or not part.replace('_', '').isalnum() or not part[0].isalpha() or not part.islower():
            raise IntentoActionError(f'invalid Python action name `{name}`', _line(line_no))


def _is_valid_intento_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int, float)):
        return True
    if isinstance(value, list):
        return all(_is_valid_intento_value(item) for item in value)
    return False


def _matches_declared_type(value: Any, declared_type: str) -> bool:
    if declared_type == 'any':
        return True
    if declared_type == 'nothing':
        return value is None
    if declared_type == 'number':
        return is_number(value)
    if declared_type == 'text':
        return isinstance(value, str)
    if declared_type == 'list':
        return isinstance(value, list)
    if declared_type == 'boolean':
        return isinstance(value, bool)
    return type_name(value) == declared_type


def _wrap_function(action_name: str, func: Callable[..., Any], returns: str) -> Callable[[object, list[Any], int], Any]:
    def _wrapped(runtime: object, args: list[Any], line_no: int) -> Any:
        try:
            result = func(*args)
        except Exception as exc:
            raise IntentoActionError(f'Python action `{action_name}` failed: {exc}', line_no) from None
        if not _is_valid_intento_value(result):
            raise IntentoTypeError(
                f'Python action `{action_name}` returned unsupported value type `{type(result).__name__}`',
                line_no,
            )
        if not _matches_declared_type(result, returns):
            raise IntentoTypeError(
                f'Python action `{action_name}` declared return type {returns}, got {type_name(result)}',
                line_no,
            )
        return result
    return _wrapped


def _build_action(module: ModuleType, name: str, spec: ActionSpec, line_no: int | None) -> RegisteredAction:
    _validate_action_name(name, line_no)
    if not isinstance(spec, dict):
        raise IntentoActionError(f'Python action `{name}` specification must be a dictionary', _line(line_no))
    accepts = _expect_spec_list(spec.get('accepts', []), 'accepts', name, line_no)
    returns = spec.get('returns', 'nothing')
    if not isinstance(returns, str) or returns not in _ALLOWED_TYPES:
        raise IntentoActionError(f'Python action `{name}` has invalid return type `{returns}`', _line(line_no))
    function_ref = spec.get('function')
    if isinstance(function_ref, str):
        function = getattr(module, function_ref, None)
    else:
        function = function_ref
    if not callable(function):
        raise IntentoActionError(f'Python action `{name}` does not reference a callable function', _line(line_no))
    safety = spec.get('safety', 'project-python')
    description = spec.get('description', 'Project-local Python action.')
    if not isinstance(safety, str) or not isinstance(description, str):
        raise IntentoActionError(f'Python action `{name}` has invalid metadata', _line(line_no))
    return RegisteredAction(
        name=name,
        accepts=accepts,
        returns=returns,
        safety=safety,
        description=description,
        func=_wrap_function(name, function, returns),
    )


def load_python_actions(workspace: str | Path, line_no: int | None = None) -> dict[str, RegisteredAction]:
    root = Path(workspace).resolve()
    path = (root / PYTHON_ACTIONS_RELATIVE_PATH).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise IntentoSafetyError('Python action file is outside the workspace', _line(line_no)) from None
    if not path.exists():
        return {}
    if not path.is_file():
        raise IntentoActionError('Python action path is not a file', _line(line_no))
    module = _import_module_from_path(path, line_no)
    raw_actions = getattr(module, 'ACTIONS', None)
    if not isinstance(raw_actions, dict):
        raise IntentoActionError('Python action file must define ACTIONS as a dictionary', _line(line_no))
    actions: dict[str, RegisteredAction] = {}
    for name, spec in raw_actions.items():
        if not isinstance(name, str):
            raise IntentoActionError('Python action names must be text', _line(line_no))
        action = _build_action(module, name, spec, line_no)
        actions[action.name] = action
    return actions
