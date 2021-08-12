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


def test_new_cells_order():
    """Test a new cells in base sapce is inserted in subspace
    before the cells defined in sub cells.
    """

    m = mx.new_model()

    s1 = m.new_space()
    s1.new_cells('bbb')
    s1.new_cells('aaa')
    s1.new_cells('ccc')

    s2 = m.new_space()
    s2.new_cells('fff')
    s2.new_cells('ddd')
    s2.new_cells('eee')

    s2.add_bases(s1)

    s1.new_cells('aba')

    assert list(s2.cells) == ['bbb', 'aaa', 'ccc', 'aba',
                              'fff', 'ddd', 'eee']