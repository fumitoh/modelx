import modelx as mx


def test_del_cells():

    s = mx.new_model().new_space()

    @mx.defcells
    def foo(x):
        return x

    @mx.defcells
    def bar(x):
        return 2 * foo(x)

    assert bar(1) == 2
    assert len(bar)
    del s.foo
    assert "foo" not in s.cells
    assert not len(bar)