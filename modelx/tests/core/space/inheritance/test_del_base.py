
import modelx as mx
import pytest


def test_del_defined_base():
    """
    A <- B <- C
    |    |    |
    X    X    X*
    |    |    |
    M    M*N  M*N*

    delete B.X

    A <- B <- C
    |    |    |
    X    X*   X*
    |    |    |
    M    M*   M*
    """
    m = mx.new_model()
    m.new_space("A").new_space("X").new_cells("M")
    m.new_space("B").new_space("X").new_cells("N")
    m.B.add_bases(m.A)
    m.new_space("C", bases=m.B)

    assert hasattr(m.B.X, "M")
    assert hasattr(m.B.X, "N")
    assert hasattr(m.C.X, "M")
    assert hasattr(m.C.X, "N")

    del m.B.X

    assert hasattr(m.B.X, "M")
    assert not hasattr(m.B.X, "N")
    assert hasattr(m.C.X, "M")
    assert not hasattr(m.C.X, "N")