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


@pytest.mark.parametrize("space_name", ['Base', 'Sub'])
def test_is_cached(cache_sample, tmp_path, space_name):  # cache_sample fixture in conftest

    m = cache_sample
    getattr(m, space_name).foo.is_cached = False
    m.write(tmp_path / "cash_sample")

    m = mx.read_model(tmp_path / "cash_sample", name="cache_sample_read_%s" % space_name)

    assert m.Sub.foo.is_cached == False


