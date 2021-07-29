import pytest
import textwrap
import modelx as mx


def test_serialize_allow_none(tmp_path):

    m = mx.new_model()
    A = mx.new_space('A')
    B = A.new_space('B')

    @mx.defcells
    def foo(x):
        return x

    foo.allow_none = True

    B.set_ref("bar", foo, "absolute")
    D = m.new_space('D', bases=B)

    baz = B.new_cells(name="baz", formula=lambda y: 2 * y)

    B.baz.doc = textwrap.dedent(\
    """Baz docment

    this is Baz's docstring
    """)

    baz.allow_none = False

    m.write(tmp_path / "teatprop")

    m2 = mx.read_model(tmp_path / "teatprop")

    assert m2.A.B.foo.allow_none == True
    assert m2.A.B.baz.allow_none == False