import pathlib
import itertools
import modelx as mx
from modelx.tests.testdata.testpkg import testmod
import pytest

testmodpath = pathlib.Path(testmod.__file__)

params = list(itertools.product(
    ["new_model", "new_space"],
    ["write", "zip", "backup"],
    [testmod, testmodpath, str(testmodpath)]
))


@pytest.mark.parametrize("meth, save_meth, module", params)
def test_new_module(tmp_path, meth, save_meth, module):

    p = getattr(mx, meth)(name="Parent")
    p.new_module(name="Foo", path="Parent/Foo", module=module)
    p.Bar = p.Foo

    assert p.Foo.modbar(2) == 4

    if save_meth == "backup":
        getattr(p.model, save_meth)(tmp_path / "model")

        p.model.close()
        m2 = mx.restore_model(tmp_path / "model")

    else:
        getattr(p.model, save_meth)(tmp_path / "model")
        p.model.close()
        m2 = mx.read_model(tmp_path / "model")

    p2 = m2 if meth == "new_model" else m2.spaces["Parent"]

    assert p.Foo.modbar(2) == 4
    assert p.Bar is p.Foo

    m2.close()