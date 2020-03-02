import modelx as mx


def test_overriden_refs():
    m = mx.new_model()
    base = mx.new_space("base")
    sub = mx.new_space("sub", bases=base)

    def foo(x):
        return bar

    base.new_cells(formula=foo)

    m.bar = 2                   # Add global ref
    base.bar = 3                # Add base ref
    assert sub.foo(1) == 3      # Base ref

    base.bar = 4                # Change base ref
    assert sub.foo(1) == 4      # Updated base ref

    sub.bar = 5                 # Add self ref
    assert sub.foo(1) == 5      # self ref

    del sub.bar                 # Del self ref
    assert sub.foo(1) == 4      # Base ref

    del base.bar                # Del base ref
    assert sub.foo(1) == 2      # Global ref





