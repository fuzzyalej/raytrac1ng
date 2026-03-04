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


# ---------------------------------------------------------------------------
# Statement parser + evaluator
# ---------------------------------------------------------------------------

_BLOCK_KEYWORDS = {
    "camera", "light",
    "sphere", "plane", "box", "cylinder", "cone", "torus",
}

_MATERIAL_FIELDS = {"color", "opacity", "reflect", "ior"}


def _child_env(parent: dict) -> dict:
    """Create a child scope that inherits from parent."""
    child = dict(parent)
    return child


class _ProgramParser(Parser):
    """Extends Parser with statement-level parsing."""

    def __init__(self, tokens, env, base_path: str = ".", imported: set | None = None):
        super().__init__(tokens, env)
        self._base_path = base_path
        self._imported = imported if imported is not None else set()

    def parse_program(self) -> list:
        items = []
        while not self._at_end():
            items.extend(self._statement())
        return items

    def _statement(self) -> list:
        tok = self._peek()
        if tok is None:
            return []

        # let statement
        if tok.type == TT.IDENT and tok.value == "let":
            return self._let_stmt()

        # import statement
        if tok.type == TT.IDENT and tok.value == "import":
            return self._import_stmt()

        # for statement
        if tok.type == TT.IDENT and tok.value == "for":
            return self._for_stmt()

        # block statement (camera, sphere, etc.)
        if tok.type == TT.IDENT and tok.value in _BLOCK_KEYWORDS:
            item = self._block_stmt(self._env)
            return [item] if item is not None else []

        raise ParseError(f"unexpected token {tok.value!r} at line {tok.line}")

    def _let_stmt(self) -> list:
        self._advance()  # consume 'let'
        name_tok = self._expect(TT.IDENT)
        name = name_tok.value
        self._expect(TT.EQUALS)

        # let x = material { ... }
        if self._match_ident("material"):
            self._advance()
            mat = self._material_block()
            self._env[name] = mat
        else:
            val = self._expr()
            self._env[name] = val
        return []

    def _material_block(self) -> dict:
        """Parse material { ... } and return a dict of material props."""
        self._expect(TT.LBRACE)
        props = dict(_MAT_DEFAULTS)  # start with defaults
        while not self._check(TT.RBRACE):
            key_tok = self._expect(TT.IDENT)
            key = key_tok.value
            if key not in _MATERIAL_FIELDS:
                raise ParseError(f"unknown material field {key!r}")
            val = self._expr()
            props[key] = val
        self._expect(TT.RBRACE)
        return props

    def _import_stmt(self) -> list:
        self._advance()  # consume 'import'
        path_tok = self._expect(TT.STRING)
        rel_path = path_tok.value
        abs_path = str(Path(self._base_path) / rel_path)

        if abs_path in self._imported:
            raise ParseError(f"circular import: {abs_path!r}")
        self._imported.add(abs_path)

        try:
            src = open(abs_path).read()
        except FileNotFoundError:
            raise ParseError(f"import not found: {abs_path!r}")

        tokens = tokenise(src)
        child_base = str(Path(abs_path).parent)
        sub = _ProgramParser(tokens, self._env, child_base, self._imported)
        items = sub.parse_program()
        # merge environment back (import makes variables available)
        self._env.update(sub._env)
        return items

    def _for_stmt(self) -> list:
        self._advance()  # consume 'for'
        var_tok = self._expect(TT.IDENT)
        var = var_tok.value

        # expect 'in'
        in_tok = self._expect(TT.IDENT)
        if in_tok.value != "in":
            raise ParseError(f"expected 'in', got {in_tok.value!r}")

        # range(...) or expression
        if self._match_ident("range"):
            self._advance()  # consume 'range'
            self._expect(TT.LPAREN)
            first = self._expr()
            if self._check(TT.COMMA):
                self._advance()
                second = self._expr()
                start, stop = int(first), int(second)
            else:
                start, stop = 0, int(first)
            self._expect(TT.RPAREN)
            iterable = range(start, stop)
        else:
            val = self._expr()
            if not isinstance(val, list):
                raise ParseError("for loop iterable must be a list")
            iterable = val

        # body
        self._expect(TT.LBRACE)
        body_tokens_start = self._pos
        # collect body tokens up to matching }
        body_tokens = self._collect_block_tokens()

        items = []
        for v in iterable:
            child_env = _child_env(self._env)
            child_env[var] = float(v) if isinstance(v, int) else v
            sub = _ProgramParser(body_tokens, child_env, self._base_path, self._imported)
            items.extend(sub.parse_program())
        return items

    def _collect_block_tokens(self) -> list:
        """Collect tokens up to and consuming the matching RBRACE.
        Handles nested braces."""
        depth = 1
        body = []
        while not self._at_end():
            tok = self._advance()
            if tok.type == TT.LBRACE:
                depth += 1
                body.append(tok)
            elif tok.type == TT.RBRACE:
                depth -= 1
                if depth == 0:
                    break
                body.append(tok)
            else:
                body.append(tok)
        return body

    def _block_stmt(self, env: dict):
        """Parse a named block (sphere, plane, camera, etc.)."""
        kind_tok = self._advance()
        kind = kind_tok.value
        self._expect(TT.LBRACE)

        props = {}
        mat_ref = None

        while not self._check(TT.RBRACE):
            key_tok = self._expect(TT.IDENT)
            key = key_tok.value

            if key == "material":
                # material <name>  (identifier reference, not a block)
                name_tok = self._expect(TT.IDENT)
                mat_name = name_tok.value
                if mat_name not in self._env:
                    raise ParseError(f"undefined material {mat_name!r}")
                mat_ref = self._env[mat_name]
                if not isinstance(mat_ref, dict):
                    raise ParseError(f"{mat_name!r} is not a material")
            else:
                val = self._expr()
                props[key] = val

        self._expect(TT.RBRACE)

        # Apply material defaults, then material ref, then inline props
        merged = dict(_MAT_DEFAULTS)
        if mat_ref:
            merged.update(mat_ref)
        merged.update({k: v for k, v in props.items() if k in _MATERIAL_FIELDS})

        # Build the right scene item
        try:
            return _build_scene_item(kind, props, merged)
        except KeyError as e:
            raise ParseError(f"missing required field {e} in {kind} block")


