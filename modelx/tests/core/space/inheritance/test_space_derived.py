import modelx as mx
import pytest

"""
            root
              |----+----+
              |    |    |
              A--->C--->E
              |　  |    |
              B--->CB-->EC*
                   |    |
                  CBD-->ECD*

"""


@pytest.fixture
def derived_sample():

    model, root = mx.new_model(), mx.new_space(name="root")
    A = root.new_space(name="A")
    B = A.new_space("B")
    C = root.new_space(name="C", bases=A)
    D = C.B.new_space(name="D")
    E = root.new_space(name="E", bases=C)

    return model


pickleparam = [False, True]


@pytest.fixture(params=pickleparam)
def unpickled_model(request, derived_sample, tmpdir_factory):

    model = derived_sample
    if request.param:
        file = str(tmpdir_factory.mktemp("data").join("testmodel.mx"))
        model.save(file)
        model.close()
        model = mx.open_model(file)

    yield model
    model.close()


def test_defined(unpickled_model):

    root = unpickled_model.root
    assert not root.C.is_derived()
    assert not root.C.B.is_derived()
    assert not root.C.B.D.is_derived()


@pytest.mark.parametrize("member", ["space", "cells", "ref"])
def test_derived_to_defined(unpickled_model, member):

    root = unpickled_model.root
    assert not root.E.is_derived()
    assert root.E.B.is_derived()
    assert root.E.B.D.is_derived()

    if member == "space":
        root.E.B.D.new_space(name="F")
    elif member == "cells":
        root.E.B.D.new_cells(name="F")
    else:
        root.E.B.D.F = 123

    assert not root.E.is_derived()
    assert not root.E.B.is_derived()
    assert not root.E.B.D.is_derived()
