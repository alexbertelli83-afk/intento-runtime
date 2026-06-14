from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .errors import (
    IntentoActionError,
    IntentoConversionError,
    IntentoFileError,
    IntentoLibraryError,
    IntentoModuleError,
    IntentoRuntimeError,
    IntentoSafetyError,
    IntentoSemanticError,
    IntentoSyntaxError,
    IntentoTypeError,
)
from .expr import evaluate_expression
from .stdlib import call_action, get_action, get_library
from .values import format_value, is_number, type_name

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_QUALIFIED_ACTION_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)?$")
_RESERVED_NAMES = {
    'show', 'remember', 'ask', 'if', 'else', 'repeat', 'for', 'each', 'in',
    'to', 'return', 'convert', 'try', 'on', 'error', 'with', 'confirmation',
    'true', 'false', 'empty', 'is', 'not', 'greater', 'than', 'less', 'at', 'least', 'most',
    'read', 'file', 'create', 'folder', 'append', 'delete', 'overwrite',
    'use', 'module', 'library', 'action', 'describe', 'result', 'version', 'as',
}


class _ReturnSignal(Exception):
    def __init__(self, value: object):
        self.value = value


@dataclass
class RuntimeResult:
    output: list[str] = field(default_factory=list)
    memory: dict[str, object] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)


@dataclass
class SourceLine:
    number: int
    indent: int
    text: str


@dataclass
class Statement:
    line: int


@dataclass
class ShowStatement(Statement):
    expr: str


@dataclass
class RememberStatement(Statement):
    name: str
    expr: str


@dataclass
class AskStatement(Statement):
    question: str
    name: str


@dataclass
class StopStatement(Statement):
    pass


@dataclass
class IfStatement(Statement):
    condition: str
    then_block: list[Statement]
    else_block: list[Statement]


@dataclass
class RepeatStatement(Statement):
    count_expr: str
    body: list[Statement]


@dataclass
class ForEachStatement(Statement):
    item_name: str
    list_expr: str
    body: list[Statement]


@dataclass
class WithConfirmationStatement(Statement):
    body: list[Statement]


@dataclass
class ReadFileStatement(Statement):
    path_expr: str
    name: str


@dataclass
class CreateFolderStatement(Statement):
    path_expr: str


@dataclass
class CreateFileStatement(Statement):
    path_expr: str
    content_expr: str


@dataclass
class AppendToFileStatement(Statement):
    path_expr: str
    content_expr: str


@dataclass
class UseLibraryStatement(Statement):
    name: str
    version: str | None = None


@dataclass
class UseActionStatement(Statement):
    action_name: str
    arg_exprs: list[str]
    result_name: str | None = None


@dataclass
class DescribeActionStatement(Statement):
    action_name: str


@dataclass
class UseModuleStatement(Statement):
    path: str
    alias: str | None = None


@dataclass
class ActionDefinitionStatement(Statement):
    name: str
    params: list[str]
    body: list[Statement]
    origin: str = 'main'


@dataclass
class ActionCallStatement(Statement):
    name: str
    arg_exprs: list[str]


@dataclass
class ConvertStatement(Statement):
    expr: str
    target_type: str
    name: str


@dataclass
class ReturnStatement(Statement):
    expr: str


