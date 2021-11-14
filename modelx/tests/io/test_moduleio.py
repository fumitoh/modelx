import pathlib
import itertools
import modelx as mx
from modelx.tests.testdata.testpkg import testmod
import pytest

testmodpath = pathlib.Path(testmod.__file__)

params = list(itertools.product(
    ["model", "space"],
    ["write", "zip", "backup"],
    [testmod, testmodpath, str(testmodpath)]
))


@pytest.mark.parametrize("parent, save_meth, module", params)
def test_new_module(tmp_path, parent, save_meth, module):

    if parent == "model":
        p = mx.new_model(name="Parent")
    else:
        p = mx.new_model().new_space(name="Parent")

    p.new_module(name="Foo", path="Parent/Foo", module=module)
    p.Bar = p.Foo

    assert p.Foo.modbar(2) == 4

    getattr(p.model, save_meth)(tmp_path / "model")
    p.model.close()

    if save_meth == "backup":
        m2 = mx.restore_model(tmp_path / "model")
    else:
        m2 = mx.read_model(tmp_path / "model")

    p2 = m2 if parent == "model" else m2.spaces["Parent"]

    assert p2.Foo.modbar(2) == 4
    assert p2.Bar is p2.Foo

    m2._impl.system._check_sanity(check_members=False)
    m2._impl._check_sanity()

    # Check saving again
    # https://github.com/fumitoh/modelx/issues/45
    getattr(p2.model, save_meth)(tmp_path / "model")
    m2.close()

    if save_meth == "backup":
        m3 = mx.restore_model(tmp_path / "model")
    else:
        m3 = mx.read_model(tmp_path / "model")

    m3._impl.system._check_sanity(check_members=False)
    m3._impl._check_sanity()

    p3 = m3 if parent == "model" else m3.spaces["Parent"]
    assert p3.Foo.modbar(2) == 4
    assert p3.Bar is p3.Foo

    m3.close()