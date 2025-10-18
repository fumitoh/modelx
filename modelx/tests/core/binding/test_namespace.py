import modelx as mx


def test_namespace_in_fromula():
    m = mx.new_model()
    s = m.new_space("Space1")

    @mx.defcells(space=s)
    def foo():
        return _model

    @mx.defcells(space=s)
    def bar():
        return _space

    assert foo() is m._impl.namespace
    assert bar() is s._impl.namespace

    m._impl._check_sanity()
    m.close()