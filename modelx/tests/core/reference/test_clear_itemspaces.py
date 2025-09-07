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

    assert itemspaces[1].SpaceB[1].qux == 5
    assert len(itemspaces[1].SpaceB._named_itemspaces)

    del itemspaces.SpaceB.qux                               # Delete ref
    assert not len(itemspaces[1].SpaceB._named_itemspaces)  # Empty
    assert len(itemspaces._named_itemspaces)                # Not Empty


def test_clear_nested_itemspaces_on_change_ref(itemspaces):

    assert itemspaces[1].SpaceB[1].qux == 5
    assert len(itemspaces[1].SpaceB._named_itemspaces)

    itemspaces.SpaceB.qux = 4                              # Delete ref
    assert not len(itemspaces[1].SpaceB._named_itemspaces)  # Empty
    assert len(itemspaces._named_itemspaces)                # Not Empty
    assert itemspaces[1].SpaceB[1].qux == 4