class _SourceParser:
    def __init__(self, runtime: 'IntentoRuntime', source: str):
        self.runtime = runtime
        self.lines = self._prepare_lines(source)
        self.index = 0

    def parse(self) -> list[Statement]:
        block = self._parse_block(expected_indent=0, stop_at_else=False)
        if self.index < len(self.lines):
            line = self.lines[self.index]
            if line.text == 'else:':
                raise IntentoSyntaxError('`else` must follow an `if` block', line.number)
            raise IntentoSyntaxError(f'unexpected indentation before `{line.text}`', line.number)
        return block

    def _prepare_lines(self, source: str) -> list[SourceLine]:
        prepared: list[SourceLine] = []
        for line_no, raw in enumerate(source.splitlines(), start=1):
            if '\t' in raw[:len(raw) - len(raw.lstrip(' \t'))]:
                raise IntentoSyntaxError('tabs are not allowed for indentation; use spaces', line_no)
            without_comment = self.runtime._strip_comment(raw)
            if not without_comment.strip():
                continue
            indent = len(without_comment) - len(without_comment.lstrip(' '))
            text = without_comment.strip()
            prepared.append(SourceLine(line_no, indent, text))
        return prepared

    def _parse_block(self, expected_indent: int, stop_at_else: bool) -> list[Statement]:
        statements: list[Statement] = []
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if line.indent < expected_indent:
                break
            if line.indent > expected_indent:
                raise IntentoSyntaxError(f'unexpected indentation before `{line.text}`', line.number)
            if line.text == 'else:':
                if stop_at_else:
                    break
                raise IntentoSyntaxError('`else` must follow an `if` block', line.number)
            statements.append(self._parse_statement(expected_indent))
        return statements

    def _parse_child_block(self, parent_indent: int, command_line: int) -> list[Statement]:
        if self.index >= len(self.lines):
            raise IntentoSyntaxError('expected indented block', command_line)
        child_indent = self.lines[self.index].indent
        if child_indent <= parent_indent:
            raise IntentoSyntaxError('expected indented block', command_line)
        return self._parse_block(child_indent, stop_at_else=False)

    def _parse_statement(self, indent: int) -> Statement:
        line = self.lines[self.index]
        text = line.text

        if text.startswith('if '):
            return self._parse_if(indent)
        if text == 'else:' or text.startswith('else'):
            raise IntentoSyntaxError('`else` must follow an `if` block', line.number)
        if text.startswith('repeat '):
            return self._parse_repeat(indent)
        if text.startswith('for each '):
            return self._parse_for_each(indent)
        if text.startswith('with confirmation'):
            return self._parse_with_confirmation(indent)
        if text.startswith('to '):
            return self._parse_action_definition(indent)

        self.index += 1
        return self.runtime._parse_simple_statement(text, line.number)

    def _parse_if(self, indent: int) -> IfStatement:
        line = self.lines[self.index]
        text = line.text
        if not text.endswith(':'):
            raise IntentoSyntaxError('expected `:` after condition', line.number)
        condition = text[3:-1].strip()
        if not condition:
            raise IntentoSyntaxError('`if` needs a condition', line.number)
        self.index += 1
        then_block = self._parse_child_block(indent, line.number)
        else_block: list[Statement] = []
        if self.index < len(self.lines):
            maybe_else = self.lines[self.index]
            if maybe_else.indent == indent and maybe_else.text.startswith('else'):
                if maybe_else.text != 'else:':
                    raise IntentoSyntaxError('invalid `else` syntax', maybe_else.number)
                self.index += 1
                else_block = self._parse_child_block(indent, maybe_else.number)
        return IfStatement(line=line.number, condition=condition, then_block=then_block, else_block=else_block)

    def _parse_repeat(self, indent: int) -> RepeatStatement:
        line = self.lines[self.index]
        text = line.text
        match = re.fullmatch(r'repeat\s+(.+)\s+times:', text)
        if not match:
            if not text.endswith(':'):
                raise IntentoSyntaxError('expected `:` after repeat instruction', line.number)
            raise IntentoSyntaxError('invalid `repeat` syntax', line.number)
        count_expr = match.group(1).strip()
        if not count_expr:
            raise IntentoSyntaxError('`repeat` needs a count', line.number)
        self.index += 1
        body = self._parse_child_block(indent, line.number)
        return RepeatStatement(line=line.number, count_expr=count_expr, body=body)

    def _parse_for_each(self, indent: int) -> ForEachStatement:
        line = self.lines[self.index]
        text = line.text
        match = re.fullmatch(r'for\s+each\s+([a-z][a-z0-9_]*)\s+in\s+(.+):', text)
        if not match:
            if not text.endswith(':'):
                raise IntentoSyntaxError('expected `:` after for each instruction', line.number)
            raise IntentoSyntaxError('invalid `for each` syntax', line.number)
        item_name, list_expr = match.groups()
        self.runtime._validate_name(item_name, line.number)
        list_expr = list_expr.strip()
        if not list_expr:
            raise IntentoSyntaxError('`for each` needs a list expression after `in`', line.number)
        self.index += 1
        body = self._parse_child_block(indent, line.number)
        return ForEachStatement(line=line.number, item_name=item_name, list_expr=list_expr, body=body)

    def _parse_with_confirmation(self, indent: int) -> WithConfirmationStatement:
        line = self.lines[self.index]
        if line.text != 'with confirmation:':
            if not line.text.endswith(':'):
                raise IntentoSyntaxError('expected `:` after `with confirmation`', line.number)
            raise IntentoSyntaxError('invalid `with confirmation` syntax', line.number)
        self.index += 1
        body = self._parse_child_block(indent, line.number)
        return WithConfirmationStatement(line=line.number, body=body)

    def _parse_action_definition(self, indent: int) -> ActionDefinitionStatement:
        line = self.lines[self.index]
        text = line.text
        match = re.fullmatch(r'to\s+([a-z][a-z0-9_]*)(?:\s+with\s+(.+))?:', text)
        if not match:
            if not text.endswith(':'):
                raise IntentoSyntaxError('expected `:` after action definition', line.number)
            raise IntentoSyntaxError('invalid `to` syntax', line.number)
        name, params_text = match.groups()
        self.runtime._validate_name(name, line.number)
        params: list[str] = []
        if params_text:
            for part in self.runtime._split_action_args(params_text, line.number):
                param = part.strip()
                self.runtime._validate_name(param, line.number)
                if param in params:
                    raise IntentoSyntaxError(f'duplicate parameter `{param}`', line.number)
                params.append(param)
        self.index += 1
        body = self._parse_child_block(indent, line.number)
        return ActionDefinitionStatement(line=line.number, name=name, params=params, body=body)


