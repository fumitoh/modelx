
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