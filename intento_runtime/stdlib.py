from __future__ import annotations

import csv
import io
import json
import re
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .errors import IntentoCSVError, IntentoDateError, IntentoFileError, IntentoJSONError, IntentoTypeError
from .values import format_value, is_number, type_name

ActionFunc = Callable[[object, list[Any], int], Any]


@dataclass(frozen=True)
class RegisteredAction:
    name: str
    accepts: tuple[str, ...]
    returns: str
    safety: str
    description: str
    func: ActionFunc

    @property
    def namespace(self) -> str:
        return self.name.split('.', 1)[0]

    def describe(self) -> list[str]:
        accepts = ', '.join(self.accepts) if self.accepts else 'nothing'
        return [
            f'Action: {self.name}',
            f'Accepts: {accepts}',
            f'Returns: {self.returns}',
            f'Safety: {self.safety}',
            f'Description: {self.description}',
        ]


def _expect_args(action: RegisteredAction, args: list[Any], line_no: int) -> None:
    expected = len(action.accepts)
    if len(args) != expected:
        plural = '' if expected == 1 else 's'
        raise IntentoTypeError(f'action `{action.name}` expects {expected} argument{plural}', line_no)
    for index, (value, expected_type) in enumerate(zip(args, action.accepts), start=1):
        if expected_type == 'any':
            continue
        if expected_type == 'number':
            ok = is_number(value)
        elif expected_type == 'text':
            ok = isinstance(value, str)
        elif expected_type == 'list':
            ok = isinstance(value, list)
        elif expected_type == 'boolean':
            ok = isinstance(value, bool)
        else:
            ok = type_name(value) == expected_type
        if not ok:
            raise IntentoTypeError(
                f'action `{action.name}` argument {index} expects {expected_type}, got {type_name(value)}',
                line_no,
            )


def _slugify_text(text: str) -> str:
    lowered = text.strip().lower()
    lowered = re.sub(r'[^a-z0-9]+', '-', lowered)
    lowered = re.sub(r'-+', '-', lowered).strip('-')
    return lowered


def _text_trim(runtime: object, args: list[Any], line_no: int) -> str:
    return args[0].strip()


def _text_uppercase(runtime: object, args: list[Any], line_no: int) -> str:
    return args[0].upper()


def _text_lowercase(runtime: object, args: list[Any], line_no: int) -> str:
    return args[0].lower()


def _text_slugify(runtime: object, args: list[Any], line_no: int) -> str:
    return _slugify_text(args[0])


def _text_count_words(runtime: object, args: list[Any], line_no: int) -> int:
    text = args[0].strip()
    if not text:
        return 0
    return len(re.findall(r'\S+', text))


def _text_split(runtime: object, args: list[Any], line_no: int) -> list[str]:
    text, separator = args
    if separator == '':
        raise IntentoTypeError('action `text.split` separator cannot be empty', line_no)
    return text.split(separator)


def _number_absolute(runtime: object, args: list[Any], line_no: int) -> int | float:
    return abs(args[0])


def _number_round(runtime: object, args: list[Any], line_no: int) -> int:
    return round(args[0])


def _number_minimum(runtime: object, args: list[Any], line_no: int) -> int | float:
    return min(args[0], args[1])


def _number_maximum(runtime: object, args: list[Any], line_no: int) -> int | float:
    return max(args[0], args[1])


def _list_count(runtime: object, args: list[Any], line_no: int) -> int:
    return len(args[0])


def _list_join(runtime: object, args: list[Any], line_no: int) -> str:
    items, separator = args
    return separator.join(format_value(item) for item in items)


def _list_contains(runtime: object, args: list[Any], line_no: int) -> bool:
    items, value = args
    return value in items


def _list_first(runtime: object, args: list[Any], line_no: int) -> Any:
    items = args[0]
    if not items:
        raise IntentoTypeError('action `list.first` cannot read from an empty list', line_no)
    return items[0]


def _list_last(runtime: object, args: list[Any], line_no: int) -> Any:
    items = args[0]
    if not items:
        raise IntentoTypeError('action `list.last` cannot read from an empty list', line_no)
    return items[-1]


def _file_exists(runtime: object, args: list[Any], line_no: int) -> bool:
    path = runtime._resolve_safe_path_literal(args[0], line_no)  # intentionally Runtime-provided helper
    return path.exists()


def _file_name(runtime: object, args: list[Any], line_no: int) -> str:
    path = runtime._resolve_safe_path_literal(args[0], line_no)
    return path.name


