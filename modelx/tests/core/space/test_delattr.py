import pytest
import modelx as mx
from modelx import defcells, new_space
from modelx.core.errors import DeletedObjectError
from modelx.testing.testutil import ConfigureExecutor

@pytest.fixture
def testmodel():
    m = mx.new_model()
    yield m
    m._impl._check_sanity()
    m.close()


def test_delattr_cells(testmodel):
    """
        A---foo(x)
    """
    space = new_space("A")

    @defcells
    def foo(x):
        return 2 * x

    foo(3)
    del space.foo

    assert not foo._is_valid()

    with ConfigureExecutor():
        with pytest.raises(AttributeError):
            space.foo(3)
        with pytest.raises(DeletedObjectError):
            foo(3)


def test_delattr_space(testmodel):
    """
        A---Child
    """
    space = new_space("A")
    child = space.new_space("Child")
    del space.Child
    assert space.named_spaces == {}
    assert not child._is_valid()


def test_delattr_space_with_itemspaces(testmodel):
    """del Space deletes the space's own live itemspaces.

    The deleted space's ``param_spaces`` entries, their ``(impl, key)``
    nodes in ``model.tracegraph`` and their entries in the dynbase's
    ``_dynamic_subs`` must all be gone after deletion.
    """
    P = testmodel.new_space("P", formula=lambda i: None)
    P_impl = P._impl
    item = P[1]

    assert (1,) in P_impl.param_spaces
    assert (P_impl, (1,)) in testmodel._impl.tracegraph
    assert P_impl._dynamic_subs

    del testmodel.P

    assert not P_impl.param_spaces
    assert not P_impl._named_itemspaces
    assert (P_impl, (1,)) not in testmodel._impl.tracegraph
    assert not P_impl._dynamic_subs
    assert not item._is_valid()


def test_delattr_space_with_itemspaces_external_dynbase(testmodel):
    """del Space removes its itemspaces from a live dynbase's subs.

    R's itemspace tree has live space Q as its dynbase; deleting R must
    remove the tree's entries from ``Q._impl._dynamic_subs``.
    """
    Q = testmodel.new_space("Q")
    Q.new_cells(name="foo", formula=lambda x: x)
    R = testmodel.new_space("R", formula=lambda i: {"base": base_})
    R.base_ = Q
    R_impl = R._impl
    R[5].foo(2)

    assert Q._impl._dynamic_subs

    del testmodel.R

    assert not Q._impl._dynamic_subs
    assert not R_impl.param_spaces
    assert (R_impl, (5,)) not in testmodel._impl.tracegraph


def test_delattr_space_with_itemspaces_in_child(testmodel):
    """del Space deletes live itemspaces of its child spaces too."""
    A = testmodel.new_space("A")
    B = A.new_space("B", formula=lambda j: None)
    B[3]
    B_impl = B._impl

    del testmodel.A

    assert not B_impl.param_spaces
    assert (B_impl, (3,)) not in testmodel._impl.tracegraph
    assert not B_impl._dynamic_subs


def test_delattr_ref(testmodel):

    s = testmodel.new_space("A")
    s.x = 3
    assert s.x == 3
    del s.x

    with ConfigureExecutor():
        with pytest.raises(AttributeError):
            s.x


def test_delattr_ref_interface(testmodel):

    s = testmodel.new_space("A")
    t = testmodel.new_space("B")
    t.x = s
    assert t.x is s
    del t.x

    with ConfigureExecutor():
        with pytest.raises(AttributeError):
            t.x


def test_delattr_null_space(testmodel):
    """
        A---B---C---foo
          |
          +-b <-- B
    """
    A = testmodel.new_space('A')
    B = A.new_space('B')
    C = B.new_space('C')

    @mx.defcells
    def foo(x):
        return x

    A.b = B
    del A.B

    assert not A.b._is_valid()
    assert not foo._is_valid()
    assert not C._is_valid()
