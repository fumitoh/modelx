import modelx as mx
import pytest

@pytest.mark.skip
def test_circler_error():
    """
        A <-B
        |   |
        C ->D
    """
    model = mx.new_model()
    B = model.new_space("B")
    A = model.new_space("A", bases=B)
    C = A.new_space("C")

    with pytest.raises(ValueError):
        D = B.new_space("D", bases=C)

    model._impl._check_sanity()
    model.close()
