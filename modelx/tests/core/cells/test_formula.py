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

    s.new_cells(name="lambda1_code",
                formula=lambda x: 3 * x)
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


def test_set_formula(sample_for_rename_and_formula):

    model = sample_for_rename_and_formula
    sub1 = model.Sub1
    sub2 = model.Sub2
    foo = model.Parent.Child1.Foo

    foo.formula = lambda x: 2 * x

    assert not len(foo)
    assert not len(sub1.Child1.Foo)
    assert sub1.Child1.Foo(1) == 2  # Changed
    assert tuple(sub2.itemspaces) == (2,)   # sub2[2] not deleted
    assert sub2[1].Foo(1) == 2  # Changed
    assert sub2[2].Bar(1) == 1


def test_set_formula_with_defined_sub(sample_for_rename_and_formula):
    """Check defined sub cells formula is not changed"""
    model = sample_for_rename_and_formula
    sub1 = model.Sub1
    sub2 = model.Sub2
    foo = model.Parent.Child1.Foo

    sub1.Child1.Foo.formula = lambda x: 3 * x
    sub1.Child1.Foo(1)

    foo.formula = lambda x: 2 * x

    assert not len(foo)
    assert len(sub1.Child1.Foo)         # Not Cleared
    assert sub1.Child1.Foo(1) == 3      # Not Changed