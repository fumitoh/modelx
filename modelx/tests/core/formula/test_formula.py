import pytest

from modelx.core.formula import Formula

funcdef1 = """\
@mx.defcells
def foo(x):
    \"\"\"docstring\"\"\"
    return 2* x
    # comment line
"""

lambdadef1 = """\
foo = lambda x: ((x+3) 
      * 3)
"""


def test_funcdef_no_name():
    f = Formula(funcdef1)
    assert f.name == "foo"
    assert f.func(1) == 2
    assert f.source == funcdef1


def test_funcdef_with_name():
    f = Formula(funcdef1, name="bar")
    assert f.name == "bar"
    assert f.func(1) == 2
    assert f.source == funcdef1


def test_lambda_no_name():
    f = Formula(lambdadef1)
    assert f.name == "<lambda>"
    assert f.func(1) == 12
    assert f.source == lambdadef1


def test_lambda_with_name():
    f = Formula(lambdadef1, name="bar")
    assert f.name == "bar"
    assert f.func(1) == 12
    assert f.source == lambdadef1
