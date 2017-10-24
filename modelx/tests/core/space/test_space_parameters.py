import pytest
from textwrap import dedent
from modelx import *

@pytest.fixture
def samplemodel():

    model = new_model()
    base_space = model.new_space(name="base")

    foo_def = dedent("""\
    def foo(x):
        if x == 0:
            return x0
        else:
            return foo(x - 1)
    """)

    base_space.new_cells(func=foo_def)

    def paramfunc(x0):
        return {'bases': base_space}

    base_space.set_paramfunc(paramfunc)

    return model


def test_space_getitem(samplemodel):

    base = samplemodel.spaces["base"]
    derived = base[10]

    assert derived.foo(1) == 10


def test_paramfunc(samplemodel):
    """Test if paramfunc passes parameters properly."""

    # [idx, x, n]
    data = [[0, 50, 10], [1, 60, 15], [2, 70, 5]]

    def params(idx):
        return {'name': 'TestSpace%s' % idx,
                'bases': _self}

    space = samplemodel.new_space(name='TestSpace', paramfunc=params)

    funcx = dedent("""
    def x():
        return data[idx][1]
    """)

    funcn = dedent("""
    def n():
        return data[idx][2]
    """)

    space.new_cells(func=funcx)
    space.new_cells(func=funcn)

    space.data = data

    check = True
    for idx, x, n in data:
        check = check and space[idx].name == 'TestSpace' + str(idx)
        check = check and space[idx].x == x
        check = check and space[idx].n == n

    assert check



