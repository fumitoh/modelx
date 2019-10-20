from textwrap import dedent
import pytest

from modelx import *
from modelx.core.errors import NoneReturnedError


def test_parent(sample_space):
    assert sample_space.func1.parent == sample_space


def test_defcells_funcs(sample_space):
    assert sample_space.func1[2] == 10 and sample_space.func2[2] == 12


def test_init_from_str(sample_space):
    assert sample_space.func[2] == 4


def test_getitem(sample_space):
    assert sample_space.fibo[10] == 55


def test_call(sample_space):
    assert sample_space.fibo(10) == 55


@pytest.mark.parametrize(
    "args, masked, value",
    [
        ((1, 2, 3), (1, 2, 3), 123),
        ((1, 2, 4), (1, 2, None), 120),
        ((1, 3, 3), (1, None, 3), 103),
        ((2, 2, 3), (None, 2, 3), 23),
        ((1, 3, 4), (1, None, None), 100),
        ((2, 2, 4), (None, 2, None), 20),
        ((2, 3, 3), (None, None, 3), 3),
        ((2, 3, 4), (None, None, None), 0),
    ],
)
def test_match(sample_space, args, masked, value):

    cells = sample_space.matchtest
    retargs, retvalue = cells.match(*args)

    assert retargs == masked and retvalue == value


def test_clear_formula(sample_space):

    space = sample_space
    f1 = dedent(
        """\
        def clear_source(x):
            if x == 1:
                return 1
            else:
                return clear_source(x - 1) + 1"""
    )

    f2 = dedent(
        """\
        def clear_dependant(x):
            return 2 * clear_source(x)"""
    )

    source = space.new_cells(formula=f1)
    dependant = space.new_cells(formula=f2)

    dependant(2)
    assert set(dependant) == {2}
    assert set(source) == {1, 2}

    del source.formula
    assert set(source) == set()
    assert set(dependant) == set()


def test_set_formula(sample_space):

    space = sample_space
    f1 = dedent(
        """\
        def clear_source(x):
            if x == 1:
                return 1
            else:
                return clear_source(x - 1) + 1"""
    )

    f2 = dedent(
        """\
        def clear_dependant(x):
            return 2 * clear_source(x)"""
    )

    f3 = dedent(
        """\
        def replace_source(x):
            if x == 1:
                return 2
            else:
                return clear_source(x - 1) + 1"""
    )

    source = space.new_cells(formula=f1)
    dependant = space.new_cells(formula=f2)

    result = dependant(2)
    assert set(dependant) == {2}
    assert set(source) == {1, 2}
    assert result == 4

    source.formula = f3
    result = dependant(2)
    assert set(source) == {1, 2}
    assert set(dependant) == {2}
    assert result == 6


def test_parameters(sample_space):

    space = sample_space
    assert space.fibo.parameters == ("x",)
    assert space.no_param.parameters == ()
    assert space.matchtest.parameters == ("x", "y", "z")


# --------------------------------------------------------------------------
# Test fullname


def test_fullname(sample_space):
    assert (
        sample_space.fibo.fullname
        == "samplemodel.samplespace.fibo"
    )


def test_fullname_omit_model(sample_space):
    assert (
        sample_space.fibo._impl.get_fullname(omit_model=True)
        == "samplespace.fibo"
    )


# --------------------------------------------------------------------------
# Test errors


def test_none_returned_error():

    errfunc = dedent(
        """\
        def return_none(x, y):
            return None"""
    )

    space = new_model(name="ErrModel").new_space(name="ErrSpace")
    cells = space.new_cells(formula=errfunc)
    cells.allow_none = False
    with pytest.raises(NoneReturnedError) as errinfo:
        cells(1, 3)

    errmsg = dedent(
        """\
        None returned from ErrModel.ErrSpace.return_none(x=1, y=3).
        Call stack traceback:
        0: ErrModel.ErrSpace.return_none(x=1, y=3)"""
    )

    assert errinfo.value.args[0] == errmsg


def test_zerodiv():

    from modelx.core.errors import RewindStackError

    zerodiv = dedent(
        """\
        def zerodiv(x):
            if x == 3:
                return x / 0
            else:
                return zerodiv(x + 1)"""
    )

    space = new_model().new_space(name="ZeroDiv")
    cells = space.new_cells(formula=zerodiv)

    with pytest.raises(RewindStackError):
        cells(0)
