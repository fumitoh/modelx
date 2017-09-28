from modelx.core.api import *


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



