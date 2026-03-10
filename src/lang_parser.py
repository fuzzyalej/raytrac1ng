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


# ---------------------------------------------------------------------------
# Closure (user-defined function)
# ---------------------------------------------------------------------------

@dataclass
class Closure:
    params: list
    body_tokens: list
    captured_env: dict
    base_path: str
    imported: set


@dataclass
class SceneSphere:
    center:    tuple
    radius:    float
    color:     tuple  = (1.0, 1.0, 1.0)
    opacity:   float  = 1.0
    reflect:   float  = 0.0
    ior:       float  = 1.0
    transform: object = None


@dataclass
class ScenePlane:
    normal:    tuple
    offset:    float
    color:     tuple  = (1.0, 1.0, 1.0)
    opacity:   float  = 1.0
    reflect:   float  = 0.0
    ior:       float  = 1.0
    transform: object = None


@dataclass
class SceneBox:
    min:       tuple
    max:       tuple
    color:     tuple  = (1.0, 1.0, 1.0)
    opacity:   float  = 1.0
    reflect:   float  = 0.0
    ior:       float  = 1.0
    transform: object = None


@dataclass
class SceneCylinder:
    bottom:    tuple
    top:       tuple
    radius:    float
    color:     tuple  = (1.0, 1.0, 1.0)
    opacity:   float  = 1.0
    reflect:   float  = 0.0
    ior:       float  = 1.0
    transform: object = None


@dataclass
class SceneCone:
    bottom:        tuple
    top:           tuple
    bottom_radius: float
    top_radius:    float
    color:         tuple  = (1.0, 1.0, 1.0)
    opacity:       float  = 1.0
    reflect:       float  = 0.0
    ior:           float  = 1.0
    transform:     object = None


@dataclass
class SceneTorus:
    center:       tuple
    axis:         tuple
    major_radius: float
    minor_radius: float
    color:        tuple  = (1.0, 1.0, 1.0)
    opacity:      float  = 1.0
    reflect:      float  = 0.0
    ior:          float  = 1.0
    transform:    object = None


@dataclass
class SceneMesh:
    file:      str
    color:     tuple | None = None   # None = use OBJ/MTL per-triangle colors
    opacity:   float | None = None   # None = use OBJ/MTL per-triangle opacity
    reflect:   float        = 0.0
    ior:       float        = 1.0
    transform: object       = None


@dataclass
class SceneTransform:
    scale:     tuple = (1.0, 1.0, 1.0)
    rotate:    tuple = (0.0, 0.0, 0.0)   # XYZ euler degrees
    translate: tuple = (0.0, 0.0, 0.0)


@dataclass
class SceneCSGUnion:
    children:  list
    fuse:      bool   = False
    color:     tuple  = None
    opacity:   float  = None
    reflect:   float  = None
    ior:       float  = None
    transform: object = None


@dataclass
class SceneCSGIntersection:
    children:  list
    color:     tuple  = None
    opacity:   float  = None
    reflect:   float  = None
    ior:       float  = None
    transform: object = None


@dataclass
class SceneCSGDifference:
    left:      object
    right:     object
    color:     tuple  = None
    opacity:   float  = None
    reflect:   float  = None
    ior:       float  = None
    transform: object = None


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
# Comparison operator set
# ---------------------------------------------------------------------------

_COMP_OPS = {TT.EQEQ, TT.NEQ, TT.LT, TT.GT, TT.LTE, TT.GTE}


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

    def _compare(self):
        """Parse comparison: expr COMPOP expr  ->  bool, or just expr."""
        left = self._expr()
        tok = self._peek()
        if tok is None or tok.type not in _COMP_OPS:
            return left
        op = self._advance().type
        right = self._expr()
        # Only compare numbers
        if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
            raise ParseError(
                f"comparison only valid on numbers, got {type(left).__name__!r} and {type(right).__name__!r}"
            )
        if op == TT.EQEQ: return left == right
        if op == TT.NEQ:  return left != right
        if op == TT.LT:   return left <  right
        if op == TT.GT:   return left >  right
        if op == TT.LTE:  return left <= right
        if op == TT.GTE:  return left >= right