def _file_extension(runtime: object, args: list[Any], line_no: int) -> str:
    path = runtime._resolve_safe_path_literal(args[0], line_no)
    suffix = path.suffix
    return suffix[1:] if suffix.startswith('.') else suffix


def _log_info(runtime: object, args: list[Any], line_no: int) -> None:
    runtime.logs.append(f'INFO {args[0]}')
    return None


def _log_warning(runtime: object, args: list[Any], line_no: int) -> None:
    runtime.logs.append(f'WARNING {args[0]}')
    return None


def _log_error(runtime: object, args: list[Any], line_no: int) -> None:
    runtime.logs.append(f'ERROR {args[0]}')
    return None


_MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
]


def _parse_iso_date(value: str, line_no: int) -> date:
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise IntentoDateError(f'cannot parse date `{value}`', line_no) from None


def _format_date(value: date, fmt: str, line_no: int) -> str:
    if fmt == 'iso':
        return value.isoformat()
    if fmt == 'short':
        return f'{value.month:02d}/{value.day:02d}/{value.year}'
    if fmt == 'long':
        return f'{_MONTH_NAMES[value.month - 1]} {value.day}, {value.year}'
    raise IntentoDateError(f'unknown date format `{fmt}`', line_no)


def _date_today(runtime: object, args: list[Any], line_no: int) -> str:
    return date.today().isoformat()


def _date_format(runtime: object, args: list[Any], line_no: int) -> str:
    raw_date, fmt = args
    parsed = _parse_iso_date(raw_date, line_no)
    return _format_date(parsed, fmt, line_no)


def _date_add_days(runtime: object, args: list[Any], line_no: int) -> str:
    raw_date, days = args
    if isinstance(days, float):
        if not days.is_integer():
            raise IntentoDateError('days must be a whole number', line_no)
        days = int(days)
    parsed = _parse_iso_date(raw_date, line_no)
    return (parsed + timedelta(days=int(days))).isoformat()


def _json_load_object(data: str, line_no: int) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except json.JSONDecodeError:
        raise IntentoJSONError('invalid JSON text', line_no) from None
    if not isinstance(value, dict):
        raise IntentoJSONError('JSON root must be an object', line_no)
    return value


def _json_to_intento_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, list):
        return [_json_to_intento_value(item) for item in value]
    # INTENTO Runtime 0.8 has no record/dictionary value yet.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _json_get(runtime: object, args: list[Any], line_no: int) -> Any:
    data, key = args
    obj = _json_load_object(data, line_no)
    if key not in obj:
        raise IntentoJSONError(f'key `{key}` not found', line_no)
    return _json_to_intento_value(obj[key])


def _json_has_key(runtime: object, args: list[Any], line_no: int) -> bool:
    data, key = args
    obj = _json_load_object(data, line_no)
    return key in obj


def _read_csv_rows(data: str, line_no: int) -> tuple[list[str], list[list[str]]]:
    try:
        reader = csv.reader(io.StringIO(data), strict=True)
        rows = list(reader)
    except csv.Error:
        raise IntentoCSVError('invalid CSV text', line_no) from None
    if not rows:
        raise IntentoCSVError('CSV text is empty', line_no)
    header = rows[0]
    if not header or any(column == '' for column in header):
        raise IntentoCSVError('CSV header is invalid', line_no)
    width = len(header)
    data_rows = rows[1:]
    for row in data_rows:
        if len(row) != width:
            raise IntentoCSVError('CSV row has a different number of columns than the header', line_no)
    return header, data_rows


def _csv_count_rows(runtime: object, args: list[Any], line_no: int) -> int:
    _header, rows = _read_csv_rows(args[0], line_no)
    return len(rows)


def _csv_get_column(runtime: object, args: list[Any], line_no: int) -> list[str]:
    data, column_name = args
    header, rows = _read_csv_rows(data, line_no)
    if column_name not in header:
        raise IntentoCSVError(f'column `{column_name}` not found', line_no)
    index = header.index(column_name)
    return [row[index] for row in rows]


def _action(name: str, accepts: tuple[str, ...], returns: str, safety: str, description: str, func: ActionFunc) -> RegisteredAction:
    return RegisteredAction(name=name, accepts=accepts, returns=returns, safety=safety, description=description, func=func)


