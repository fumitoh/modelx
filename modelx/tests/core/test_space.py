from textwrap import dedent

import pytest

from modelx.core.api import *


@pytest.fixture
def samplespace():

    space = create_model(name='samplemodel').create_space(name='samplespace')

    @defcells(space)
    def foo(x):
        if x == 0:
            return 123
        else:
            return foo(x - 1)

    return space


def test_create(samplespace):
    assert samplespace in get_currentmodel().spaces.values()


def test_get_cells_by_cells(samplespace):
    assert samplespace.cells["foo"][10] == 123


def test_get_cells_by_getattr(samplespace):
    assert samplespace.foo[10] == 123


def test_create_cells_from_module(samplespace):
    from .data import sample

    # module_name = 'modelx.tests.core.data.sample'
    names = __name__.split('.')
    names = names[:-1] + ['data', 'sample']
    module_name = '.'.join(names)

    cells = create_cells_from_module(module_name)
    assert set(sample.funcs) == set(cells.keys())


def test_mro_root(samplespace):
    space = get_currentspace()
    assert [space._impl] == space._impl.mro


def test_derived_spaces(samplespace):

    model = get_currentmodel()

    space_a = model.create_space()

    @defcells
    def cells_a(x):
        if x == 0:
            return 1
        else:
            return cells_a(x - 1)

    space_b = model.create_space(bases=space_a)

    space_b.cells_a[0] = 2

    assert space_a.cells_a[2] == 1 and space_b.cells_a(2) == 2


def test_factory(samplespace):

    model = get_currentmodel()
    base = model.create_space(factory=lambda x, y: {'bases': get_self()})

    distance_def = dedent("""\
    def distance():
        return (x ** 2 + y ** 2) ** 0.5
    """)

    base.create_cells(func=distance_def)

    assert base[3, 4].distance == 5

# ----- Testing _impl methods ----


def test_fullname(samplespace):
    assert samplespace._impl.get_fullname() == "samplemodel.samplespace"


def test_fullname_omit_model(samplespace):
    assert samplespace._impl.get_fullname(omit_model=True) == 'samplespace'