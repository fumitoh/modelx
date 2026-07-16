import modelx as mx


def test_space_not_self_observer():
    """D-12 (Phase 2): a space no longer registers in its own observer list.

    The space's own namespace-dependent caches are invalidated through
    the direct on_ns_invalidated hook in NamespaceServer.on_notify instead.
    """
    m = mx.new_model()
    s = m.new_space("Space1")
    impl = s._impl
    assert all(obs is not impl for obs in impl.observers)

    m._impl._check_sanity()
    m.close()


def test_direct_hook_invalidates_space_formula():
    """A ref change rebinds the space's own (param) formula via the hook."""
    m = mx.new_model()
    s = m.new_space("Space1", formula=lambda i: {"refs": {"y": x * i}})
    s.x = 2
    assert s[3].y == 6
    s.x = 5
    assert s[3].y == 15

    m._impl._check_sanity()
    m.close()


def test_setstate_strips_self_observation():
    """Unpickled state saved before D-12 drops the self-observation edge.

    Without this, notifying a space restored from an old runtime pickle
    would recurse infinitely (the identity dispatch that used to absorb
    the self-edge is gone).
    """
    from modelx.core.space import UserSpaceImpl

    obj = UserSpaceImpl.__new__(UserSpaceImpl)
    other = object()
    obj.__setstate__({"observers": [obj, other]})
    assert obj.observers == [other]


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