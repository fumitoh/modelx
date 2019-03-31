import pytest

from modelx.core.formula import Formula

funcdef1 = """\
@mx.defcells
def foo(x):
    \"\"\"docstring\"\"\"
    return 2* x
    # comment line
"""

funcdef1_nodeco = """\
def foo(x):
    \"\"\"docstring\"\"\"
    return 2* x
    # comment line
"""

funcdef1_renamed = """\
def bar(x):
    \"\"\"docstring\"\"\"
    return 2* x
    # comment line
"""

lambdadef1 = """\
foo = lambda x: ((x+3) 
      * 3)
"""

lambdadef1_extracted = """\
lambda x: ((x+3) 
      * 3)"""

lambdadef2 = "foo(x, y=lambda i: 1 + (2 * i), z=123)"
lambdadef2_extracted = "lambda i: 1 + (2 * i)"

def test_funcdef_no_name():
    f = Formula(funcdef1)
    assert f.name == "foo"
    assert f.func(1) == 2
    assert f.source == funcdef1_nodeco


def test_funcdef_with_name():
    f = Formula(funcdef1, name="bar")
    assert f.name == "bar"
    assert f.func(1) == 2
    assert f.source == funcdef1_renamed


def test_lambda_no_name():
    f = Formula(lambdadef1)
    assert f.name == "<lambda>"
    assert f.func(1) == 12
    assert f.source == lambdadef1_extracted


def test_lambda_with_name():
    f = Formula(lambdadef1, name="bar")
    assert f.name == "bar"
    assert f.func(1) == 12
    assert f.source == lambdadef1_extracted


def test_lambda_as_param():
    f = Formula(lambdadef2)
    assert f.func(1) == 3
    assert f.source == lambdadef2_extracted