def _build_scene_item(kind: str, props: dict, mat: dict):
    """Convert raw props dict + resolved material into a scene item dataclass."""
    color   = mat["color"]
    opacity = mat["opacity"]
    reflect = mat["reflect"]
    ior     = mat["ior"]

    if kind == "camera":
        return SceneCamera(
            location=props["location"],
            look_at=props["look_at"],
            fov=float(props["fov"]),
        )
    if kind == "light":
        return SceneLight(
            position=props["position"],
            radius=float(props.get("radius", 0.0)),
            samples=int(props.get("samples", 16)),
        )
    if kind == "sphere":
        return SceneSphere(
            center=props["center"],
            radius=float(props["radius"]),
            color=color, opacity=opacity, reflect=reflect, ior=ior,
        )
    if kind == "plane":
        return ScenePlane(
            normal=props["normal"],
            offset=float(props["offset"]),
            color=color, opacity=opacity, reflect=reflect, ior=ior,
        )
    if kind == "box":
        return SceneBox(
            min=props["min"],
            max=props["max"],
            color=color, opacity=opacity, reflect=reflect, ior=ior,
        )
    if kind == "cylinder":
        return SceneCylinder(
            bottom=props["bottom"],
            top=props["top"],
            radius=float(props["radius"]),
            color=color, opacity=opacity, reflect=reflect, ior=ior,
        )
    if kind == "cone":
        return SceneCone(
            bottom=props["bottom"],
            top=props["top"],
            bottom_radius=float(props["bottom_radius"]),
            top_radius=float(props["top_radius"]),
            color=color, opacity=opacity, reflect=reflect, ior=ior,
        )
    if kind == "torus":
        return SceneTorus(
            center=props["center"],
            axis=props["axis"],
            major_radius=float(props["major_radius"]),
            minor_radius=float(props["minor_radius"]),
            color=color, opacity=opacity, reflect=reflect, ior=ior,
        )
    raise ParseError(f"unknown block type {kind!r}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_source(src: str, base_path: str = ".") -> list:
    """Parse a .pow source string; return list of scene item dataclasses."""
    tokens = tokenise(src)
    env = dict(BUILTINS)
    parser = _ProgramParser(tokens, env, base_path)
    return parser.parse_program()
