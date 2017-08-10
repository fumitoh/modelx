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

    assert space._impl.fullname == "samplemodel.derived_space"