import modelx as mx
import pytest

@pytest.fixture
def cache_sample():
    m = mx.new_model(name='cache_sample')
    base = m.new_space("Base")
    sub = m.new_space("Sub", bases=base)

    @mx.defcells(space=base)
    def foo(other, x):
        return other(x)

    @mx.defcells(space=base)
    def bar(x):
        return 2 * x

    @mx.defcells(space=base)
    def baz(x):
        return foo(bar, x)

    yield m
    m.close()