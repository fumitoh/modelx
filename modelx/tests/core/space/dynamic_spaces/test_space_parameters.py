import pytest
from textwrap import dedent
from modelx import *


@pytest.fixture
def samplemodel():

    model = new_model()
    base_space = model.new_space(name="base")

    foo_def = dedent(
        """\
    def foo(x):
        if x == 0:
            return x0
        else:
            return foo(x - 1)
    """
    )

    base_space.new_cells(formula=foo_def)

    def formula(x0):
        return {"bases": _space}

    base_space.set_formula(formula)

    return model


def test_space_getitem(samplemodel):

    base = samplemodel.spaces["base"]
    derived = base[10]

    assert derived.foo(1) == 10


def test_formula(samplemodel):
    """Test if formula passes parameters properly."""

    # [idx, x, n]
    data = [[0, 50, 10], [1, 60, 15], [2, 70, 5]]

    def params(idx):
        return {"name": "TestSpace%s" % idx}
        # 'bases': _self}

    space = samplemodel.new_space(name="TestSpace", formula=params)

    funcx = dedent(
        """
    def x():
        return data[idx][1]
    """
    )

    funcn = dedent(
        """
    def n():
        return data[idx][2]
    """
    )

    space.new_cells(formula=funcx)
    space.new_cells(formula=funcn)
    space.data = data

    for idx, x, n in data:
        assert space[idx].name == "TestSpace" + str(idx)
        assert space[idx].x == x
        assert space[idx].n == n


def test_parameters(samplemodel):
    assert samplemodel.base.parameters == ("x0",)
