from modelx import new_model, defcells

import pytest


@pytest.fixture
def sample_space():

    space = new_model(name="samplemodel").new_space(name="samplespace")

    funcdef = """def func(x): return 2 * x"""

    space.new_cells(formula=funcdef)

    @defcells
    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo(x - 1) + fibo[x - 2]

    @defcells
    def double(x):
        double[x] = 2 * x

    @defcells
    def return_last(x):
        return return_last(x - 1)

    def func1(x):
        return 5 * x

    def func2(y):
        return 6 * y

    func1, func2 = defcells(func1, func2)

    @defcells
    def no_param():
        return 5

    @defcells
    def matchtest(x, y, z):
        return None

    matchtest.allow_none = True

    matchtest[1, 2, 3] = 123
    matchtest[1, 2, None] = 120
    matchtest[1, None, 3] = 103
    matchtest[None, 2, 3] = 23
    matchtest[1, None, None] = 100
    matchtest[None, 2, None] = 20
    matchtest[None, None, 3] = 3
    matchtest[None, None, None] = 0

    return space