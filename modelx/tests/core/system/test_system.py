import sys
import modelx as mx
from textwrap import dedent
from modelx.core.system import mxsys
from modelx.core.api import *
from modelx.testing.testutil import SuppressFormulaError
from modelx.core.errors import DeepReferenceError
import pytest


def test_executer_type():
    if sys.version_info < (3, 11) and sys.platform == "win32":
        assert isinstance(mxsys.executor, mx.core.system.ThreadedExecutor)
    else:
        assert isinstance(mxsys.executor, mx.core.system.NonThreadedExecutor)

@pytest.fixture
def testmodel():
    m, s = new_model("ModelA"), new_space("SpaceA")
    yield m
    m._impl._check_sanity()
    m.close()

def test_get_object_from_tuple(testmodel):
    testmodel.SpaceA.formula = lambda x: None
    s = mxsys.get_object_from_idtuple(("ModelA", "SpaceA", (1,)))
    assert s is testmodel.SpaceA[1]


def test_defcells_withname(testmodel):
    @defcells(name="bar")
    def foo(x):
        if x == 0:
            return 123
        else:
            return bar(x - 1)

    assert foo[10] == 123


def test_defcells_withspace(testmodel):
    @defcells(space=cur_space())
    def foo(x):
        if x == 0:
            return 123
        else:
            return foo(x - 1)

    assert foo[10] == 123


def test_defcells_lambda_object(testmodel):

    fibo = defcells(space=cur_space(), name="fibo")(
        lambda x: x if x == 0 or x == 1 else fibo(x - 1) + fibo(x - 2)
    )

    assert fibo(10) == 55


def test_decells_lambda_source(testmodel):

    src = "lambda x: x if x == 0 or x == 1 else fibo2(x - 1) + fibo2(x - 2)"
    fibo2 = cur_space().new_cells(name="fibo2", formula=src)

    assert fibo2(10) == 55


def test_deep_reference_error():

    from modelx.core import mxsys

    last_maxdepth = mxsys.callstack.maxdepth

    try:
        set_recursion(3)

        errfunc = dedent(
            """\
        def erronerous(x, y):
            return erronerous(x + 1, y - 1)"""
        )

        space = new_model(name="ErrModel").new_space(name="ErrSpace")
        cells = space.new_cells(formula=errfunc)

        with SuppressFormulaError():
            with pytest.raises(DeepReferenceError) as errinfo:
                cells(1, 3)

        assert errinfo.value.args[0] == "Formula chain exceeded the 3 limit"

        with pytest.raises(mx.core.system.FormulaError) as errinfo:
            cells(1, 3)

        errmsg = dedent(
            """\
            Error raised during formula execution
            modelx.core.errors.DeepReferenceError: Formula chain exceeded the 3 limit
            
            Formula traceback:
            0: ErrModel.ErrSpace.erronerous(x=1, y=3), line 2
            1: ErrModel.ErrSpace.erronerous(x=2, y=2), line 2
            2: ErrModel.ErrSpace.erronerous(x=3, y=1), line 2
            3: ErrModel.ErrSpace.erronerous(x=4, y=0), line 2
            
            Formula source:
            def erronerous(x, y):
                return erronerous(x + 1, y - 1)
            """
        )
    finally:
        set_recursion(last_maxdepth)
    assert errinfo.value.args[0] == errmsg


def test_configure_python():
    configure_python()
    assert sys.getrecursionlimit() == 10**6


def test_restore_python():

    restore_python()

    assert sys.getrecursionlimit() == 1000
    assert not hasattr(sys, "tracebacklimit")

    configure_python()


def test_rename_same_name():

    m1 = new_model("dupname")
    with pytest.warns(UserWarning):
        m2 = new_model("dupname")

    assert "dupname_BAK" in m1.name
    assert m1.name in get_models()



