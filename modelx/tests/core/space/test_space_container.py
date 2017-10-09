import pytest
from textwrap import dedent
from modelx.core.api import *
from ..data import testmodule
from ..data import testpkg

@pytest.fixture
def samplemodel():

    model = create_model(name='samplemodel')
    base_space = model.create_space(name='base_space')
    base_space2 = model.create_space(name='base_space2')

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

    base_space.create_cells(func=foo_def)
    model.create_space(name='derived_space', bases=base_space)
    base_space2.create_cells(func=bar_def)
    model.create_space(name='derived_space2', bases=[base_space, base_space2])

    return model


def test_derived_space(samplemodel):

    space = samplemodel.spaces['derived_space']
    assert space.foo(5) == 123


def test_multiple_inheritance(samplemodel):

    space = samplemodel.spaces['derived_space2']
    assert space.bar(5) ==123


def test_fullname(samplemodel):

    space = samplemodel.spaces['derived_space']
    assert space._impl.get_fullname() == "samplemodel.derived_space"


def test_create_space_from_module(samplemodel):

    space = samplemodel.create_space_from_module(testmodule, name='sample_module')
    assert set(testmodule.funcs) == set(space.cells.keys())


def test_create_space_from_module_by_name(samplemodel):

    space = samplemodel.create_space_from_module(testmodule.__name__)
    assert set(testmodule.funcs) == set(space.cells.keys())


def test_create_sapce_recursive(samplemodel):

    space = samplemodel.create_space_from_module(testpkg.__name__,
                                                 recursive=True)
    errors = []
    if not space.pkgfibo(10) == 55:
        errors.append("error with pkgfibo")

    if not space.testmod.modfibo(10) == 55:
        errors.append("error with testmod.modfibo")

    if not space.nestedpkg.nestedfibo(10) == 55:
        errors.append("error with nestedpkg.nestedfibo")

    assert not errors, "errors:\n{}".format("\n".join(errors))