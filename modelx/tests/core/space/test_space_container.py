import pytest
from textwrap import dedent
from modelx.core.api import *
from ..data import testmodule
from ..data import testpkg

@pytest.fixture
def samplemodel():

    #       samplemodel------------+
    #        |                     |
    # base_space<--base_space2    base_space2<--derived_space2
    #        |                     |
    #       foo                   bar

    model = new_model(name='samplemodel')
    base_space = model.new_space(name='base_space')
    base_space2 = model.new_space(name='base_space2')

    foo_def = dedent("""\
    def foo(x):
        if x == 0:
            return 123
        else:
            return foo(x - 1)
    """)

    bar_def = dedent("""\
    def bar(x):
        return foo(x)
    """)

    base_space.new_cells(func=foo_def)
    model.new_space(name='derived_space', bases=base_space)
    base_space2.new_cells(func=bar_def)
    model.new_space(name='derived_space2', bases=[base_space, base_space2])

    return model


def test_change_cur_model(samplemodel):
    space = samplemodel.cur_space('base_space2')
    assert space is samplemodel.spaces['base_space2']


def test_new_cur_model(samplemodel):
    space = samplemodel.base_space.new_space()
    assert space is samplemodel.cur_space()


def test_derived_space(samplemodel):

    space = samplemodel.spaces['derived_space']
    assert space.foo(5) == 123


def test_multiple_inheritance(samplemodel):

    space = samplemodel.spaces['derived_space2']
    assert space.bar(5) ==123


def test_fullname(samplemodel):

    space = samplemodel.spaces['derived_space']
    assert space._impl.get_fullname() == "samplemodel.derived_space"


def test_new_space_from_module(samplemodel):

    space = samplemodel.new_space_from_module(testmodule, name='sample_module')
    assert set(testmodule.funcs) == set(space.cells.keys())


def test_new_space_from_module_by_name(samplemodel):

    space = samplemodel.new_space_from_module(testmodule.__name__)
    assert set(testmodule.funcs) == set(space.cells.keys())


def test_create_sapce_recursive(samplemodel):

    space = samplemodel.new_space_from_module(testpkg.__name__,
                                                 recursive=True)
    errors = []
    if not space.pkgfibo(10) == 55:
        errors.append("error with pkgfibo")

    if not space.testmod.modfibo(10) == 55:
        errors.append("error with testmod.modfibo")

    if not space.nestedpkg.nestedfibo(10) == 55:
        errors.append("error with nestedpkg.nestedfibo")

    assert not errors, "errors:\n{}".format("\n".join(errors))