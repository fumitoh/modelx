from textwrap import dedent
import pytest
import pickle

from modelx.core.api import *
from modelx.core.cells import CellPointer
from modelx.core.base import get_interfaces


# ---- Test impl ----

@pytest.fixture
def pickletest():

    model = create_model('TestModel')
    space = model.create_space()

    func1 = dedent("""\
    def single_value(x):
        return 5 * x
    """)

    func2 = dedent("""\
    def mult_single_value(x):
        return 2 * single_value(x)
    """)

    func1 = space.create_cells(func=func1)
    func2 = space.create_cells(func=func2)

    func2(5)

    byte_obj = pickle.dumps(model._impl)
    unpickled = pickle.loads(byte_obj)

    return [model._impl, unpickled]


def test_unpickled_model(pickletest):

    model, unpickeld = pickletest

    errors = []

    if not model.name == unpickeld.name:
        errors.append("name did not match")

    if not hasattr(model, 'interface'):
        errors.append("no interface")

    if not hasattr(model, 'cellgraph'):
        errors.append("no cellgraph")

    assert not errors, "errors:\n{}".format("\n".join(errors))



def x_test_model_load(simplemodel):

    simplemodel.save('data\simplemodel')

    model = load_model('data\simplemodel')

    # print(model.spaces)
    # space = simplemodel.currentspace
    # simplemodel.save('data\simplemodel')
    # print(space.fibo[10])


