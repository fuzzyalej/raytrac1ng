import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lexer import tokenise, TT, LexError
import pytest

def test_empty():
    assert tokenise("") == []

def test_number_int():
    toks = tokenise("42")
    assert toks[0].type == TT.NUMBER
    assert toks[0].value == 42.0

def test_number_float():
    toks = tokenise("3.14")
    assert toks[0].type == TT.NUMBER
    assert abs(toks[0].value - 3.14) < 1e-9

def test_negative_number():
    toks = tokenise("-1.5")
    assert toks[0].type == TT.NUMBER
    assert toks[0].value == -1.5

def test_string():
    toks = tokenise('"hello"')
    assert toks[0].type == TT.STRING
    assert toks[0].value == "hello"

def test_ident():
    toks = tokenise("my_var")
    assert toks[0].type == TT.IDENT
    assert toks[0].value == "my_var"

def test_punctuation():
    toks = tokenise("{ } ( ) [ ] , =")
    types = [t.type for t in toks]
    assert types == [TT.LBRACE, TT.RBRACE, TT.LPAREN, TT.RPAREN,
                     TT.LBRACKET, TT.RBRACKET, TT.COMMA, TT.EQUALS]

def test_operators():
    toks = tokenise("+ - * /")
    types = [t.type for t in toks]
    assert types == [TT.PLUS, TT.MINUS, TT.STAR, TT.SLASH]

def test_comment_stripped():
    toks = tokenise("42 // this is a comment\n99")
    values = [t.value for t in toks]
    assert values == [42.0, 99.0]

def test_multiline():
    src = "let x = 1.0\nlet y = 2.0"
    toks = tokenise(src)
    assert toks[0].value == "let"
    assert toks[1].value == "x"

def test_unknown_char_raises():
    with pytest.raises(LexError):
        tokenise("@")

def test_line_numbers():
    toks = tokenise("a\nb")
    assert toks[0].line == 1
    assert toks[1].line == 2

def test_minus_with_space_is_operator():
    # "-" followed by space then digit = subtraction operator + number
    toks = tokenise("x - 1")
    types = [t.type for t in toks]
    assert types == [TT.IDENT, TT.MINUS, TT.NUMBER]

def test_minus_no_space_is_negative():
    # "-" immediately followed by digit = negative number
    toks = tokenise("-1.5")
    assert len(toks) == 1
    assert toks[0].type == TT.NUMBER
    assert toks[0].value == -1.5

def test_eqeq():
    toks = tokenise("==")
    assert toks[0].type == TT.EQEQ

def test_neq():
    toks = tokenise("!=")
    assert toks[0].type == TT.NEQ

def test_lt():
    toks = tokenise("<")
    assert toks[0].type == TT.LT

def test_gt():
    toks = tokenise(">")
    assert toks[0].type == TT.GT

def test_lte():
    toks = tokenise("<=")
    assert toks[0].type == TT.LTE

def test_gte():
    toks = tokenise(">=")
    assert toks[0].type == TT.GTE

def test_equals_still_works():
    toks = tokenise("let x = 1")
    types = [t.type for t in toks]
    assert TT.EQUALS in types
    assert TT.EQEQ not in types

def test_comparison_expression_tokens():
    toks = tokenise("a == b")
    assert toks[1].type == TT.EQEQ
