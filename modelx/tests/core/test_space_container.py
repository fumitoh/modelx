import pytest
from textwrap import dedent
from modelx.core.api import *


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

    # print('name is\n', space._impl.fullname)

    assert space._impl.get_fullname() == "samplemodel.derived_space"


def test_create_space_from_module(samplemodel):
    from .data import sample

    space = samplemodel.create_space_from_module(sample, name='sample_module')

    assert set(sample.funcs) == set(space.cells.keys())


def test_create_space_from_module_by_name(samplemodel):
    from .data import sample

    space = samplemodel.create_space_from_module(sample.__name__)

    assert set(sample.funcs) == set(space.cells.keys())


def test_create_sapce_recursive(samplemodel):
    from .data import testpkg

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