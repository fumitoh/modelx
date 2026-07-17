import modelx as mx
import pytest


@pytest.fixture
def itemspaces():
    """
        Model---SpaceA[i]---SpaceB[j]
                |          |
                |          +---qux=5 (ref)
                |
                +---foo=3 (ref)
    """

    def param(i):
        refs = {"bar": foo}
        return {"refs": refs}

    def param2(j):
        refs = {"baz": qux}
        return {"refs": refs}

    m = mx.new_model()
    A = m.new_space("SpaceA", formula=param)
    B = A.new_space("SpaceB", formula=param2)

    A.foo = 3
    B.qux = 5

    assert A[1] is A._named_itemspaces["__Space1"]
    yield A
    m._impl._check_sanity()
    m.close()


def test_clear_itemspaces_on_del_ref(itemspaces):
    del itemspaces.foo                               # Delete ref
    assert not len(itemspaces._named_itemspaces)     # Empty


def test_clear_itemspaces_on_change_ref(itemspaces):
    itemspaces.foo = 4                               # Delete ref
    assert not len(itemspaces._named_itemspaces)     # Empty
    assert itemspaces[1].foo == 4


def test_clear_nested_itemspaces_on_del_ref(itemspaces):
    """SpaceB is a dynbase of SpaceA[1]'s tree (its refs are baked into
    the tree's ``_dynbase_refs``), so a SpaceB ref edit deletes
    SpaceA[1] wholesale (Phase 7 closure semantics; asserted before
    any re-access re-creates it)."""
    a1 = itemspaces[1]
    assert a1.SpaceB[1].qux == 5
    assert len(a1.SpaceB._named_itemspaces)

    del itemspaces.SpaceB.qux                               # Delete ref
    assert not len(itemspaces._named_itemspaces)            # A[1] deleted
    assert not a1._is_valid()

    assert not len(itemspaces[1].SpaceB._named_itemspaces)  # Re-created
    assert len(itemspaces._named_itemspaces)


def test_clear_nested_itemspaces_on_change_ref(itemspaces):
    a1 = itemspaces[1]
    assert a1.SpaceB[1].qux == 5
    assert len(a1.SpaceB._named_itemspaces)

    itemspaces.SpaceB.qux = 4                               # Change ref
    assert not len(itemspaces._named_itemspaces)            # A[1] deleted
    assert not a1._is_valid()

    assert not len(itemspaces[1].SpaceB._named_itemspaces)  # Re-created
    assert len(itemspaces._named_itemspaces)
    assert itemspaces[1].SpaceB[1].qux == 4
