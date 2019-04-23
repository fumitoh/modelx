import pytest
import modelx as mx


def func1(x):
    return 2 * x


src_func1 ="""\
def func1(x):
    return 2 * x
"""


@pytest.fixture
def testspace():
    m, s = mx.new_model(), mx.new_space()

    s.new_cells(name="func1_code", formula=func1)
    s.new_cells(name="func1_src", formula=src_func1)

    s.new_cells(name="lambda1_code", formula=lambda x: 3 * x)
    s.new_cells(name="lambda1_src", formula="lambda x: 3 * x")

    return s


def test_formula_source(testspace):
    s = testspace

    assert s.func1_code[2] == s.func1_src[2]

    # Compare other than function name line
    assert (repr(s.func1_code.formula).split("\n")[1:]
            == repr(s.func1_src.formula).split("\n")[1:])

    assert s.lambda1_code[2] == s.lambda1_src[2]
    assert (s.lambda1_code.formula.source == "lambda x: 3 * x")
    assert s.lambda1_src.formula.source == "lambda x: 3 * x"



