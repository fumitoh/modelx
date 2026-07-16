import pytest
import modelx as mx


@pytest.fixture
def testmodel():
    m = mx.new_model()
    yield m
    m._impl._check_sanity()
    m.close()


def test_del_derived_ref_raises(testmodel):
    """Deleting a derived ref raises ValueError and leaves it intact."""
    A = testmodel.new_space("A")
    A.x = 1
    B = testmodel.new_space("B", bases=A)

    with pytest.raises(ValueError, match="cannot delete derived ref 'x'"):
        del B.x

    assert B.x == 1
    assert B._impl.own_refs["x"].is_derived()


def test_del_ref_overriding_derived(testmodel):
    """Deleting a defined override reverts to the inherited ref."""
    A = testmodel.new_space("A")
    A.x = 1
    B = testmodel.new_space("B", bases=A)

    B.x = 5
    assert B.x == 5
    assert not B._impl.own_refs["x"].is_derived()

    del B.x

    assert B.x == 1
    assert B._impl.own_refs["x"].is_derived()


def test_del_ref_created_by_new_space(testmodel):
    """Refs created by new_space(refs=...) are never registered in
    ValueRegistry but must still be deletable."""
    C = testmodel.new_space("C", refs={"y": 42})

    del C.y

    assert "y" not in C.refs
