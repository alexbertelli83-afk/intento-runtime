from __future__ import annotations


def type_name(value) -> str:
    if value is None:
        return "empty"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, list):
        return "list"
    return type(value).__name__


def format_value(value) -> str:
    """Format an INTENTO value for user-visible output."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "[" + ", ".join(_format_list_item(item) for item in value) + "]"
    return str(value)


def _format_list_item(value) -> str:
    if isinstance(value, str):
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return format_value(value)


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
