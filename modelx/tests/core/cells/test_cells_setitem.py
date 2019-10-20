import pytest


def test_setitem(sample_space):
    sample_space.fibo[0] = 1
    sample_space.return_last[4] = 5
    assert sample_space.fibo[2] == 2
    assert sample_space.return_last(5) == 5


def test_setitem_str(sample_space):
    cells = sample_space.new_cells(formula="lambda s: 2 * s")
    cells["ABC"] = "DEF"
    assert cells["ABC"] == "DEF"


def test_setitem_in_cells(sample_space):
    assert sample_space.double[3] == 6


def test_setitem_in_formula_invalid_assignment_error(sample_space):

    def invalid_in_formula_assignment(x):
        invalid_in_formula_assignment[x + 1] = 3 * x

    sample_space.new_cells(formula=invalid_in_formula_assignment)
    with pytest.raises(KeyError):
        sample_space.invalid_in_formula_assignment[3]


def test_setitem_in_formula_duplicate_assignment_error(sample_space):

    def duplicate_assignment(x):
        duplicate_assignment[x] = 4 * x
        return 4 * x

    sample_space.new_cells(formula=duplicate_assignment)
    with pytest.raises(ValueError):
        sample_space.duplicate_assignment[4]


