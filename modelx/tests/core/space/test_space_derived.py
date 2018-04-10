import modelx as mx
import pytest

"""
            root
              |----+----+
              |    |    |
              A--->C--->E
              |　  |    |
              B--->B2-->B3
                   |    |
                   D--->D2

"""

@pytest.fixture
def derived_sample():

    model, root = mx.new_model(), mx.new_space(name='root')
    A = root.new_space(name='A')
    B = A.new_space('B')
    C = root.new_space(name='C', bases=A)
    D = C.B.new_space(name='D')
    E = root.new_space(name='E', bases=C)

    return root


def test_defined(derived_sample):

    root = derived_sample
    assert not root.C.is_derived()
    assert not root.C.B.is_derived()
    assert not root.C.B.D.is_derived()


def test_derived_to_defined(derived_sample):

    root = derived_sample
    assert not root.E.is_derived()
    assert root.E.B.is_derived()
    assert root.E.B.D.is_derived()

    root.E.B.D.new_space(name='F')

    assert not root.E.is_derived()
    assert not root.E.B.is_derived()
    assert not root.E.B.D.is_derived()
