from itertools import chain
import pytest
import modelx as mx

foo = lambda n: foo(n - 1) if n > 1 else n


@pytest.fixture(scope="module")
def testspace():
    m = mx.new_model(name="TestTraceModel")
    yield m.new_space(
        name="TestTraceSpace",
        formula=lambda i: None
    )
    m._impl._check_sanity()
    m.close()


@pytest.fixture(scope="module")
def testcells(testspace):
    c = testspace.new_cells(
        name="foo",
        formula=foo
    )
    mx.start_stacktrace()
    c[10]
    yield c
    c.clear()
    mx.stop_stacktrace()


@pytest.mark.parametrize(
    "count, position",
    list(enumerate(chain(range(0, 10), range(9, -1, -1)))))
def test_get_stacktrace(testcells, count, position):

    trace = mx.get_stacktrace()
    assert trace[count][0] == "ENTER" if count < 10 else "EXIT"
    assert trace[count][1] == position
    assert trace[count][3] == testcells._get_repr(
        fullname=True,
        add_params=True
    )
    assert trace[count][4] == (10 - position,)


def test_clear_stacktrace(testcells):

    assert mx.get_stacktrace()
    mx.clear_stacktrace()
    assert not mx.get_stacktrace()  # Empty list