class IntentoRuntime:
    def __init__(
        self,
        input_func: Callable[[str], str] | None = None,
        confirm_func: Callable[[str], bool] | None = None,
        workspace: str | Path | None = None,
        dry_run: bool = False,
        trace: bool = False,
    ):
        self.memory: dict[str, object] = {}
        self.output: list[str] = []
        self.logs: list[str] = []
        self.loaded_libraries: set[str] = set()
        self.custom_actions: dict[str, ActionDefinitionStatement] = {}
        self.loaded_modules: set[tuple[Path, str | None]] = set()
        self.input_func = input_func or self._default_input
        self.confirm_func = confirm_func or self._default_confirm
        self.workspace = Path(workspace or Path.cwd()).resolve()
        self.dry_run = dry_run
        self.trace = trace
        self._confirmation_depth = 0
        self._call_depth = 0

    def run_source(self, source: str) -> RuntimeResult:
        statements = self._parse_source(source)
        try:
            self._execute_block(statements)
        except StopIteration:
            pass
        return RuntimeResult(output=self.output[:], memory=self.memory.copy(), logs=self.logs[:])

    def check_source(self, source: str) -> None:
        self._parse_source(source)

    def _parse_source(self, source: str) -> list[Statement]:
        return _SourceParser(self, source).parse()

    def _parse_simple_statement(self, line: str, line_no: int) -> Statement:
        if line.endswith(':'):
            command = line[:-1].strip().split(' ', 1)[0]
            raise IntentoSyntaxError(
                f"block command `{command}` is not implemented in INTENTO Runtime 0.8",
                line_no,
            )

        if line == 'stop':
            return StopStatement(line=line_no)

        if line.startswith('show '):
            expr = line[len('show '):].strip()
            if not expr:
                raise IntentoSyntaxError('`show` needs a value', line_no)
            return ShowStatement(line=line_no, expr=expr)

        if line == 'show':
            raise IntentoSyntaxError('`show` needs a value', line_no)

        if line.startswith('remember '):
            return self._parse_remember(line, line_no)

        if line.startswith('ask '):
            return self._parse_ask(line, line_no)

        if line.startswith('use module '):
            return self._parse_use_module(line, line_no)

        if line.startswith('use library '):
            return self._parse_use_library(line, line_no)

        if line.startswith('use action '):
            return self._parse_use_action(line, line_no)

        if line.startswith('describe action '):
            return self._parse_describe_action(line, line_no)

        if line.startswith('convert '):
            return self._parse_convert(line, line_no)

        if line.startswith('read file '):
            return self._parse_read_file(line, line_no)

        if line.startswith('create folder '):
            path_expr = line[len('create folder '):].strip()
            if not path_expr:
                raise IntentoSyntaxError('`create folder` needs a path', line_no)
            return CreateFolderStatement(line=line_no, path_expr=path_expr)

        if line.startswith('create file '):
            return self._parse_create_file(line, line_no)

        if line.startswith('append to file '):
            return self._parse_append_to_file(line, line_no)

        if line.startswith(('delete file', 'overwrite file')):
            raise IntentoSafetyError('deletion and overwrite are not available in INTENTO Runtime 0.8', line_no)

        if line.startswith('return '):
            expr = line[len('return '):].strip()
            if not expr:
                raise IntentoSyntaxError('`return` needs a value', line_no)
            return ReturnStatement(line=line_no, expr=expr)

        if line == 'return':
            raise IntentoSyntaxError('`return` needs a value', line_no)

        if line.startswith(('try', 'on error')):
            first = line.split()[0]
            raise IntentoSyntaxError(
                f"instruction `{first}` is reserved but not implemented in INTENTO Runtime 0.8",
                line_no,
            )

        action_call = self._parse_action_call(line, line_no)
        if action_call is not None:
            return action_call

        raise IntentoSyntaxError(f"unknown instruction `{line}`", line_no)

    def _parse_remember(self, line: str, line_no: int) -> RememberStatement:
        rest = line[len('remember '):].strip()
        split = self._split_outside_syntax(rest, ' as ')
        if split is None:
            raise IntentoSyntaxError('`remember` needs `as`', line_no)
        name, expr = split
        name = name.strip()
        expr = expr.strip()
        self._validate_name(name, line_no)
        if not expr:
            raise IntentoSyntaxError('`remember` needs a value after `as`', line_no)
        return RememberStatement(line=line_no, name=name, expr=expr)

    def _parse_ask(self, line: str, line_no: int) -> AskStatement:
        match = re.fullmatch(r'ask\s+"((?:[^"\\]|\\.)*)"\s+and\s+call\s+the\s+answer\s+([a-z][a-z0-9_]*)', line)
        if not match:
            if not line.startswith('ask "'):
                raise IntentoSyntaxError('question text must be written between quotation marks', line_no)
            raise IntentoSyntaxError('invalid `ask` syntax', line_no)
        raw_question, name = match.groups()
        self._validate_name(name, line_no)
        question = bytes(raw_question, 'utf-8').decode('unicode_escape')
        return AskStatement(line=line_no, question=question, name=name)

    def _parse_use_module(self, line: str, line_no: int) -> UseModuleStatement:
        match = re.fullmatch(r'use\s+module\s+"((?:[^"\\]|\\.)*)"(?:\s+as\s+([a-z][a-z0-9_]*))?', line)
        if not match:
            if not line.startswith('use module "'):
                raise IntentoSyntaxError('module path must be written between quotation marks', line_no)
            raise IntentoSyntaxError('invalid `use module` syntax', line_no)
        raw_path, alias = match.groups()
        path = bytes(raw_path, 'utf-8').decode('unicode_escape')
        if not path:
            raise IntentoSyntaxError('module path cannot be empty', line_no)
        if alias is not None:
            self._validate_name(alias, line_no)
        return UseModuleStatement(line=line_no, path=path, alias=alias)

    def _parse_use_library(self, line: str, line_no: int) -> UseLibraryStatement:
        match = re.fullmatch(r'use\s+library\s+"([a-z][a-z0-9_]*)"(?:\s+version\s+"([0-9]+(?:\.[0-9]+)*)")?', line)
        if not match:
            if not line.startswith('use library "'):
                raise IntentoSyntaxError('library name must be written between quotation marks', line_no)
            raise IntentoSyntaxError('invalid `use library` syntax', line_no)
        name, version = match.groups()
        return UseLibraryStatement(line=line_no, name=name, version=version)

    def _parse_use_action(self, line: str, line_no: int) -> UseActionStatement:
        match = re.fullmatch(r'use\s+action\s+"([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)"(.*)', line)
        if not match:
            if not line.startswith('use action "'):
                raise IntentoSyntaxError('action name must be written between quotation marks', line_no)
            raise IntentoSyntaxError('invalid `use action` syntax', line_no)
        action_name, rest = match.groups()
        rest = rest.strip()
        arg_exprs: list[str] = []
        result_name: str | None = None
        if not rest:
            return UseActionStatement(line=line_no, action_name=action_name, arg_exprs=arg_exprs, result_name=result_name)

        if rest.startswith('with '):
            after_with = rest[len('with '):].strip()
            split = self._split_outside_syntax(after_with, ' and call the result ')
            if split is not None:
                args_text, result_text = split
                result_name = result_text.strip()
                self._validate_name(result_name, line_no)
            else:
                args_text = after_with
            arg_exprs = self._split_action_args(args_text, line_no)
            return UseActionStatement(line=line_no, action_name=action_name, arg_exprs=arg_exprs, result_name=result_name)

        if rest.startswith('and call the result '):
            result_name = rest[len('and call the result '):].strip()
            self._validate_name(result_name, line_no)
            return UseActionStatement(line=line_no, action_name=action_name, arg_exprs=arg_exprs, result_name=result_name)

        raise IntentoSyntaxError('invalid `use action` syntax', line_no)

    def _parse_describe_action(self, line: str, line_no: int) -> DescribeActionStatement:
        match = re.fullmatch(r'describe\s+action\s+"([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)"', line)
        if not match:
            if not line.startswith('describe action "'):
                raise IntentoSyntaxError('action name must be written between quotation marks', line_no)
            raise IntentoSyntaxError('invalid `describe action` syntax', line_no)
        return DescribeActionStatement(line=line_no, action_name=match.group(1))

    def _parse_action_call(self, line: str, line_no: int) -> ActionCallStatement | None:
        split = self._split_outside_syntax(line, ' with ')
        if split is None:
            name = line.strip()
            args_text = None
        else:
            name, args_text = split[0].strip(), split[1].strip()
        if not _QUALIFIED_ACTION_RE.match(name):
            return None
        if name in _RESERVED_NAMES:
            return None
        arg_exprs = self._split_action_args(args_text, line_no) if args_text is not None else []
        return ActionCallStatement(line=line_no, name=name, arg_exprs=arg_exprs)

    def _split_action_args(self, args_text: str, line_no: int) -> list[str]:
        args_text = args_text.strip()
        if not args_text:
            return []
        args: list[str] = []
        rest = args_text
        while True:
            idx = self._find_marker_outside_syntax(rest, ' and ')
            if idx < 0:
                part = rest.strip()
                if not part:
                    raise IntentoSyntaxError('empty action argument', line_no)
                args.append(part)
                return args
            part = rest[:idx].strip()
            if not part:
                raise IntentoSyntaxError('empty action argument', line_no)
            args.append(part)
            rest = rest[idx + len(' and '):]

    def _parse_convert(self, line: str, line_no: int) -> ConvertStatement:
        rest = line[len('convert '):].strip()
        split_type = self._split_outside_syntax(rest, ' to ')
        if split_type is None:
            raise IntentoSyntaxError('`convert` needs `to type and call it name`', line_no)
        expr, after_to = split_type
        expr = expr.strip()
        split_name = self._split_outside_syntax(after_to, ' and call it ')
        if split_name is None:
            raise IntentoSyntaxError('`convert` needs `and call it name`', line_no)
        target_type, name = split_name
        target_type = target_type.strip()
        name = name.strip()
        if not expr:
            raise IntentoSyntaxError('`convert` needs a value', line_no)
        if target_type not in {'text', 'number', 'boolean'}:
            raise IntentoSyntaxError(f'unsupported conversion target `{target_type}`', line_no)
        self._validate_name(name, line_no)
        return ConvertStatement(line=line_no, expr=expr, target_type=target_type, name=name)

    def _parse_read_file(self, line: str, line_no: int) -> ReadFileStatement:
        rest = line[len('read file '):].strip()
        split = self._split_outside_syntax(rest, ' and call it ')
        if split is None:
            raise IntentoSyntaxError('`read file` needs `and call it name`', line_no)
        path_expr, name = split
        path_expr = path_expr.strip()
        name = name.strip()
        if not path_expr:
            raise IntentoSyntaxError('`read file` needs a path', line_no)
        self._validate_name(name, line_no)
        return ReadFileStatement(line=line_no, path_expr=path_expr, name=name)

    def _parse_create_file(self, line: str, line_no: int) -> CreateFileStatement:
        rest = line[len('create file '):].strip()
        split = self._split_outside_syntax(rest, ' with ')
        if split is None:
            raise IntentoSyntaxError('`create file` needs `with content`', line_no)
        path_expr, content_expr = split
        path_expr = path_expr.strip()
        content_expr = content_expr.strip()
        if not path_expr:
            raise IntentoSyntaxError('`create file` needs a path', line_no)
        if not content_expr:
            raise IntentoSyntaxError('`create file` needs content after `with`', line_no)
        return CreateFileStatement(line=line_no, path_expr=path_expr, content_expr=content_expr)

    def _parse_append_to_file(self, line: str, line_no: int) -> AppendToFileStatement:
        rest = line[len('append to file '):].strip()
        split = self._split_outside_syntax(rest, ' with ')
        if split is None:
            raise IntentoSyntaxError('`append to file` needs `with content`', line_no)
        path_expr, content_expr = split
        path_expr = path_expr.strip()
        content_expr = content_expr.strip()
        if not path_expr:
            raise IntentoSyntaxError('`append to file` needs a path', line_no)
        if not content_expr:
            raise IntentoSyntaxError('`append to file` needs content after `with`', line_no)
        return AppendToFileStatement(line=line_no, path_expr=path_expr, content_expr=content_expr)

    def _execute_block(self, statements: list[Statement]) -> None:
        for statement in statements:
            self._execute_statement(statement)

    def _execute_statement(self, statement: Statement) -> None:
        self._trace_statement(statement)
        if isinstance(statement, ShowStatement):
            value = evaluate_expression(statement.expr, self.memory, statement.line)
            self.output.append(format_value(value))
            return

        if isinstance(statement, RememberStatement):
            self.memory[statement.name] = evaluate_expression(statement.expr, self.memory, statement.line)
            return

        if isinstance(statement, AskStatement):
            self.memory[statement.name] = self.input_func(statement.question)
            return

        if isinstance(statement, UseModuleStatement):
            self._load_module(statement.path, statement.alias, statement.line)
            return

        if isinstance(statement, UseLibraryStatement):
            self._load_library(statement.name, statement.version, statement.line)
            return

        if isinstance(statement, UseActionStatement):
            self._execute_registered_action(statement)
            return

        if isinstance(statement, DescribeActionStatement):
            self._describe_action(statement.action_name, statement.line)
            return

        if isinstance(statement, ActionDefinitionStatement):
            self._register_action_definition(statement, prefix=None)
            return

        if isinstance(statement, ActionCallStatement):
            self._execute_custom_action(statement)
            return

        if isinstance(statement, ConvertStatement):
            value = evaluate_expression(statement.expr, self.memory, statement.line)
            self.memory[statement.name] = self._convert_value(value, statement.target_type, statement.line)
            return

        if isinstance(statement, ReturnStatement):
            if self._call_depth <= 0:
                raise IntentoSyntaxError('`return` can only be used inside a custom action', statement.line)
            raise _ReturnSignal(evaluate_expression(statement.expr, self.memory, statement.line))

        if isinstance(statement, StopStatement):
            raise StopIteration

        if isinstance(statement, IfStatement):
            if self._evaluate_condition(statement.condition, statement.line):
                self._execute_block(statement.then_block)
            else:
                self._execute_block(statement.else_block)
            return

        if isinstance(statement, RepeatStatement):
            count_value = evaluate_expression(statement.count_expr, self.memory, statement.line)
            count = self._validate_repeat_count(count_value, statement.line)
            for _ in range(count):
                self._execute_block(statement.body)
            return

        if isinstance(statement, ForEachStatement):
            list_value = evaluate_expression(statement.list_expr, self.memory, statement.line)
            if not isinstance(list_value, list):
                raise IntentoTypeError('`for each` requires a list after `in`', statement.line)
            old_exists = statement.item_name in self.memory
            old_value = self.memory.get(statement.item_name)
            try:
                for item in list_value:
                    self.memory[statement.item_name] = item
                    self._execute_block(statement.body)
            finally:
                if old_exists:
                    self.memory[statement.item_name] = old_value
                else:
                    self.memory.pop(statement.item_name, None)
            return

        if isinstance(statement, WithConfirmationStatement):
            self._confirmation_depth += 1
            try:
                self._execute_block(statement.body)
            finally:
                self._confirmation_depth -= 1
            return

        if isinstance(statement, ReadFileStatement):
            path = self._resolve_safe_path(statement.path_expr, statement.line)
            if not path.exists():
                raise IntentoFileError(f'file not found: {self._display_path(path)}', statement.line)
            if not path.is_file():
                raise IntentoFileError(f'path is not a file: {self._display_path(path)}', statement.line)
            self.memory[statement.name] = path.read_text(encoding='utf-8')
            return

        if isinstance(statement, CreateFolderStatement):
            path = self._resolve_safe_path(statement.path_expr, statement.line)
            if self._confirm_or_dry_run(f'create folder {self._display_path(path)}', statement.line):
                path.mkdir(parents=True, exist_ok=True)
            return

        if isinstance(statement, CreateFileStatement):
            path = self._resolve_safe_path(statement.path_expr, statement.line)
            content = evaluate_expression(statement.content_expr, self.memory, statement.line)
            if isinstance(content, list):
                raise IntentoTypeError('`create file` content must be text, number, boolean, or empty', statement.line)
            if self.dry_run:
                self._confirm_or_dry_run(f'create file {self._display_path(path)}', statement.line)
                return
            if path.exists():
                raise IntentoFileError(f'file already exists: {self._display_path(path)}', statement.line)
            if not path.parent.exists():
                raise IntentoFileError(f'parent folder does not exist: {self._display_path(path.parent)}', statement.line)
            if self._confirm_or_dry_run(f'create file {self._display_path(path)}', statement.line):
                path.write_text(format_value(content), encoding='utf-8')
            return

        if isinstance(statement, AppendToFileStatement):
            path = self._resolve_safe_path(statement.path_expr, statement.line)
            content = evaluate_expression(statement.content_expr, self.memory, statement.line)
            if isinstance(content, list):
                raise IntentoTypeError('`append to file` content must be text, number, boolean, or empty', statement.line)
            if self.dry_run:
                self._confirm_or_dry_run(f'append to file {self._display_path(path)}', statement.line)
                return
            if not path.exists():
                raise IntentoFileError(f'cannot append because file does not exist: {self._display_path(path)}', statement.line)
            if not path.is_file():
                raise IntentoFileError(f'path is not a file: {self._display_path(path)}', statement.line)
            if self._confirm_or_dry_run(f'append to file {self._display_path(path)}', statement.line):
                with path.open('a', encoding='utf-8') as handle:
                    handle.write(format_value(content))
            return

        raise AssertionError(f'unknown statement type: {statement!r}')

    def _trace_statement(self, statement: Statement) -> None:
        if not self.trace:
            return
        name = type(statement).__name__.replace('Statement', '')
        self.logs.append(f'TRACE line {statement.line}: {name}')

    def _convert_value(self, value: object, target_type: str, line_no: int) -> object:
        if target_type == 'text':
            return format_value(value)
        if target_type == 'number':
            if is_number(value):
                return value
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    raise IntentoConversionError('cannot convert empty text to number', line_no)
                try:
                    if any(ch in text for ch in '.eE'):
                        return float(text)
                    return int(text)
                except ValueError:
                    raise IntentoConversionError(f'cannot convert `{value}` to number', line_no) from None
            raise IntentoConversionError(f'cannot convert {type_name(value)} to number', line_no)
        if target_type == 'boolean':
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                text = value.strip()
                if text == 'true':
                    return True
                if text == 'false':
                    return False
                raise IntentoConversionError(f'cannot convert `{value}` to boolean', line_no)
            raise IntentoConversionError(f'cannot convert {type_name(value)} to boolean', line_no)
        raise IntentoSyntaxError(f'unsupported conversion target `{target_type}`', line_no)

    def _register_action_definition(self, statement: ActionDefinitionStatement, prefix: str | None) -> None:
        key = f'{prefix}.{statement.name}' if prefix else statement.name
        if key in self.custom_actions:
            raise IntentoSemanticError(f'custom action `{key}` is already defined', statement.line)
        self.custom_actions[key] = statement

    def _execute_custom_action(self, statement: ActionCallStatement) -> None:
        action = self.custom_actions.get(statement.name)
        if action is None:
            raise IntentoSemanticError(f'unknown custom action `{statement.name}`', statement.line)
        if len(statement.arg_exprs) != len(action.params):
            expected = len(action.params)
            plural = '' if expected == 1 else 's'
            raise IntentoActionError(f'action `{statement.name}` needs {expected} parameter{plural}', statement.line)
        args = [evaluate_expression(expr, self.memory, statement.line) for expr in statement.arg_exprs]
        old_memory = self.memory.copy()
        local_memory = self.memory.copy()
        for name, value in zip(action.params, args):
            local_memory[name] = value
        self.memory = local_memory
        self._call_depth += 1
        try:
            try:
                self._execute_block(action.body)
            except _ReturnSignal:
                # Runtime 0.8 supports `return` structurally, but action call statements do not consume return values yet.
                pass
        finally:
            self._call_depth -= 1
            self.memory = old_memory

    def _load_module(self, path_text: str, alias: str | None, line_no: int) -> None:
        path = self._resolve_path_value(path_text, line_no)
        if not path.exists():
            raise IntentoModuleError(f'module not found: {self._display_path(path)}', line_no)
        if not path.is_file():
            raise IntentoModuleError(f'module path is not a file: {self._display_path(path)}', line_no)
        if path.suffix != '.intento':
            raise IntentoModuleError('module files must use the .intento extension', line_no)
        load_key = (path.resolve(), alias)
        if load_key in self.loaded_modules:
            return
        source = path.read_text(encoding='utf-8')
        statements = self._parse_source(source)
        for statement in statements:
            if not isinstance(statement, (ActionDefinitionStatement, UseLibraryStatement, UseModuleStatement)):
                raise IntentoModuleError('top-level executable instructions are not allowed in imported module', statement.line)
        self.loaded_modules.add(load_key)
        for statement in statements:
            if isinstance(statement, UseLibraryStatement):
                self._load_library(statement.name, statement.version, statement.line)
            elif isinstance(statement, UseModuleStatement):
                self._load_module(statement.path, statement.alias, statement.line)
            elif isinstance(statement, ActionDefinitionStatement):
                self._register_action_definition(statement, prefix=alias)
        self.logs.append(f'Loaded module: {self._display_path(path)}' + (f' as {alias}' if alias else ''))

    def _load_library(self, name: str, version: str | None, line_no: int) -> None:
        if get_library(name) is None:
            raise IntentoLibraryError(f'unknown library `{name}`', line_no)
        if version is not None and version != '1.0':
            raise IntentoLibraryError(f'library `{name}` version `{version}` is not available', line_no)
        self.loaded_libraries.add(name)

    def _execute_registered_action(self, statement: UseActionStatement) -> None:
        action = get_action(statement.action_name)
        if action is None:
            raise IntentoSemanticError(f'unknown registered action `{statement.action_name}`', statement.line)
        if action.namespace not in self.loaded_libraries:
            raise IntentoLibraryError(f'library `{action.namespace}` must be loaded before using `{statement.action_name}`', statement.line)
        args = [evaluate_expression(expr, self.memory, statement.line) for expr in statement.arg_exprs]
        result = call_action(action, self, args, statement.line)
        if action.returns == 'nothing':
            if statement.result_name is not None:
                raise IntentoActionError(f'action `{statement.action_name}` does not return a value', statement.line)
            return
        if statement.result_name is not None:
            self.memory[statement.result_name] = result

    def _describe_action(self, action_name: str, line_no: int) -> None:
        action = get_action(action_name)
        if action is None:
            raise IntentoSemanticError(f'unknown registered action `{action_name}`', line_no)
        self.output.extend(action.describe())

    def _confirm_or_dry_run(self, description: str, line_no: int) -> bool:
        if self.dry_run:
            self.output.append(f'DRY RUN: would {description}')
            return False
        if self._confirmation_depth <= 0:
            raise IntentoSafetyError(f'operation `{description}` requires `with confirmation`', line_no)
        if not self.confirm_func(description):
            raise IntentoRuntimeError('operation cancelled by user', line_no)
        return True

    def _resolve_safe_path_literal(self, path_text: str, line_no: int) -> Path:
        if not isinstance(path_text, str):
            raise IntentoTypeError('file path must be text', line_no)
        return self._resolve_path_value(path_text, line_no)

    def _resolve_safe_path(self, path_expr: str, line_no: int) -> Path:
        value = evaluate_expression(path_expr, self.memory, line_no)
        if not isinstance(value, str):
            raise IntentoTypeError('file path must be text', line_no)
        return self._resolve_path_value(value, line_no)

    def _resolve_path_value(self, value: str, line_no: int) -> Path:
        if value == '':
            raise IntentoFileError('file path cannot be empty', line_no)
        if '\x00' in value:
            raise IntentoFileError('file path contains invalid null byte', line_no)
        raw_path = Path(value)
        if raw_path.is_absolute():
            candidate = raw_path.resolve()
        else:
            candidate = (self.workspace / raw_path).resolve()
        workspace = self.workspace.resolve()
        try:
            candidate.relative_to(workspace)
        except ValueError:
            raise IntentoSafetyError('path is outside the allowed workspace', line_no) from None
        return candidate

    def _display_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.workspace.resolve()))
        except ValueError:
            return str(path)

    def _validate_repeat_count(self, value: object, line_no: int) -> int:
        if not is_number(value):
            raise IntentoTypeError('repeat count must be a number', line_no)
        if isinstance(value, float):
            if not value.is_integer():
                raise IntentoTypeError('repeat count must be a whole number', line_no)
            value = int(value)
        if value < 0:
            raise IntentoRuntimeError('repeat count cannot be negative', line_no)
        return int(value)

    def _evaluate_condition(self, condition: str, line_no: int) -> bool:
        condition = condition.strip()
        if not condition:
            raise IntentoSyntaxError('`if` needs a condition', line_no)

        operators = [
            (' is not empty', 'is not empty'),
            (' is empty', 'is empty'),
            (' is greater than ', 'is greater than'),
            (' is less than ', 'is less than'),
            (' is at least ', 'is at least'),
            (' is at most ', 'is at most'),
            (' is not ', 'is not'),
            (' is ', 'is'),
        ]
        for marker, op in operators:
            split = self._split_condition(condition, marker, line_no)
            if split is None:
                continue
            left_text, right_text = split
            left = evaluate_expression(left_text, self.memory, line_no)
            if op in {'is empty', 'is not empty'}:
                result = self._is_empty(left)
                return not result if op == 'is not empty' else result
            right = evaluate_expression(right_text, self.memory, line_no)
            return self._compare_values(left, right, op, line_no)

        value = evaluate_expression(condition, self.memory, line_no)
        if not isinstance(value, bool):
            raise IntentoTypeError('condition must be boolean or use a comparison', line_no)
        return value

    def _split_condition(self, condition: str, marker: str, line_no: int) -> tuple[str, str] | None:
        split = self._split_outside_syntax(condition, marker)
        if split is None:
            return None
        left, right = split
        left = left.strip()
        right = right.strip()
        if not left:
            raise IntentoSyntaxError('condition is missing left value', line_no)
        if marker.strip() in {'is empty', 'is not empty'}:
            if right:
                raise IntentoSyntaxError('unexpected value after empty comparison', line_no)
        elif not right:
            raise IntentoSyntaxError('condition is missing right value', line_no)
        return left, right

    def _split_outside_syntax(self, text: str, marker: str) -> tuple[str, str] | None:
        idx = self._find_marker_outside_syntax(text, marker)
        if idx < 0:
            return None
        return text[:idx], text[idx + len(marker):]

    def _find_marker_outside_syntax(self, text: str, marker: str) -> int:
        in_string = False
        escape = False
        depth = 0
        i = 0
        while i <= len(text) - len(marker):
            ch = text[i]
            if escape:
                escape = False
                i += 1
                continue
            if ch == '\\':
                escape = True
                i += 1
                continue
            if ch == '"':
                in_string = not in_string
                i += 1
                continue
            if not in_string:
                if ch in '([':
                    depth += 1
                elif ch in ')]':
                    depth = max(0, depth - 1)
                if depth == 0 and text.startswith(marker, i):
                    return i
            i += 1
        return -1

    def _compare_values(self, left: object, right: object, op: str, line_no: int) -> bool:
        if op in {'is', 'is not'}:
            if type_name(left) != type_name(right):
                result = False
            else:
                result = left == right
            return not result if op == 'is not' else result

        if not (is_number(left) and is_number(right)):
            raise IntentoTypeError(f'cannot compare {type_name(left)} with {type_name(right)} using `{op}`', line_no)
        if op == 'is greater than':
            return left > right
        if op == 'is less than':
            return left < right
        if op == 'is at least':
            return left >= right
        if op == 'is at most':
            return left <= right
        raise AssertionError(op)

    @staticmethod
    def _is_empty(value: object) -> bool:
        return value is None or value == '' or value == []

    def _validate_name(self, name: str, line_no: int) -> None:
        if not _NAME_RE.match(name):
            if ' ' in name:
                raise IntentoSyntaxError('names cannot contain spaces', line_no)
            raise IntentoSyntaxError(f'invalid name `{name}`', line_no)
        if name in _RESERVED_NAMES:
            raise IntentoSyntaxError(f'`{name}` is a reserved keyword', line_no)

    @staticmethod
    def _strip_comment(line: str) -> str:
        in_string = False
        escape = False
        for i, ch in enumerate(line):
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if ch == '#' and not in_string:
                return line[:i]
        return line

    @staticmethod
    def _default_input(question: str) -> str:
        return input(question + '\n')

    @staticmethod
    def _default_confirm(description: str) -> bool:
        answer = input(f'Confirm operation: {description}? [y/N]\n')
        return answer.strip().lower() in {'y', 'yes'}


def run_source(
    source: str,
    input_func: Callable[[str], str] | None = None,
    confirm_func: Callable[[str], bool] | None = None,
    workspace: str | Path | None = None,
    dry_run: bool = False,
    trace: bool = False,
) -> RuntimeResult:
    runtime = IntentoRuntime(
        input_func=input_func,
        confirm_func=confirm_func,
        workspace=workspace,
        dry_run=dry_run,
        trace=trace,
    )
    return runtime.run_source(source)