# ---------------------------------------------------------------------------
# Statement parser + evaluator
# ---------------------------------------------------------------------------

_BLOCK_KEYWORDS = {
    "camera", "light",
    "sphere", "plane", "box", "cylinder", "cone", "torus",
    "union", "intersection", "difference",
    "mesh",
}

_MATERIAL_FIELDS = {"color", "opacity", "reflect", "ior"}

_STMT_KEYWORDS = {"let", "for", "import", "if"} | _BLOCK_KEYWORDS


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
        self._pending_items: list = []

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

        # if statement
        if tok.type == TT.IDENT and tok.value == "if":
            items, _ = self._if_stmt()   # discard return value at top level
            return items

        # block statement (camera, sphere, etc.)
        if tok.type == TT.IDENT and tok.value in _BLOCK_KEYWORDS:
            item = self._block_stmt(self._env)
            return [item] if item is not None else []

        # Closure call statement at top level: IDENT(args)
        if tok.type == TT.IDENT:
            name = tok.value
            val = self._env.get(name)
            if isinstance(val, Closure):
                nxt = self._tokens[self._pos + 1] if self._pos + 1 < len(self._tokens) else None
                if nxt is not None and nxt.type == TT.LPAREN:
                    self._advance()  # consume IDENT
                    self._advance()  # consume (
                    args = []
                    if not self._check(TT.RPAREN):
                        args.append(self._expr())
                        while self._check(TT.COMMA):
                            self._advance()
                            args.append(self._expr())
                    self._expect(TT.RPAREN)
                    emitted, _ = self._call_closure(val, args)
                    return emitted

        raise ParseError(f"unexpected token {tok.value!r} at line {tok.line}")

    def _let_stmt(self) -> list:
        self._advance()  # consume 'let'
        name_tok = self._expect(TT.IDENT)
        name = name_tok.value
        self._expect(TT.EQUALS)

        # let x = fn(...) { ... }
        if self._match_ident("fn"):
            self._advance()  # consume 'fn'
            self._expect(TT.LPAREN)
            params = []
            if not self._check(TT.RPAREN):
                params.append(self._expect(TT.IDENT).value)
                while self._check(TT.COMMA):
                    self._advance()
                    params.append(self._expect(TT.IDENT).value)
            self._expect(TT.RPAREN)
            self._expect(TT.LBRACE)
            body_tokens = self._collect_block_tokens()
            closure = Closure(
                params=params,
                body_tokens=body_tokens,
                captured_env=dict(self._env),
                base_path=self._base_path,
                imported=self._imported,
            )
            self._env[name] = closure
            return []

        # let x = material { ... }
        if self._match_ident("material"):
            self._advance()
            mat = self._material_block()
            self._env[name] = mat
            return []

        # let x = transform { ... }
        if self._match_ident("transform"):
            self._advance()   # consume 'transform'
            t = self._transform_block()
            self._env[name] = t
            return []

        # let x = <expr>
        val = self._expr()
        self._env[name] = val
        # Flush any items emitted by closure calls during expression evaluation
        emitted = list(self._pending_items)
        self._pending_items.clear()
        return emitted

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

    _TRANSFORM_FIELDS = {"scale", "rotate", "translate"}

    def _transform_block(self) -> SceneTransform:
        """Parse transform { ... } and return a SceneTransform."""
        self._expect(TT.LBRACE)
        scale     = (1.0, 1.0, 1.0)
        rotate    = (0.0, 0.0, 0.0)
        translate = (0.0, 0.0, 0.0)

        while not self._check(TT.RBRACE):
            key_tok = self._expect(TT.IDENT)
            key = key_tok.value
            if key not in self._TRANSFORM_FIELDS:
                raise ParseError(f"unknown transform field {key!r}")
            val = self._expr()
            if key == "scale":
                # Accept scalar (uniform) or vec3
                if isinstance(val, (int, float)):
                    scale = (float(val), float(val), float(val))
                else:
                    scale = val
            elif key == "rotate":
                rotate = val
            elif key == "translate":
                translate = val

        self._expect(TT.RBRACE)
        return SceneTransform(scale=scale, rotate=rotate, translate=translate)

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

        # Route CSG blocks to dedicated parser
        if kind in ("union", "intersection", "difference"):
            return self._block_stmt_csg(kind)

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
            elif key == "transform":
                name_tok = self._expect(TT.IDENT)
                t_name = name_tok.value
                if t_name not in self._env:
                    raise ParseError(f"undefined transform {t_name!r}")
                t_val = self._env[t_name]
                if not isinstance(t_val, SceneTransform):
                    raise ParseError(f"{t_name!r} is not a transform")
                props["__transform__"] = t_val
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
        transform_val = props.pop("__transform__", None)
        try:
            item = _build_scene_item(kind, props, merged, mat_ref is not None)
        except KeyError as e:
            raise ParseError(f"missing required field {e} in {kind} block")
        if transform_val is not None:
            item.transform = transform_val
        return item

    def _block_stmt_csg(self, kind: str):
        """Parse a CSG block (union / intersection / difference)."""
        self._expect(TT.LBRACE)

        fuse          = False
        color         = None
        opacity       = None
        reflect       = None
        ior           = None
        mat_ref       = None
        transform_val = None
        children      = []

        _CHILD_KEYWORDS = {
            "sphere", "plane", "box", "cylinder", "cone", "torus",
            "union", "intersection", "difference",
        }

        while not self._check(TT.RBRACE):
            key_tok = self._expect(TT.IDENT)
            key     = key_tok.value

            if key == "fuse":
                if kind != "union":
                    raise ParseError(f"'fuse' is only valid in union blocks, not {kind!r}")
                val = self._expect(TT.IDENT).value
                if val not in ("yes", "no"):
                    raise ParseError(f"fuse value must be 'yes' or 'no', got {val!r}")
                fuse = (val == "yes")

            elif key == "material":
                name_tok = self._expect(TT.IDENT)
                mat_name = name_tok.value
                if mat_name not in self._env:
                    raise ParseError(f"undefined material {mat_name!r}")
                mat_ref = self._env[mat_name]
                if not isinstance(mat_ref, dict):
                    raise ParseError(f"{mat_name!r} is not a material")

            elif key == "transform":
                name_tok = self._expect(TT.IDENT)
                t_name = name_tok.value
                if t_name not in self._env:
                    raise ParseError(f"undefined transform {t_name!r}")
                t_val = self._env[t_name]
                if not isinstance(t_val, SceneTransform):
                    raise ParseError(f"{t_name!r} is not a transform")
                transform_val = t_val

            elif key in _MATERIAL_FIELDS:
                val = self._expr()
                if key == "color":   color   = val
                if key == "opacity": opacity = float(val)
                if key == "reflect": reflect = float(val)
                if key == "ior":     ior     = float(val)

            elif key in _CHILD_KEYWORDS:
                child = self._parse_csg_child(key)
                children.append(child)

            else:
                raise ParseError(f"unexpected field {key!r} in {kind} block")

        self._expect(TT.RBRACE)

        # Apply mat_ref defaults, inline overrides win
        if mat_ref:
            if color   is None: color   = mat_ref.get("color")
            if opacity is None: opacity = mat_ref.get("opacity")
            if reflect is None: reflect = mat_ref.get("reflect")
            if ior     is None: ior     = mat_ref.get("ior")

        if kind == "union":
            return SceneCSGUnion(children=children, fuse=fuse,
                                 color=color, opacity=opacity,
                                 reflect=reflect, ior=ior,
                                 transform=transform_val)

        if kind == "intersection":
            if len(children) < 2:
                raise ParseError("intersection requires at least 2 children")
            return SceneCSGIntersection(children=children,
                                        color=color, opacity=opacity,
                                        reflect=reflect, ior=ior,
                                        transform=transform_val)

        if kind == "difference":
            if len(children) != 2:
                raise ParseError(
                    f"difference requires exactly 2 children, got {len(children)}"
                )
            return SceneCSGDifference(left=children[0], right=children[1],
                                      color=color, opacity=opacity,
                                      reflect=reflect, ior=ior,
                                      transform=transform_val)

    def _parse_csg_child(self, kind: str):
        """Parse a child of a CSG block: primitive or nested CSG."""
        _CSG_KINDS = {"union", "intersection", "difference"}
        if kind in _CSG_KINDS:
            return self._block_stmt_csg(kind)
        # Primitive: parse the { ... } block manually
        self._expect(TT.LBRACE)
        props   = {}
        mat_ref = None
        while not self._check(TT.RBRACE):
            key_tok = self._expect(TT.IDENT)
            key     = key_tok.value
            if key == "material":
                name_tok = self._expect(TT.IDENT)
                mat_name = name_tok.value
                if mat_name not in self._env:
                    raise ParseError(f"undefined material {mat_name!r}")
                mat_ref = self._env[mat_name]
            elif key == "transform":
                name_tok = self._expect(TT.IDENT)
                t_name = name_tok.value
                if t_name not in self._env:
                    raise ParseError(f"undefined transform {t_name!r}")
                t_val = self._env[t_name]
                if not isinstance(t_val, SceneTransform):
                    raise ParseError(f"{t_name!r} is not a transform")
                props["__transform__"] = t_val
            else:
                props[key] = self._expr()
        self._expect(TT.RBRACE)

        merged = dict(_MAT_DEFAULTS)
        if mat_ref:
            merged.update(mat_ref)
        merged.update({k: v for k, v in props.items() if k in _MATERIAL_FIELDS})

        transform_val = props.pop("__transform__", None)
        try:
            item = _build_scene_item(kind, props, merged, mat_ref is not None)
        except KeyError as e:
            raise ParseError(f"missing required field {e} in {kind} block")
        if transform_val is not None:
            item.transform = transform_val
        return item

    def _call_closure(self, closure: Closure, args: list) -> tuple:
        """Execute a closure. Returns (scene_items, return_value)."""
        if len(args) != len(closure.params):
            raise ParseError(
                f"function expects {len(closure.params)} argument(s), got {len(args)}"
            )
        child_env = dict(closure.captured_env)
        # Make new bindings (defined after this closure) visible, but don't overwrite captures
        for k, v in self._env.items():
            if k not in closure.captured_env:
                child_env[k] = v
        for param, arg in zip(closure.params, args):
            child_env[param] = arg
        sub = _FunctionParser(
            closure.body_tokens, child_env,
            closure.base_path, closure.imported
        )
        return sub.parse_function_body()

    def _if_stmt(self) -> tuple:
        """Parse if/else-if/else. Returns (scene_items, last_value)."""
        self._advance()  # consume 'if'
        condition = self._compare()
        self._expect(TT.LBRACE)
        body_tokens = self._collect_block_tokens()

        branches = [(condition, body_tokens)]

        # else if / else
        while self._match_ident("else"):
            self._advance()  # consume 'else'
            if self._match_ident("if"):
                self._advance()  # consume 'if'
                cond = self._compare()
                self._expect(TT.LBRACE)
                btoks = self._collect_block_tokens()
                branches.append((cond, btoks))
            else:
                # plain else
                self._expect(TT.LBRACE)
                btoks = self._collect_block_tokens()
                branches.append((True, btoks))
                break

        # evaluate the first true branch
        for cond, btoks in branches:
            if cond:
                sub = _FunctionParser(btoks, _child_env(self._env),
                                      self._base_path, self._imported)
                items, val = sub.parse_function_body()
                return items, val

        return [], None

    def _primary(self):
        tok = self._peek()
        # Closure call in expression context
        if (tok is not None and tok.type == TT.IDENT):
            name = tok.value
            val = self._env.get(name)
            if val is None:
                val = BUILTINS.get(name)
            if isinstance(val, Closure):
                # peek ahead for (
                nxt = self._tokens[self._pos + 1] if self._pos + 1 < len(self._tokens) else None
                if nxt is not None and nxt.type == TT.LPAREN:
                    self._advance()  # consume IDENT
                    self._advance()  # consume (
                    args = []
                    if not self._check(TT.RPAREN):
                        args.append(self._expr())
                        while self._check(TT.COMMA):
                            self._advance()
                            args.append(self._expr())
                    self._expect(TT.RPAREN)
                    emitted, return_val = self._call_closure(val, args)
                    self._pending_items.extend(emitted)
                    if return_val is None:
                        raise ParseError(
                            f"function {name!r} used as an expression but its body does not return a value"
                        )
                    return return_val
        # fall through to base class
        return super()._primary()


