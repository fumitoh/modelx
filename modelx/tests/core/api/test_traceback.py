import types

import modelx as mx
from modelx.core.errors import (
    FormulaError,
    DeepReferenceError,
    NoneReturnedError)
import pytest
from textwrap import dedent


@pytest.fixture(scope="module")
def errormodel():

    m = mx.new_model("ErrorModel")
    s = m.new_space("ErrorSpace")

    @mx.defcells
    def foo(x):
        a, b = 1, 'b'
        if x > 0:
            return foo(x-1) + 1
        else:
            raise ValueError

    @mx.defcells
    def bar(x):
        if x > 0:
            return bar(x-1)
        else:
            return None

    @mx.defcells
    def infinite(x):
        return infinite(x-1)

    @mx.defcells
    def listcomp(t):
        if t > 0:
            return sum([listcomp(t - i) for i in range(1, 2)])
        else:
            raise ValueError()

    s.new_cells("lam", formula=lambda x: qux(x-1) if x > 0 else 1/0)

    @mx.defcells
    def qux(x):
        return lam(x)

    @mx.defcells
    def quux(t):
        def my_sum(*args):
            return sum(args)
        return my_sum('a')

    yield m
    m._impl._check_sanity()
    m.close()


@pytest.fixture(params=[True, False])
def formula_error_handle_state(request):
    saved_formula_error_handle_state = mx.handle_formula_error()
    mx.handle_formula_error(request.param)
    yield mx.handle_formula_error()
    mx.handle_formula_error(saved_formula_error_handle_state)


def test_value_error(errormodel, formula_error_handle_state, capsys):

    cells = errormodel.ErrorSpace.foo
    errmsg = dedent("""\
        Error raised during formula execution
        ValueError
        
        Formula traceback:
        0: ErrorModel.ErrorSpace.foo(x=1), line 4
        1: ErrorModel.ErrorSpace.foo(x=0), line 6
        
        Formula source:
        def foo(x):
            a, b = 1, 'b'
            if x > 0:
                return foo(x-1) + 1
            else:
                raise ValueError
        """)

    if formula_error_handle_state:
        cells(1)
        assert capsys.readouterr().err == errmsg + '\n'
    else:
        with pytest.raises(FormulaError) as errinfo:
            cells(1)
        assert errinfo.value.args[0] == errmsg
    assert isinstance(mx.get_error(), ValueError)

    assert mx.get_traceback() == [
        (cells.node(1), 4),
        (cells.node(0), 6)]

    assert mx.get_traceback(show_locals=True) == [
        (cells.node(1), 4, {'x':1, 'a':1, 'b':'b'}),
        (cells.node(0), 6, {'x':0, 'a':1, 'b':'b'})]

    assert mx.trace_locals() == {'x':0, 'a':1, 'b':'b'}
    assert mx.trace_locals(0) == {'x':1, 'a':1, 'b':'b'}


def test_none_returned_error(errormodel, formula_error_handle_state, capsys):

    cells = errormodel.ErrorSpace.bar
    errmsg = dedent("""\
        Error raised during formula execution
        modelx.core.errors.NoneReturnedError: ErrorModel.ErrorSpace.bar(x=0)
        
        Formula traceback:
        0: ErrorModel.ErrorSpace.bar(x=1), line 3
        1: ErrorModel.ErrorSpace.bar(x=0)
        
        Formula source:
        def bar(x):
            if x > 0:
                return bar(x-1)
            else:
                return None
        """)
    if formula_error_handle_state:
        cells(1)
        assert capsys.readouterr().err == errmsg + '\n'
    else:
        with pytest.raises(FormulaError) as errinfo:
            cells(1)
        assert errinfo.value.args[0] == errmsg

    assert isinstance(mx.get_error(), NoneReturnedError)
    assert mx.get_traceback(show_locals=True) == [
        (cells.node(1), 3, {'x':1}),
        (cells.node(0), 0, None)]
    assert mx.get_traceback() == [
        (cells.node(1), 3),
        (cells.node(0), 0)]


