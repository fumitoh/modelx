import pytest

from modelx.core.api import *
from modelx.core.cells import CellPointer
from modelx.core.base import get_interfaces


@pytest.fixture
def simplemodel():

    model = create_model()
    space = model.create_space()

    @defcells
    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo(x - 1) + fibo(x - 2)

    return model


def x_test_model_load(simplemodel):

    simplemodel.save('data\simplemodel')

    model = load_model('data\simplemodel')

    # print(model.spaces)
    # space = simplemodel.currentspace
    # simplemodel.save('data\simplemodel')
    # print(space.fibo[10])
