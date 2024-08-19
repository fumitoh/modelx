import modelx as mx
import pytest


@pytest.mark.parametrize("space", ["Base", "Sub"])
def test_cache(cache_sample, space):

    m = cache_sample
    s = m.spaces[space]
    s.foo.is_cached = False
    s.baz(3)

    nodes = s.baz.preds(3)
    print(nodes)

    assert repr(nodes[-1]) == f"cache_sample.{space}.foo(other, x)"


def test_cached_in_cacheless():
    """Calling cached cells in cacheless cells

    The called cached cells is a precedent of cached callers of the cacheless
    """
    m = mx.new_model()
    s = m.new_space()
    @mx.defcells(space=s)
    def foo(x):
        return bar(x)

    @mx.defcells(space=s)
    def bar(x):
        return x + baz(3)

    bar.is_cached = False

    @mx.defcells(space=s)
    def baz(x):
        return x

    @mx.defcells(space=s)
    def foo2(x):
        return bar(x)

    foo(3)
    foo2(3)

    for preds in [foo.preds(3), foo2.preds(3)]:
        assert preds[0].obj is baz
        assert preds[0].args == (3,)
        assert preds[1].obj is bar
        assert preds[1].args is None

    m.close()


def test_redefine_cacheless():

    m = mx.new_model()
    s = m.new_space()

    @mx.defcells
    def foo(x):
        return bar(x)

    @mx.defcells
    def bar(x):
        return 3 * x

    bar.is_cached = False

    assert foo(3) == 9

    @mx.defcells
    def bar(x):
        return 4 * x

    assert foo(3) == 12

    m.close()