def test_deep_reference_error(errormodel, formula_error_handle_state, capsys):

    cells = errormodel.ErrorSpace.infinite
    saved = mx.get_recursion()
    errmsg = dedent("""\
        Error raised during formula execution
        modelx.core.errors.DeepReferenceError: Formula chain exceeded the 3 limit
        
        Formula traceback:
        0: ErrorModel.ErrorSpace.infinite(x=3), line 2
        1: ErrorModel.ErrorSpace.infinite(x=2), line 2
        2: ErrorModel.ErrorSpace.infinite(x=1), line 2
        3: ErrorModel.ErrorSpace.infinite(x=0), line 2
        
        Formula source:
        def infinite(x):
            return infinite(x-1)
        """)
    if formula_error_handle_state:
        try:
            mx.set_recursion(3)
            cells(3)
        finally:
            mx.set_recursion(saved)
        assert capsys.readouterr().err == errmsg + '\n'
    else:
        try:
            mx.set_recursion(3)
            with pytest.raises(FormulaError) as errinfo:
                cells(3)
        finally:
            mx.set_recursion(saved)
        assert errinfo.value.args[0] == errmsg

    assert isinstance(mx.get_error(), DeepReferenceError)
    assert mx.get_traceback(show_locals=True) == [
        (cells.node(3), 2, {'x': 3}),
        (cells.node(2), 2, {'x': 2}),
        (cells.node(1), 2, {'x': 1}),
        (cells.node(0), 2, {'x': 0})]
    assert mx.get_traceback() == [
        (cells.node(3), 2),
        (cells.node(2), 2),
        (cells.node(1), 2),
        (cells.node(0), 2)]


def test_listcomp_error(errormodel, formula_error_handle_state, capsys):

    # https://github.com/fumitoh/modelx/issues/31

    cells = errormodel.ErrorSpace.listcomp
    errmsg = dedent("""\
        Error raised during formula execution
        ValueError
        
        Formula traceback:
        0: ErrorModel.ErrorSpace.listcomp(t=1), line 3
        1: ErrorModel.ErrorSpace.listcomp(t=0), line 5
        
        Formula source:
        def listcomp(t):
            if t > 0:
                return sum([listcomp(t - i) for i in range(1, 2)])
            else:
                raise ValueError()
        """)
    if formula_error_handle_state:
        cells(1)
        assert capsys.readouterr().err == errmsg + '\n'
    else:
        with pytest.raises(FormulaError) as errinfo:
            cells(1)
        assert errinfo.value.args[0] == errmsg
    assert isinstance(mx.get_error(), ValueError)
    assert mx.get_traceback(show_locals=True) == [
        (cells.node(1), 3, {'t': 1}),
        (cells.node(0), 5, {'t': 0})]
    assert mx.get_traceback() == [
        (cells.node(1), 3),
        (cells.node(0), 5)]

def test_lambda_error(errormodel, formula_error_handle_state, capsys):

    cells = errormodel.ErrorSpace.lam
    qux = errormodel.ErrorSpace.qux
    errmsg = dedent("""\
        Error raised during formula execution
        ZeroDivisionError: division by zero
        
        Formula traceback:
        0: ErrorModel.ErrorSpace.lam(x=1), line 1
        1: ErrorModel.ErrorSpace.qux(x=0), line 2
        2: ErrorModel.ErrorSpace.lam(x=0), line 1
        
        Formula source:
        lambda x: qux(x-1) if x > 0 else 1/0""")

    if formula_error_handle_state:
        cells(1)
        assert capsys.readouterr().err == errmsg + '\n'
    else:
        with pytest.raises(FormulaError) as errinfo:
            cells(1)
        assert errinfo.value.args[0] == errmsg

    assert isinstance(mx.get_error(), ZeroDivisionError)
    assert mx.get_traceback(show_locals=True) == [
        (cells.node(1), 1, {'x': 1}),
        (qux.node(0), 2, {'x': 0}),
        (cells.node(0), 1, {'x': 0})]
    assert mx.get_traceback() == [
        (cells.node(1), 1),
        (qux.node(0), 2),
        (cells.node(0), 1)]


def test_nested_def_error(errormodel, formula_error_handle_state, capsys):

    cells = errormodel.ErrorSpace.quux
    errmsg = dedent("""\
    Error raised during formula execution
    TypeError: unsupported operand type(s) for +: 'int' and 'str'
    
    Formula traceback:
    0: ErrorModel.ErrorSpace.quux(t=1), line 4
    
    Formula source:
    def quux(t):
        def my_sum(*args):
            return sum(args)
        return my_sum('a')
    """)
    if formula_error_handle_state:
        cells(1)
        assert capsys.readouterr().err == errmsg + '\n'
    else:
        with pytest.raises(FormulaError) as errinfo:
            cells(1)
        assert errinfo.value.args[0] == errmsg
    assert isinstance(mx.get_error(), TypeError)
    assert mx.get_traceback(True)[0][:-1] == (cells.node(1), 4)
    assert mx.get_traceback(True)[0][-1]['t'] == 1
    assert isinstance(mx.get_traceback(True)[0][-1]['my_sum'], types.FunctionType)
