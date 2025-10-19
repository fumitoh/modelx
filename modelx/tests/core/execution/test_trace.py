import os
import pathlib
import modelx as mx
import modelx.tests.testdata

datadir = pathlib.Path(os.path.dirname(mx.tests.testdata.__file__))


def test_deleting_nested_itemspaces():
    """
    Parent[x]---Child[y]---GrandChild
       |           |           |
       +---foo(t)  +---bar(t)  +---baz(t)
    """
    from modelx.core.base import null_impl
    m = mx.read_model(datadir / "NestedItemSpaces")

    m.Parent[1].foo(1)
    m.Parent[1].Child[1].bar(1)
    m.Parent[1].Child[1].GrandChild.baz(1)

    foo = m.Parent[1].foo
    bar = m.Parent[1].Child[1].bar
    baz = m.Parent[1].Child[1].GrandChild.baz

    m.clear_all()

    assert foo._impl is null_impl
    assert bar._impl is null_impl
    assert baz._impl is null_impl

    m._impl._check_sanity()
    m.close()