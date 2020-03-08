import modelx as mx


def test_recalc_attrref():

    m = mx.new_model()
    s = m.new_space()

    @mx.defcells
    def foo(x):
        return bar.x

    @mx.defcells
    def qux(y):
        return bar[1].x

    s2 = mx.new_space("bar", formula=lambda a: None)
    s.bar = s2

    s2.x = "bar"
    assert foo(3) == qux(3) == "bar"

    s2.x = "baz"
    assert foo(3) == qux(3) == "baz"
