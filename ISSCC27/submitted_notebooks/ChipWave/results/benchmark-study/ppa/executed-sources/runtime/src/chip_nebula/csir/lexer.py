from __future__ import annotations

from dataclasses import dataclass

from .ast import Span


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    value: str
    span: Span


class LexError(ValueError):
    def __init__(self, message: str, span: Span):
        super().__init__(message)
        self.message = message
        self.span = span


_MULTI_OPERATORS = ("|->", "|=>", "&&", "||", "==", "!=", "<=", ">=", "<<", ">>", "->", "##")
_SINGLE = set("{}()[],:;@'=+-*/%!~&|^<>")


def lex(text: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    line = 1
    column = 1

    def span(start_line: int, start_column: int, length: int) -> Span:
        return Span(start_line, start_column, start_line, start_column + length)

    while index < len(text):
        char = text[index]
        if char in " \t\r":
            index += 1
            column += 1
            continue
        if char == "\n":
            tokens.append(Token("NEWLINE", "\n", span(line, column, 1)))
            index += 1
            line += 1
            column = 1
            continue
        if text.startswith("//", index):
            while index < len(text) and text[index] != "\n":
                index += 1
                column += 1
            continue

        start_line, start_column = line, column
        matched = next((op for op in _MULTI_OPERATORS if text.startswith(op, index)), None)
        if matched is not None:
            tokens.append(Token(matched, matched, span(start_line, start_column, len(matched))))
            index += len(matched)
            column += len(matched)
            continue

        if char.isdigit():
            start = index
            while index < len(text) and (text[index].isdigit() or text[index] == "_"):
                index += 1
            if index < len(text) and text[index] == "'":
                index += 1
                if index >= len(text) or text[index].lower() not in "hbdo":
                    raise LexError(
                        "expected h, b, d, or o after based literal apostrophe",
                        span(start_line, start_column, index - start),
                    )
                index += 1
                digits_start = index
                while index < len(text) and (text[index].isalnum() or text[index] in "_?"):
                    index += 1
                raw = text[start:index]
                digits = text[digits_start:index].lower()
                if any(value in digits for value in ("x", "z", "?")):
                    raise LexError(
                        "X, Z, and ? digits are not legal in the 2-state v0.1 core",
                        span(start_line, start_column, index - start),
                    )
                base_code = text[digits_start - 1].lower()
                valid_digits = {
                    "b": set("01_"),
                    "o": set("01234567_"),
                    "d": set("0123456789_"),
                    "h": set("0123456789abcdef_"),
                }[base_code]
                if not digits or any(value not in valid_digits for value in digits):
                    raise LexError(
                        f"invalid digits in base-{base_code} literal {raw!r}",
                        span(start_line, start_column, index - start),
                    )
                tokens.append(
                    Token("BASED_INT", raw, span(start_line, start_column, index - start))
                )
            else:
                raw = text[start:index]
                tokens.append(Token("INT", raw, span(start_line, start_column, index - start)))
            column += index - start
            continue

        if char.isalpha() or char == "_":
            start = index
            while index < len(text) and (text[index].isalnum() or text[index] == "_"):
                index += 1
            raw = text[start:index]
            tokens.append(Token("IDENT", raw, span(start_line, start_column, index - start)))
            column += index - start
            continue

        if char == "?":
            tokens.append(Token("?", "?", span(start_line, start_column, 1)))
            index += 1
            column += 1
            continue
        if char == "$":
            tokens.append(Token("$", "$", span(start_line, start_column, 1)))
            index += 1
            column += 1
            continue
        if char in _SINGLE:
            tokens.append(Token(char, char, span(start_line, start_column, 1)))
            index += 1
            column += 1
            continue
        raise LexError(f"unexpected character {char!r}", span(start_line, start_column, 1))

    eof_span = Span(line, column, line, column)
    tokens.append(Token("EOF", "", eof_span))
    return tokens
