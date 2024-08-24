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


@pytest.mark.parametrize("pattern", range(3))
def test_cached_in_uncached(pattern):
    """Calling cached cells in cacheless cells

    The called cached cells is a precedent of cached callers of the cacheless
    """
    m = mx.new_model()
    s = m.new_space()
    @mx.defcells(space=s)
    def foo(x):
        return bar(x)

    if pattern == 0:
        @mx.defcells(space=s)
        def bar(x):
            return x + baz(3)

        bar.is_cached = False

    elif pattern == 1:
        @mx.defcells(space=s, is_cached=False)
        def bar(x):
            return x + baz(3)

    elif pattern == 2:

        @mx.uncached
        def bar(x):
            return x + baz(3)

    else:
        raise ValueError


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


@pytest.mark.parametrize("pattern", range(3))
def test_redefine_uncached(pattern):

    m = mx.new_model()
    s = m.new_space()

    @mx.defcells
    def foo(x):
        return bar(x)

    if pattern == 0:

        @mx.defcells
        def bar(x):
            return 3 * x

        bar.is_cached = False

    elif pattern == 1:
        @mx.defcells(is_cached=False)
        def bar(x):
            return 3 * x

    elif pattern == 2:
        @mx.uncached
        def bar(x):
            return 3 * x

    assert foo(3) == 9

    @mx.defcells    # defcells won't change is_cached
    def bar(x):
        return 4 * x

    assert foo(3) == 12
    assert bar.is_cached is False

    m.close()


def test_unhashable_arg():

    m = mx.new_model()

    @mx.defcells
    def foo(x):
        return bar([1, 2, 3])

    @mx.defcells
    def bar(l: list):
        return l

    bar.is_cached = False

    foo(0)

    assert foo.preds(0)[0].obj is bar
    assert foo.preds(0)[0].args is None

    m.close()
