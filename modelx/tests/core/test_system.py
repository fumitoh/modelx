from textwrap import dedent
from modelx.core.api import *
from modelx.core.errors import DeepReferenceError
import pytest


def test_defcells_withname():

    create_model().create_space()

    @defcells(name="bar")
    def foo(x):
        if x == 0:
            return 123
        else:
            return bar(x - 1)

    assert foo[10] == 123


def test_defcells_withspace():

    @defcells(space=get_currentspace())
    def foo(x):
        if x == 0:
            return 123
        else:
            return foo(x - 1)

    assert foo[10] == 123


def test_defcells_lambda_object():

    fibo = defcells(space=get_currentspace(), name='fibo')(
        lambda x: x if x == 0 or x == 1 else fibo[x - 1] + fibo[x - 2])

    assert fibo(10) == 55


def test_decells_lambda_source():

    src = "lambda x: x if x == 0 or x == 1 else fibo2[x - 1] + fibo2[x - 2]"
    fibo2 = get_currentspace().create_cells(name='fibo2', func=src)

    assert fibo2(10) == 55


def test_deep_reference_error():

    from modelx.core import system
    last_max_depth = system.callstack.max_depth
    system.callstack.max_depth = 3

    errfunc = dedent("""\
    def erronerous(x, y):
        return erronerous(x + 1, y - 1)""")

    space = create_model(name='ErrModel').create_space(name='ErrSpace')
    cells = space.create_cells(func=errfunc)
    with pytest.raises(DeepReferenceError) as errinfo:
        cells(1, 3)

    errmsg = dedent("""
    Formula chain exceeded the 3 limit.
    Call stack traceback:
    0: ErrModel.ErrSpace.erronerous(x=1, y=3)
    1: ErrModel.ErrSpace.erronerous(x=2, y=2)
    2: ErrModel.ErrSpace.erronerous(x=3, y=1)
    3: ErrModel.ErrSpace.erronerous(x=4, y=0)
    """)

    system.callstack.max_depth = last_max_depth
    assert errinfo.value.args[0] == errmsg