from textwrap import dedent
import pytest

import modelx as mx
from modelx.core.errors import NoneReturnedError, FormulaError
from modelx.testing.testutil import ConfigureExecutor

# --------------------------------------------------------------------------
# Test errors


def test_none_returned_error():

    errfunc = dedent(
        """\
        def return_none(x, y):
            return None"""
    )

    m = mx.new_model(name="ErrModel")
    space = m.new_space(name="ErrSpace")
    cells = space.new_cells(formula=errfunc)
    cells.allow_none = False

    with ConfigureExecutor():
        with pytest.raises(NoneReturnedError) as errinfo:
            cells(1, 3)

    errmsg = "ErrModel.ErrSpace.return_none(x=1, y=3)"
    assert errinfo.value.args[0] == errmsg

    with pytest.raises(FormulaError) as errinfo:
        cells(1, 3)

    errmsg = dedent("""\
        Error raised during formula execution
        modelx.core.errors.NoneReturnedError: ErrModel.ErrSpace.return_none(x=1, y=3)
        
        Formula traceback:
        0: ErrModel.ErrSpace.return_none(x=1, y=3)
        
        Formula source:
        def return_none(x, y):
            return None
        """)

    assert errinfo.value.args[0] == errmsg
    m._impl._check_sanity()
    m.close()


def test_zerodiv():

    zerodiv = dedent(
        """\
        def zerodiv(x):
            if x == 3:
                return x / 0
            else:
                return zerodiv(x + 1)"""
    )

    m = mx.new_model()
    space = m.new_space(name="ZeroDiv")
    cells = space.new_cells(formula=zerodiv)

    with ConfigureExecutor():
        with pytest.raises(ZeroDivisionError):
            cells(0)

    m._impl._check_sanity()
    m.close()

# --------------------------------------------------------------------------
# Test graph clean-up upon error

def test_trace_cleanup_value_error():

    @mx.defcells
    def foo(i):
        import datetime
        return foo(i - 1).replace(
            month=foo(i - 1).month + 1) if i > 0 else datetime.date(2016, 1, 1)

    with ConfigureExecutor():
        with pytest.raises(ValueError):
            foo(20)

    assert foo._impl.check_sanity()
    assert len(foo) == 12

    m = foo.model
    m._impl._check_sanity()
    m.close()


def test_trace_cleanup_type_error():

    @mx.defcells
    def foo(i):
        if i > 0:
            return foo(i - 1) + (1 if i < 2 else "error")
        else:
            return 0

    with ConfigureExecutor():
        with pytest.raises(TypeError):
            foo(2)

    assert foo._impl.check_sanity()
    assert len(foo) == 2

    m = foo.model
    m._impl._check_sanity()
    m.close()


