from itertools import chain
import pytest
import modelx as mx


def foo():
    import time
    time.sleep(0.1)
    return bar(3)


def bar(x):
    return bar(x-1) + 1 if x > 0 else 0


@pytest.fixture(scope="module")
def testspace():
    m = mx.new_model(name="TestTraceSummary")
    yield m.new_space(
        name="TestTraceSpace",
        formula=lambda i: None
    )
    m._impl._check_sanity()
    m.close()


@pytest.fixture(scope="module")
def testcells(testspace):
    c = testspace.new_cells(formula=foo)
    testspace.new_cells(formula=bar)
    mx.start_stacktrace()
    c()
    yield c
    c.clear()
    mx.stop_stacktrace()


def test_summary(testcells):

    trace = mx.get_stacktrace()
    summary = mx.get_stacktrace(True)

    foo = 'TestTraceSummary.TestTraceSpace.foo()'
    bar = 'TestTraceSummary.TestTraceSpace.bar(x)'

    assert summary[foo]['calls'] == 1
    assert summary[foo]['first_entry_at'] == trace[0][2]
    assert summary[foo]['last_exit_at'] == trace[-1][2]

    assert summary[foo]['duration'] == (
        trace[1][2] - trace[0][2] +
        trace[-1][2] - trace[-2][2]
    )
    assert summary[foo]['calls']
    assert summary[foo]['calls']

    assert summary[bar]['calls'] == 4
    assert summary[bar]['first_entry_at'] == trace[1][2]
    assert summary[bar]['last_exit_at'] == trace[-2][2]

    assert summary[bar]['duration'] == (
        trace[-2][2] - trace[1][2]
    )



