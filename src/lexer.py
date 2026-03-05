from enum import Enum, auto
from dataclasses import dataclass


class TT(Enum):
    # Literals
    NUMBER   = auto()
    STRING   = auto()
    IDENT    = auto()

    # Punctuation
    LBRACE   = auto()   # {
    RBRACE   = auto()   # }
    LPAREN   = auto()   # (
    RPAREN   = auto()   # )
    LBRACKET = auto()   # [
    RBRACKET = auto()   # ]
    COMMA    = auto()   # ,
    EQUALS   = auto()   # =

    # Operators
    PLUS     = auto()   # +
    MINUS    = auto()   # -
    STAR     = auto()   # *
    SLASH    = auto()   # /

    # Comparison operators
    EQEQ     = auto()   # ==
    NEQ      = auto()   # !=
    LT       = auto()   # <
    GT       = auto()   # >
    LTE      = auto()   # <=
    GTE      = auto()   # >=

    EOF      = auto()


@dataclass
class Token:
    type: TT
    value: str | float
    line: int

    def __eq__(self, other):
        if not isinstance(other, Token):
            return NotImplemented
        return self.type == other.type and self.value == other.value and self.line == other.line


class LexError(Exception):
    pass


_SINGLE_CHAR = {
    '{': TT.LBRACE,
    '}': TT.RBRACE,
    '(': TT.LPAREN,
    ')': TT.RPAREN,
    '[': TT.LBRACKET,
    ']': TT.RBRACKET,
    ',': TT.COMMA,
    '+': TT.PLUS,
    '-': TT.MINUS,
    '*': TT.STAR,
    '/': TT.SLASH,
}
# Note: '=' is intentionally excluded — handled inline below so that '=='
# (EQEQ) is matched first before a bare '=' (EQUALS).


def tokenise(src: str) -> list[Token]:
    tokens = []
    i = 0
    line = 1
    n = len(src)

    while i < n:
        c = src[i]

        # Newline
        if c == '\n':
            line += 1
            i += 1
            continue

        # Whitespace
        if c in ' \t\r':
            i += 1
            continue

        # Comment
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            while i < n and src[i] != '\n':
                i += 1
            continue

        # String
        if c == '"':
            i += 1
            start = i
            while i < n and src[i] != '"':
                i += 1
            if i >= n:
                raise LexError(f"unterminated string at line {line}")
            tokens.append(Token(TT.STRING, src[start:i], line))
            i += 1
            continue

        # Negative number: '-' immediately followed by a digit
        if c == '-' and i + 1 < n and src[i + 1].isdigit():
            i += 1
            start = i
            while i < n and src[i].isdigit():
                i += 1
            if i < n and src[i] == '.' and i + 1 < n and src[i + 1].isdigit():
                i += 1
                while i < n and src[i].isdigit():
                    i += 1
            tokens.append(Token(TT.NUMBER, -float(src[start:i]), line))
            continue

        # Number
        if c.isdigit():
            start = i
            while i < n and src[i].isdigit():
                i += 1
            if i < n and src[i] == '.' and i + 1 < n and src[i + 1].isdigit():
                i += 1
                while i < n and src[i].isdigit():
                    i += 1
            tokens.append(Token(TT.NUMBER, float(src[start:i]), line))
            continue

        # Identifier
        if c.isalpha() or c == '_':
            start = i
            while i < n and (src[i].isalnum() or src[i] == '_'):
                i += 1
            tokens.append(Token(TT.IDENT, src[start:i], line))
            continue

        # Multi-char and comparison operators (must come before single-char fallback)
        if c == '=' and i + 1 < n and src[i + 1] == '=':
            tokens.append(Token(TT.EQEQ, '==', line))
            i += 2
            continue
        if c == '!' and i + 1 < n and src[i + 1] == '=':
            tokens.append(Token(TT.NEQ, '!=', line))
            i += 2
            continue
        if c == '<' and i + 1 < n and src[i + 1] == '=':
            tokens.append(Token(TT.LTE, '<=', line))
            i += 2
            continue
        if c == '>' and i + 1 < n and src[i + 1] == '=':
            tokens.append(Token(TT.GTE, '>=', line))
            i += 2
            continue
        if c == '<':
            tokens.append(Token(TT.LT, '<', line))
            i += 1
            continue
        if c == '>':
            tokens.append(Token(TT.GT, '>', line))
            i += 1
            continue
        if c == '=':
            tokens.append(Token(TT.EQUALS, '=', line))
            i += 1
            continue

        # Single-char tokens
        if c in _SINGLE_CHAR:
            tokens.append(Token(_SINGLE_CHAR[c], c, line))
            i += 1
            continue

        raise LexError(f"unexpected char {c!r} at line {line}")

    return tokens