ACTIONS: dict[str, RegisteredAction] = {
    'text.trim': _action('text.trim', ('text',), 'text', 'safe', 'Removes leading and trailing spaces from text.', _text_trim),
    'text.uppercase': _action('text.uppercase', ('text',), 'text', 'safe', 'Converts text to uppercase.', _text_uppercase),
    'text.lowercase': _action('text.lowercase', ('text',), 'text', 'safe', 'Converts text to lowercase.', _text_lowercase),
    'text.slugify': _action('text.slugify', ('text',), 'text', 'safe', 'Converts text into a lowercase URL-safe slug.', _text_slugify),
    'text.count_words': _action('text.count_words', ('text',), 'number', 'safe', 'Counts words in a text value.', _text_count_words),
    'text.split': _action('text.split', ('text', 'text'), 'list', 'safe', 'Splits text using a text separator.', _text_split),

    'number.absolute': _action('number.absolute', ('number',), 'number', 'safe', 'Returns the absolute value of a number.', _number_absolute),
    'number.round': _action('number.round', ('number',), 'number', 'safe', 'Rounds a number to the nearest whole number.', _number_round),
    'number.minimum': _action('number.minimum', ('number', 'number'), 'number', 'safe', 'Returns the smaller of two numbers.', _number_minimum),
    'number.maximum': _action('number.maximum', ('number', 'number'), 'number', 'safe', 'Returns the larger of two numbers.', _number_maximum),

    'list.count': _action('list.count', ('list',), 'number', 'safe', 'Counts the items in a list.', _list_count),
    'list.join': _action('list.join', ('list', 'text'), 'text', 'safe', 'Joins list items into text using a separator.', _list_join),
    'list.contains': _action('list.contains', ('list', 'any'), 'boolean', 'safe', 'Checks whether a list contains a value.', _list_contains),
    'list.first': _action('list.first', ('list',), 'any', 'safe', 'Returns the first item in a list.', _list_first),
    'list.last': _action('list.last', ('list',), 'any', 'safe', 'Returns the last item in a list.', _list_last),

    'file.exists': _action('file.exists', ('text',), 'boolean', 'safe', 'Checks whether a path exists inside the workspace.', _file_exists),
    'file.name': _action('file.name', ('text',), 'text', 'safe', 'Returns the filename part of a path inside the workspace.', _file_name),
    'file.extension': _action('file.extension', ('text',), 'text', 'safe', 'Returns the extension of a path inside the workspace.', _file_extension),

    'date.today': _action('date.today', tuple(), 'text', 'safe', 'Returns the current Runtime date in ISO format.', _date_today),
    'date.format': _action('date.format', ('text', 'text'), 'text', 'safe', 'Formats an ISO date using iso, short, or long format.', _date_format),
    'date.add_days': _action('date.add_days', ('text', 'number'), 'text', 'safe', 'Adds a number of days to an ISO date.', _date_add_days),

    'json.get': _action('json.get', ('text', 'text'), 'any', 'safe', 'Reads a value from JSON object text by key.', _json_get),
    'json.has_key': _action('json.has_key', ('text', 'text'), 'boolean', 'safe', 'Checks whether JSON object text contains a key.', _json_has_key),

    'csv.count_rows': _action('csv.count_rows', ('text',), 'number', 'safe', 'Counts CSV data rows excluding the header row.', _csv_count_rows),
    'csv.get_column': _action('csv.get_column', ('text', 'text'), 'list', 'safe', 'Returns a list of values from a named CSV column.', _csv_get_column),

    'log.info': _action('log.info', ('text',), 'nothing', 'safe', 'Writes an informational message to the Runtime log.', _log_info),
    'log.warning': _action('log.warning', ('text',), 'nothing', 'safe', 'Writes a warning message to the Runtime log.', _log_warning),
    'log.error': _action('log.error', ('text',), 'nothing', 'safe', 'Writes an error message to the Runtime log.', _log_error),
}

LIBRARIES: dict[str, tuple[str, ...]] = {}
for action_name in ACTIONS:
    namespace = action_name.split('.', 1)[0]
    LIBRARIES.setdefault(namespace, tuple())
LIBRARIES = {name: tuple(sorted(a for a in ACTIONS if a.startswith(name + '.'))) for name in LIBRARIES}


def get_action(name: str) -> RegisteredAction | None:
    return ACTIONS.get(name)


def get_library(name: str) -> tuple[str, ...] | None:
    return LIBRARIES.get(name)


def list_libraries() -> list[str]:
    return sorted(LIBRARIES)


def list_actions(namespace: str | None = None) -> list[str]:
    if namespace is None:
        return sorted(ACTIONS)
    return sorted(action for action in ACTIONS if action.startswith(namespace + '.'))


def call_action(action: RegisteredAction, runtime: object, args: list[Any], line_no: int) -> Any:
    _expect_args(action, args, line_no)
    return action.func(runtime, args, line_no)
