"""
Recursive-descent parser and evaluator for the POW scene language.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from pathlib import Path
from lexer import tokenise, Token, TT


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ParseError(Exception):
    pass


# ---------------------------------------------------------------------------
# Built-in environment
# ---------------------------------------------------------------------------

BUILTINS: dict = {
    "pi":  math.pi,
    "sin": math.sin,
    "cos": math.cos,
    "abs": abs,
}


# ---------------------------------------------------------------------------
# Scene item dataclasses (produced by the statement evaluator)
# ---------------------------------------------------------------------------

@dataclass
class SceneCamera:
    location: tuple
    look_at:  tuple
    fov:      float


@dataclass
class SceneLight:
    position: tuple
    radius:   float = 0.0
    samples:  int   = 16


_MAT_DEFAULTS = dict(color=(1.0, 1.0, 1.0), opacity=1.0, reflect=0.0, ior=1.0)


@dataclass
class SceneSphere:
    center:  tuple
    radius:  float
    color:   tuple = (1.0, 1.0, 1.0)
    opacity: float = 1.0
    reflect: float = 0.0
    ior:     float = 1.0


@dataclass
class ScenePlane:
    normal:  tuple
    offset:  float
    color:   tuple = (1.0, 1.0, 1.0)
    opacity: float = 1.0
    reflect: float = 0.0
    ior:     float = 1.0


@dataclass
class SceneBox:
    min:     tuple
    max:     tuple
    color:   tuple = (1.0, 1.0, 1.0)
    opacity: float = 1.0
    reflect: float = 0.0
    ior:     float = 1.0


@dataclass
class SceneCylinder:
    bottom:  tuple
    top:     tuple
    radius:  float
    color:   tuple = (1.0, 1.0, 1.0)
    opacity: float = 1.0
    reflect: float = 0.0
    ior:     float = 1.0


@dataclass
class SceneCone:
    bottom:        tuple
    top:           tuple
    bottom_radius: float
    top_radius:    float
    color:         tuple = (1.0, 1.0, 1.0)
    opacity:       float = 1.0
    reflect:       float = 0.0
    ior:           float = 1.0


@dataclass
class SceneTorus:
    center:       tuple
    axis:         tuple
    major_radius: float
    minor_radius: float
    color:        tuple = (1.0, 1.0, 1.0)
    opacity:      float = 1.0
    reflect:      float = 0.0
    ior:          float = 1.0


# ---------------------------------------------------------------------------
# Vec3 helpers
# ---------------------------------------------------------------------------

def _vec_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def _vec_mul(v, s):
    return (v[0] * s, v[1] * s, v[2] * s)

def _vec_div(v, s):
    return (v[0] / s, v[1] / s, v[2] / s)

def _vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def _is_vec(v):
    return isinstance(v, tuple) and len(v) == 3


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    def __init__(self, tokens: list[Token], env: dict):
        self._tokens = tokens
        self._pos = 0
        self._env = env

    # --- token stream helpers ---

    def _peek(self) -> Token | None:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, tt: TT) -> Token:
        tok = self._peek()
        if tok is None or tok.type != tt:
            got = repr(tok.value) if tok else "EOF"
            raise ParseError(f"expected {tt.name}, got {got}")
        return self._advance()

    def _check(self, tt: TT) -> bool:
        tok = self._peek()
        return tok is not None and tok.type == tt

    def _match_ident(self, name: str) -> bool:
        tok = self._peek()
        return tok is not None and tok.type == TT.IDENT and tok.value == name

    def _at_end(self) -> bool:
        return self._peek() is None

    # --- expression parser ---

    def parse_expr(self):
        return self._expr()

    def _expr(self):
        left = self._term()
        while self._peek() and self._peek().type in (TT.PLUS, TT.MINUS):
            op = self._advance().type
            right = self._term()
            if op == TT.PLUS:
                if _is_vec(left) and _is_vec(right):
                    left = _vec_add(left, right)
                elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    left = left + right
                else:
                    raise ParseError("type mismatch in +")
            else:
                if _is_vec(left) and _is_vec(right):
                    left = _vec_sub(left, right)
                elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    left = left - right
                else:
                    raise ParseError("type mismatch in -")
        return left

    def _term(self):
        left = self._unary()
        while self._peek() and self._peek().type in (TT.STAR, TT.SLASH):
            op = self._advance().type
            right = self._unary()
            if op == TT.STAR:
                if _is_vec(left) and isinstance(right, (int, float)):
                    left = _vec_mul(left, right)
                elif isinstance(left, (int, float)) and _is_vec(right):
                    left = _vec_mul(right, left)
                elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    left = left * right
                else:
                    raise ParseError("type mismatch in *")
            else:
                if _is_vec(left) and isinstance(right, (int, float)):
                    left = _vec_div(left, right)
                elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    left = left / right
                else:
                    raise ParseError("type mismatch in /")
        return left

    def _unary(self):
        if self._check(TT.MINUS):
            self._advance()
            val = self._unary()
            if isinstance(val, (int, float)):
                return -val
            if _is_vec(val):
                return (-val[0], -val[1], -val[2])
            raise ParseError("cannot negate this value")
        return self._primary()

    def _primary(self):
        tok = self._peek()
        if tok is None:
            raise ParseError("unexpected end of input")

        # Number literal
        if tok.type == TT.NUMBER:
            self._advance()
            return float(tok.value)

        # String literal
        if tok.type == TT.STRING:
            self._advance()
            return tok.value

        # List literal [...]
        if tok.type == TT.LBRACKET:
            self._advance()
            items = []
            if not self._check(TT.RBRACKET):
                items.append(self._expr())
                while self._check(TT.COMMA):
                    self._advance()
                    items.append(self._expr())
            self._expect(TT.RBRACKET)
            return items

        # Parenthesised expression or vec3
        if tok.type == TT.LPAREN:
            self._advance()
            first = self._expr()
            if self._check(TT.COMMA):
                # vec3: (x, y, z)
                self._advance()
                second = self._expr()
                self._expect(TT.COMMA)
                third = self._expr()
                self._expect(TT.RPAREN)
                return (float(first), float(second), float(third))
            else:
                self._expect(TT.RPAREN)
                return first

        # Identifier: variable reference or function call
        if tok.type == TT.IDENT:
            self._advance()
            name = tok.value
            # Function call
            if self._check(TT.LPAREN):
                self._advance()
                args = []
                if not self._check(TT.RPAREN):
                    args.append(self._expr())
                    while self._check(TT.COMMA):
                        self._advance()
                        args.append(self._expr())
                self._expect(TT.RPAREN)
                # Look up in env first, then builtins
                fn = self._env.get(name) or BUILTINS.get(name)
                if fn is None:
                    raise ParseError(f"undefined function {name!r}")
                if not callable(fn):
                    raise ParseError(f"{name!r} is not callable")
                return fn(*args)
            # Variable reference
            if name in self._env:
                return self._env[name]
            if name in BUILTINS:
                return BUILTINS[name]
            raise ParseError(f"undefined variable {name!r}")

        raise ParseError(f"unexpected token {tok.value!r} at line {tok.line}")
