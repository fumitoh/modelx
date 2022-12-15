import modelx as mx
import pytest


@pytest.fixture
def param_formula_sample():
    """
        m---SpaceA[a]---SpaceB---x
                               +-bar
    """
    def param(a):
        refs = {"y": SpaceB.x,
                "z": SpaceB.bar()}
        return {"refs": refs}

    m = mx.new_model()
    A = m.new_space("SpaceA", formula=param)
    B = A.new_space("SpaceB")

    B.x = 3

    @mx.defcells(B)
    def bar():
        return 5

    @mx.defcells(A)
    def foo():
        return y * z

    yield A
    m._impl._check_sanity()
    m.close()


def test_change_ref_in_param_formula(
        param_formula_sample
):
    A = param_formula_sample
    assert A[1].foo() == 3 * 5

    A.SpaceB.x = 7
    assert A[1].foo() == 7 * 5


def test_assign_value_to_cells_in_param_formula(
        param_formula_sample
):
    A = param_formula_sample
    assert A[1].foo() == 3 * 5

    A.SpaceB.bar = 11
    assert A[1].foo() == 3 * 11


def test_change_cells_in_param_formula(
        param_formula_sample
):
    A = param_formula_sample
    assert A[1].foo() == 3 * 5

    A.SpaceB.bar.formula = lambda : 13
    assert A[1].foo() == 3 * 13
