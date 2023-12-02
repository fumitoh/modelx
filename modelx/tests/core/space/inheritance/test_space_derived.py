import modelx as mx
import pytest

"""
            root
              |----+----+
              |    |    |
              A--->C--->E
              |　  |    |
              B--->CB-->EB*
                   |    |
                  CBD-->EBD*

"""


@pytest.fixture
def derived_sample():
    """
    root---A---B
      +---C(A)
    """

    model, root = mx.new_model(), mx.new_space(name="root")
    A = root.new_space(name="A")
    B = A.new_space("B")
    C = root.new_space(name="C", bases=A)
    D = C.B.new_space(name="D")
    E = root.new_space(name="E", bases=C)

    return model


@pytest.fixture
def unpickled_model(derived_sample, tmpdir_factory):

    model = derived_sample
    yield model
    model._impl._check_sanity()
    model.close()

@pytest.mark.skip
def test_defined(unpickled_model):

    root = unpickled_model.root
    assert not root.C._is_derived()
    assert not root.C.B._is_derived()
    assert not root.C.B.D._is_derived()


@pytest.mark.skip
@pytest.mark.parametrize("member", ["space", "cells", "ref"])
def test_derived_to_defined(unpickled_model, member):

    root = unpickled_model.root
    assert not root.E._is_derived()
    assert root.E.B._is_derived()
    assert root.E.B.D._is_derived()

    if member == "space":
        root.E.B.D.new_space(name="F")
    elif member == "cells":
        root.E.B.D.new_cells(name="F")
    else:
        root.E.B.D.F = 123

    assert not root.E._is_derived()
    assert not root.E.B._is_derived()
    assert not root.E.B.D._is_derived()
