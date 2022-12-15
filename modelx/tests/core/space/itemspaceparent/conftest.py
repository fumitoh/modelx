import modelx as mx
import inspect
import pytest


def paramfunc1(i):
    return None


def paramfunc2(i, j):
    return None


@pytest.fixture(params=[paramfunc1, paramfunc2])
def itemspacetest(request):

    paramfunc = request.param
    m, s = mx.new_model(), mx.new_space(formula=paramfunc)

    @mx.defcells
    def foo(x):
        return x

    paramlen = len(inspect.signature(paramfunc).parameters)
    for i in range(10):
        assert s(*((i,) * paramlen)).foo(i) == i

    yield paramlen, s
    m._impl._check_sanity()
    m.close()

