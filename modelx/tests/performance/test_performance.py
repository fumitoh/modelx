import modelx as mx
import pytest


@pytest.mark.skip()
def test_cells_calls(benchmark):

    s = mx.new_model().new_space()

    @mx.defcells
    def foo(t):
        return 1

    @mx.defcells
    def bar(t, u):
        return foo(0)

    def run():
        for x in range(10):
            for y in range(100):
                bar(x, y)

    benchmark(run)

    assert sum(bar.values())


@pytest.mark.skip()
def test_space_items(benchmark):

    s = mx.new_model().new_space()

    def foo(x):
        return x

    for _ in range(100):
        c = s.new_cells()
        c.formula = foo

    s.formula = lambda i: None

    def run():
        for i in range(1000):
            s[i]

    benchmark(run)
