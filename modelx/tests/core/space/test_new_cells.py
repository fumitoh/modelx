import modelx as mx
from modelx.core.errors import DeletedObjectError
import pytest


def test_new_cells_in_dynbase():
    """
        m----Parent----Parent[x]<--Base
           |
           +-Base----Cells1
                   +-Cells2(create)

    """
    m = mx.new_model()
    parent = m.new_space('Parent')

    def _formula(x, y=0):
        return {"bases": Base}

    parent.formula = _formula

    base = m.new_space('Base')
    base.new_cells('Cells1', formula=lambda n: n)
    parent.Base = base
    s1 = parent[1]

    # Create new cells in dynamic base
    base.new_cells('Cells2', formula=lambda n: 2 * n)

    # Check if dynamic subspace is deleted
    with pytest.raises(DeletedObjectError):
        s1.Cells1(1)

    # Check new cells in base is reflected
    assert parent[1].Cells2(1) == 2
