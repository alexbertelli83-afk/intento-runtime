from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import IntentoSemanticError, IntentoSyntaxError, IntentoTypeError, IntentoRuntimeError
from .values import is_number, format_value, type_name


@dataclass
class Token:
    kind: str
    value: Any
    position: int


class ExpressionTokenizer:
    def __init__(self, text: str, line: int | None = None):
        self.text = text
        self.line = line
        self.i = 0
        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        while self.i < len(self.text):
            ch = self.text[self.i]

            if ch.isspace():
                self.i += 1
                continue

            if ch == '"':
                self.tokens.append(self._string())
                continue

            if ch.isdigit() or (ch == '.' and self._peek_next_is_digit()):
                self.tokens.append(self._number())
                continue

            if ch.isalpha() or ch == '_':
                self.tokens.append(self._word())
                continue

            single = {
                '+': 'PLUS',
                '-': 'MINUS',
                '*': 'TIMES',
                '/': 'DIVIDE',
                '(': 'LPAREN',
                ')': 'RPAREN',
                '[': 'LBRACK',
                ']': 'RBRACK',
                ',': 'COMMA',
            }
            if ch in single:
                self.tokens.append(Token(single[ch], ch, self.i))
                self.i += 1
                continue

            raise IntentoSyntaxError(f"unexpected character `{ch}` in expression", self.line)

        self.tokens.append(Token('EOF', None, self.i))
        return self.tokens

    def _peek_next_is_digit(self) -> bool:
        return self.i + 1 < len(self.text) and self.text[self.i + 1].isdigit()

    def _string(self) -> Token:
        start = self.i
        self.i += 1
        chars: list[str] = []
        while self.i < len(self.text):
            ch = self.text[self.i]
            if ch == '"':
                self.i += 1
                return Token('STRING', ''.join(chars), start)
            if ch == '\\':
                self.i += 1
                if self.i >= len(self.text):
                    raise IntentoSyntaxError("unfinished escape sequence in text value", self.line)
                esc = self.text[self.i]
                mapping = {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}
                chars.append(mapping.get(esc, esc))
                self.i += 1
                continue
            chars.append(ch)
            self.i += 1
        raise IntentoSyntaxError("missing closing quotation mark", self.line)

    def _number(self) -> Token:
        start = self.i
        has_dot = False
        while self.i < len(self.text):
            ch = self.text[self.i]
            if ch == '.':
                if has_dot:
                    raise IntentoSyntaxError("invalid number", self.line)
                has_dot = True
                self.i += 1
            elif ch.isdigit():
                self.i += 1
            else:
                break
        raw = self.text[start:self.i]
        if raw == '.':
            raise IntentoSyntaxError("invalid number", self.line)
        if has_dot:
            return Token('NUMBER', float(raw), start)
        return Token('NUMBER', int(raw), start)

    def _word(self) -> Token:
        start = self.i
        while self.i < len(self.text) and (self.text[self.i].isalnum() or self.text[self.i] == '_'):
            self.i += 1
        word = self.text[start:self.i]
        if word == 'plus':
            return Token('PLUS', word, start)
        if word == 'minus':
            return Token('MINUS', word, start)
        if word == 'times':
            return Token('TIMES', word, start)
        if word == 'divided':
            saved = self.i
            while self.i < len(self.text) and self.text[self.i].isspace():
                self.i += 1
            if self.text.startswith('by', self.i):
                end = self.i + 2
                if end == len(self.text) or not (self.text[end].isalnum() or self.text[end] == '_'):
                    self.i = end
                    return Token('DIVIDE', 'divided by', start)
            self.i = saved
        if word == 'true':
            return Token('BOOL', True, start)
        if word == 'false':
            return Token('BOOL', False, start)
        if word == 'empty':
            return Token('EMPTY', None, start)
        return Token('NAME', word, start)


class ExpressionParser:
    def __init__(self, text: str, memory: dict[str, Any], line: int | None = None):
        self.text = text
        self.memory = memory
        self.line = line
        self.tokens = ExpressionTokenizer(text, line).tokenize()
        self.pos = 0

    def parse(self) -> Any:
        value = self._expr()
        if self._current().kind != 'EOF':
            raise IntentoSyntaxError("unexpected token after expression", self.line)
        return value

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _match(self, kind: str) -> bool:
        if self._current().kind == kind:
            self._advance()
            return True
        return False

    def _expr(self) -> Any:
        return self._additive()

    def _additive(self) -> Any:
        left = self._multiplicative()
        while self._current().kind in ('PLUS', 'MINUS'):
            op = self._advance()
            right = self._multiplicative()
            if op.kind == 'PLUS':
                left = self._apply_plus(left, right, op.value)
            else:
                left = self._apply_numeric(left, right, '-', op.value)
        return left

    def _multiplicative(self) -> Any:
        left = self._unary()
        while self._current().kind in ('TIMES', 'DIVIDE'):
            op = self._advance()
            right = self._unary()
            if op.kind == 'TIMES':
                left = self._apply_numeric(left, right, '*', op.value)
            else:
                if is_number(right) and right == 0:
                    raise IntentoRuntimeError("division by zero", self.line)
                left = self._apply_numeric(left, right, '/', op.value)
        return left

    def _unary(self) -> Any:
        if self._match('MINUS'):
            value = self._unary()
            if not is_number(value):
                raise IntentoTypeError("unary `-` requires number", self.line)
            return -value
        return self._primary()

    def _primary(self) -> Any:
        tok = self._current()
        if tok.kind in ('STRING', 'NUMBER', 'BOOL', 'EMPTY'):
            self._advance()
            return tok.value
        if tok.kind == 'NAME':
            self._advance()
            if tok.value not in self.memory:
                raise IntentoSemanticError(f"unknown name `{tok.value}`", self.line)
            return self.memory[tok.value]
        if tok.kind == 'LPAREN':
            self._advance()
            value = self._expr()
            if not self._match('RPAREN'):
                raise IntentoSyntaxError("missing closing parenthesis", self.line)
            return value
        if tok.kind == 'LBRACK':
            return self._list_literal()
        raise IntentoSyntaxError("expected value", self.line)

    def _list_literal(self) -> list[Any]:
        self._advance()  # [
        values: list[Any] = []
        if self._match('RBRACK'):
            return values
        while True:
            values.append(self._expr())
            if self._match('RBRACK'):
                return values
            if not self._match('COMMA'):
                raise IntentoSyntaxError("expected comma or closing bracket in list", self.line)

    def _apply_plus(self, left: Any, right: Any, op_text: str) -> Any:
        if is_number(left) and is_number(right):
            return left + right
        if isinstance(left, str) or isinstance(right, str):
            return format_value(left) + format_value(right)
        raise IntentoTypeError(f"`{op_text}` requires numbers or text", self.line)

    def _apply_numeric(self, left: Any, right: Any, symbol: str, op_text: str) -> Any:
        if not (is_number(left) and is_number(right)):
            raise IntentoTypeError(f"`{op_text}` requires numbers", self.line)
        if symbol == '-':
            return left - right
        if symbol == '*':
            return left * right
        if symbol == '/':
            return left / right
        raise AssertionError(symbol)


def evaluate_expression(text: str, memory: dict[str, Any], line: int | None = None) -> Any:
    if not text.strip():
        raise IntentoSyntaxError("expected expression", line)
    return ExpressionParser(text, memory, line).parse()
