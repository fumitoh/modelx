import sys
from inspect import getsource
from textwrap import dedent


def test_cacheless_cells(cache_sample, tmp_path):  # fixture defined in conftest

    output = dedent("""\
    def foo(self, other, x):
        return other(x)
    """)

    m = cache_sample
    m.Base.foo.is_cached = False
    m.export(tmp_path / "cache_sample_nomx")
    try:
        sys.path.insert(0, str(tmp_path))
        from cache_sample_nomx import mx_model as nomx
        assert nomx.Base.baz(2) == 4
        assert nomx.Sub.baz(2) == 4
        assert dedent(getsource(nomx.Base.foo)) == output
        assert dedent(getsource(nomx.Sub.foo)) == output
    finally:
        sys.path.pop(0)


