
import modelx as mx
import pytest


@pytest.mark.parametrize("base_name", ["Base"])   # TODO: Fix when base is Child
def test_del_base_in_model(base_name):
    """
        m---Base---Child---foo
          |  |
          |  +--bar
          |
          +-Sub(Base)

    """
    m, base = mx.new_model(), mx.new_space("Base")
    child = base.new_space("Child")
    cells = base.new_cells("bar")
    child.new_cells("foo")
    base = base if base_name == "Base" else child

    m.new_space("Sub", bases=base)

    del m.Base

    assert not m.Sub.cells
    assert not m.Sub.spaces

    m._impl._check_sanity()
    m.close()


def test_del_space_with_relative_ref_from_surviving_base():
    """Deleting a tree targeted by a surviving base's relative ref
    succeeds.

    S inherits from X and A; both define a 'relative' ref r pointing at
    X.C. Deleting X re-derives S.r from A.r, whose value lies inside
    the deleted tree; the value must be treated as already invalid so
    that the failing relative resolution does not abort the deletion
    (pre-pipeline deletion order).
    """
    m = mx.new_model()
    X = m.new_space("X")
    C = X.new_space("C")
    X.set_ref("r", C, "relative")
    S = m.new_space("S", bases=X)
    A = m.new_space("A")
    A.set_ref("r", C, "relative")
    S.add_bases(A)

    del m.X

    assert "X" not in m.spaces
    assert "r" in S._impl.own_refs   # derived from A.r, now invalid

    m._impl._check_sanity()
    m.close()