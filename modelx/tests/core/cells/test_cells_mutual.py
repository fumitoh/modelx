from textwrap import dedent
import pytest
import modelx as mx


def test_cells_mutual():

    m = mx.new_model()
    space = m.new_space()

    func1 = dedent(
        """\
    def single_value(x):
        return 5 * x
    """
    )

    func2 = dedent(
        """\
    def mult_single_value(x):
        return 2 * single_value(x)
    """
    )

    f1 = space.new_cells(formula=func1)
    f2 = space.new_cells(formula=func2)

    assert f2(5) == 50

    m._impl._check_sanity()
    m.close()