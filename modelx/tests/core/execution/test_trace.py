import os
import pathlib
import modelx as mx
import modelx.tests.testdata

datadir = pathlib.Path(os.path.dirname(mx.tests.testdata.__file__))


def test_extended_dfs_nodes():
    """
    Parent[x]---Child[y]---GrandChild
       |           |           |
       +---foo(t)  +---bar(t)  +---baz(t)
    """
    m = mx.read_model(datadir / "NestedItemSpaces")

    m.Parent[1].foo(1)
    m.Parent[1].Child[1].bar(1)
    m.Parent[1].Child[1].GrandChild.baz(1)

    assert (list(m._impl._extended_dfs_nodes((mx.Model1.Parent._impl, (1,))))
            == [(m.Parent[1].foo._impl, (1,)),
                (m.Parent[1].Child[1].GrandChild.baz._impl, (1,)),
                (m.Parent[1].Child.bar._impl, (1,)),
                (m.Parent[1].Child[1].bar._impl, (1,)),
                (m.Parent[1].Child._impl, (1,)),
                (m.Parent._impl, (1,))])

    m._impl._check_sanity()
    m.close()