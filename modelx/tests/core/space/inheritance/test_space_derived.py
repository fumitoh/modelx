import modelx as mx
import pytest


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
