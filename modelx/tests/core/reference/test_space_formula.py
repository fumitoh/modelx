import modelx as mx
import pytest

def test_update_global_in_space_formula():
    """
        m-----SpaceA
        |-x1      |
                  --SpaceA[y]----x3 == m.x1

    """
    m = mx.new_model()
    s = m.new_space("SpaceA")


    def param(y):
        return {'refs': {'x3': x1}}

    s.formula = param
    m.x1 = 3

    assert s[1].x3 == 3
    m.x1 = 4
    assert not s.itemspaces
    assert s[1].x3 == 4

    m._impl._check_sanity()
    m.close()


def test_update_cells_in_space_formula():
    """
        m-----SpaceA
        |-x1      |---------foo---> m.x1
                  --SpaceA[y]----x3 == m.x1

    """
    m = mx.new_model()
    s = m.new_space("SpaceA")

    @mx.defcells
    def foo(x):
        return x1

    def param(y):
        return {'refs': {'x3': foo(0)}}

    s.formula = param

    m.x1 = 3
    assert s[1].x3 == 3
    m.x1 = 4
    assert not s.itemspaces
    assert s[1].x3 == 4

    m._impl._check_sanity()
    m.close()

@pytest.mark.parametrize("op", ["add", "change", "delete"])
def test_dynamic_space_not_flushed(op):
    """Test input in dynamic cells"""
    m = mx.new_model()
    A = m.new_space("SpaceA")

    @mx.defcells
    def foo(x):
        pass

    A.parameters = ('i',)

    A[1].foo[1] = 1

    m.x0 = 1
    if op == "change":
        A[1].foo[1] = 1
        m.x0 = 2
    elif op == "delete":
        A[1].foo[1] = 1
        del m.x0

    assert not len(A.itemspaces)

    m._impl._check_sanity()
    m.close()


