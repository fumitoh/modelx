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


