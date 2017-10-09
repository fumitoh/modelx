import pytest
from textwrap import dedent
from modelx import *

@pytest.fixture
def samplemodel():

    model = create_model()
    base_space = model.create_space(name="base")

    foo_def = dedent("""\
    def foo(x):
        if x == 0:
            return x0
        else:
            return foo(x - 1)
    """)

    base_space.create_cells(func=foo_def)

    def paramfunc(x0):
        return {'bases': base_space}

    base_space.set_paramfunc(paramfunc)

    return model


def test_space_getitem(samplemodel):

    base = samplemodel.spaces["base"]
    derived = base[10]

    assert derived.foo(1) == 10