# ---------------------------------------------------------------------------
# _FunctionParser: parses a function body
# ---------------------------------------------------------------------------

class _FunctionParser(_ProgramParser):
    """Parses a function body; tracks the last expression as a return value."""

    def parse_function_body(self) -> tuple:
        """Returns (scene_items: list, return_value: Any)."""
        items = []
        last_value = None
        while not self._at_end():
            tok = self._peek()
            if tok is None:
                break

            # Known statement keyword or block keyword
            if tok.type == TT.IDENT and tok.value in _STMT_KEYWORDS:
                if tok.value == "if":
                    stmt_items, val = self._if_stmt()
                    items.extend(stmt_items)
                    items.extend(self._pending_items)
                    self._pending_items.clear()
                    last_value = val
                else:
                    stmt_items = self._statement()
                    items.extend(stmt_items)
                    items.extend(self._pending_items)
                    self._pending_items.clear()
                    last_value = None
                continue

            # Closure call statement: IDENT ( where IDENT resolves to a Closure
            if tok.type == TT.IDENT and self._resolves_to_closure(tok.value):
                stmt_items, val = self._closure_call_stmt()
                items.extend(stmt_items)
                last_value = val
                continue

            # Bare expression = return value (must be last)
            val = self._expr()
            items.extend(self._pending_items)
            self._pending_items.clear()
            last_value = val
            if not self._at_end():
                raise ParseError(
                    "unexpected token after return expression in function body"
                )

        return items, last_value

    def _resolves_to_closure(self, name: str) -> bool:
        val = self._env.get(name)
        nxt = self._tokens[self._pos + 1] if self._pos + 1 < len(self._tokens) else None
        return isinstance(val, Closure) and nxt is not None and nxt.type == TT.LPAREN

    def _closure_call_stmt(self) -> tuple:
        """Parse name(args) where name is a Closure. Returns (items, return_value)."""
        name = self._advance().value   # IDENT
        self._expect(TT.LPAREN)
        args = []
        if not self._check(TT.RPAREN):
            args.append(self._expr())
            while self._check(TT.COMMA):
                self._advance()
                args.append(self._expr())
        self._expect(TT.RPAREN)
        closure = self._env[name]
        return self._call_closure(closure, args)


# ---------------------------------------------------------------------------
# _build_scene_item helper
# ---------------------------------------------------------------------------

def _build_scene_item(kind: str, props: dict, mat: dict, mat_ref_present: bool = False):
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
    if kind == "mesh":
        if "file" not in props:
            raise ParseError("mesh block requires a 'file' field")
        return SceneMesh(
            file=str(props["file"]),
            color=mat["color"] if ("color" in props or mat_ref_present) else None,
            opacity=mat["opacity"] if ("opacity" in props or mat_ref_present) else None,
            # reflect and ior are not representable in OBJ/MTL format,
            # so they are always applied as overrides (defaulting to 0.0 / 1.0).
            reflect=float(mat["reflect"]),
            ior=float(mat["ior"]),
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
