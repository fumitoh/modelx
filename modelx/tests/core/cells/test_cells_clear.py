import modelx as mx
from textwrap import dedent
import pytest

@pytest.fixture
def clearsample():

    m, s = mx.new_model(), mx.new_space()

    @mx.defcells
    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo(x - 1) + fibo[x - 2]

    @mx.defcells
    def no_param():
        return 5

    yield s
    m._impl._check_sanity()
    m.close()


def test_clear_at_arg(clearsample):
    clearsample.fibo[5]

    clearsample.fibo.clear_at(3)
    assert set(clearsample.fibo) == {0, 1, 2}


def test_clear_at_kwarg(clearsample):
    clearsample.fibo[5]

    clearsample.fibo.clear_at(x=3)
    assert set(clearsample.fibo) == {0, 1, 2}


@pytest.mark.parametrize(
    ["method", "input", "expected"],
    [["clear", False, set()],
     ["clear", True, {0, 1}],
     ["clear_all", False, set()],
     ["clear_all", True, set()]])
def test_clear_with_param(clearsample, method, input, expected):

    if input:
        clearsample.fibo[0] = 0
        clearsample.fibo[1] = 1
        assert clearsample.fibo.is_input(0)
        assert clearsample.fibo.is_input(1)

    clearsample.fibo[5]

    assert set(clearsample.fibo) == {0, 1, 2, 3, 4, 5}
    getattr(clearsample.fibo, method)()
    assert set(clearsample.fibo) == expected


@pytest.mark.parametrize(
    ["method", "input", "expected"],
    [["clear_at", False, set()],
     ["clear_at", True, set()],
     ["clear", False, set()],
     ["clear", True, {()}],
     ["clear_all", False, set()],
     ["clear_all", True, set()]])
def test_clear_no_param(clearsample, method, input, expected):

    if input:
        clearsample.no_param = 5
        assert clearsample.no_param.is_input()
    assert clearsample.no_param() == 5
    getattr(clearsample.no_param, method)()
    assert set(clearsample.no_param) == expected


def test_clear_other(clearsample):

    space = clearsample

    f1 = dedent(
        """\
        def source(x):
            if x == 1:
                return 1
            else:
                return source(x - 1) + 1"""
    )

    f2 = dedent(
        """\
        def dependant(x):
            return 2 * source(x)"""
    )

    space.new_cells(formula=f1)
    space.new_cells(formula=f2)

    space.dependant(2)
    assert set(space.dependant) == {2}
    assert set(space.source) == {1, 2}

    space.source.clear_at(1)
    assert set(space.source) == set()
    assert set(space.dependant) == set()

