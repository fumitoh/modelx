import modelx as mx


def test_recalc_dynamic():
    """
        m---base[i]---child[j]---baz(y)
          |  +---foo(x)        +-qux
          |  +---bar
          +-sub(base)[j]
    """
    m = mx.new_model()
    base = mx.new_space("base", formula=lambda i: None)
    sub = mx.new_space("sub", bases=base, formula=lambda j:None)
    child = base.new_space("child", formula=lambda k:None)

    def foo(x):
        return bar

    def baz(y):
        return qux

    child.qux = 30

    base.new_cells(formula=foo)
    child.new_cells(formula=baz)

    base.bar = 3
    assert base[3].foo(1) == 3

    base.bar = 4
    assert base[3].foo(1) == 4

    assert sub[3].child.qux == 30
    assert sub[3].child[2].qux == 30
    assert sub[3].child[2].baz(4) == 30

    base.child.qux = 40
    assert sub[3].child.qux == 40
    assert sub[3].child[2].qux == 40
    assert sub[3].child[2].baz(4) == 40
