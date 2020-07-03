import modelx as mx
import pytest
import itertools
from modelx.serialize import ziputil

sample_log = """\
Space1.Space1.foo(x=0)=Empty DataFrame
Columns: []
Index: []
Space1.Space1.foo(x=2)=1
Space1.Space1[3].foo(x=3)=1"""


@pytest.mark.parametrize(
    "func_or_meth, write_or_zip",
    itertools.product(
        ["func", "meth"],
        ["write", "zip"]
    )
)
def test_log_input(tmp_path, func_or_meth, write_or_zip):

    import pandas as pd

    m, s = mx.new_model(), mx.new_space()
    ns = s.new_space()

    @mx.defcells
    def foo(x):
        return x

    foo[0] = pd.DataFrame()
    foo[2] = 1

    ns.parameters = ("x",)

    ns[3].foo[3] = 1

    if func_or_meth == "func":
        getattr(mx, write_or_zip + "_model")(
            m, tmp_path / "model", log_input=True)
    else:
        getattr(m, write_or_zip)(tmp_path / "model", log_input=True)

    s = ziputil.read_str(tmp_path / "model/_input_log.txt")

    assert s == sample_log


