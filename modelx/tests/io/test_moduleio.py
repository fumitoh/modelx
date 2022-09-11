import pathlib
import itertools
import shutil
import modelx as mx
from modelx.tests.testdata.testpkg import testmod
import pytest
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec

SAMPLE_MODULE = pathlib.Path(testmod.__file__)

params = list(itertools.product(
    ["model", "space"],
    ["write", "zip", "backup"],
    [testmod, SAMPLE_MODULE, str(SAMPLE_MODULE)]
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


def load_module(path_):
    loader = SourceFileLoader("<unnamed module>", path=str(path_))
    spec = spec_from_loader(loader.name, loader)
    mod = module_from_spec(spec)
    loader.exec_module(mod)
    return mod


params_update = list(itertools.product(
    ["model", "space"],
    ["write", "zip"],
    ["module", "path-like", "str", None],
))


@pytest.mark.parametrize("parent, save_meth, replace", params_update)
def test_update_module(
        tmp_path, parent, save_meth, replace):

    if parent == "model":
        p = mx.new_model(name="Parent")
    else:
        p = mx.new_model().new_space(name="Parent")

    module1 = tmp_path / SAMPLE_MODULE.name
    module2 = tmp_path / "testmod_updated.py"

    # Copy sample modules in tmp_path
    shutil.copyfile(SAMPLE_MODULE, module1)
    shutil.copyfile(SAMPLE_MODULE.parent / "testmod_updated.py", module2)

    old_module = p.new_module(name="Foo", path="Parent/Foo", module=module1)
    p.Bar = p.Foo

    def assert_original(m_or_s):
        assert m_or_s.Foo.modfibo(10) == 55
        assert m_or_s.Foo.modbar(2) == 4
        assert m_or_s.Foo is m_or_s.Bar

    assert_original(p)

    # Set new_module parameter
    if replace == "module":
        new_module = load_module(module2)
    elif replace == "path-like":
        new_module = module2
    elif replace == "str":
        new_module = str(module2)
    else:
        new_module = None
        shutil.copyfile(module2, module1)

    p.update_module(old_module, new_module=new_module)

    def assert_updated(m_or_s):
        assert m_or_s.Foo.modfibo(10) == 144
        assert m_or_s.Foo.modbar(2) == 6
        assert m_or_s.Foo is m_or_s.Bar

    assert_updated(p)
    getattr(p.model, save_meth)(tmp_path / "model")
    p.model.close()

    m2 = mx.read_model(tmp_path / "model")
    p2 = m2 if parent == "model" else m2.spaces["Parent"]

    assert_updated(p2)

    m2._impl.system._check_sanity(check_members=False)
    m2._impl._check_sanity()

    # Check saving again
    # https://github.com/fumitoh/modelx/issues/45
    getattr(p2.model, save_meth)(tmp_path / "model")
    m2.close()

    m3 = mx.read_model(tmp_path / "model")
    m3._impl.system._check_sanity(check_members=False)
    m3._impl._check_sanity()

    p3 = m3 if parent == "model" else m3.spaces["Parent"]

    assert_updated(p3)
    m3.close()


params_update_path = list(itertools.product(
    ["model", "space"],
    ["write", "zip"]
))

@pytest.mark.parametrize("parent, save_meth", params_update_path)
def test_update_path(tmp_path, parent, save_meth):

    if parent == "model":
        p = mx.new_model(name="Parent")
    else:
        p = mx.new_model().new_space(name="Parent")

    module1 = tmp_path / SAMPLE_MODULE.name

    # Copy sample modules in tmp_path
    shutil.copyfile(SAMPLE_MODULE, module1)

    module_ = p.new_module(name="Foo", path="Parent/Foo", module=module1)
    p.Bar = p.Foo

    def assert_module(m_or_s):
        assert m_or_s.Foo.modfibo(10) == 55
        assert m_or_s.Foo.modbar(2) == 4
        assert m_or_s.Foo is m_or_s.Bar

    assert_module(p)

    p.model.get_spec(module_).path = "Parent/Foo1"

    def assert_path(m_or_s, module_, nth):
        assert m_or_s.model.get_spec(module_).path == pathlib.Path("Parent/Foo%s" % nth)
        assert m_or_s.model.iospecs[0].path == pathlib.Path("Parent/Foo%s" % nth)
        assert_module(m_or_s)

    assert_path(p, module_, "1")

    getattr(p.model, save_meth)(tmp_path / "model")
    p.model.close()

    m2 = mx.read_model(tmp_path / "model")
    p2 = m2 if parent == "model" else m2.spaces["Parent"]

    assert_path(p2, p2.Foo, "1")

    m2.get_spec(p2.Foo).path = "Parent/Foo2"
    assert_path(p2, p2.Foo, "2")

    m2._impl.system._check_sanity(check_members=False)
    m2._impl._check_sanity()

    # Check saving again
    # https://github.com/fumitoh/modelx/issues/45
    getattr(p2.model, save_meth)(tmp_path / "model")
    m2.close()

    m3 = mx.read_model(tmp_path / "model")
    m3._impl.system._check_sanity(check_members=False)
    m3._impl._check_sanity()

    p3 = m3 if parent == "model" else m3.spaces["Parent"]
    assert_path(p3, p3.Foo, "2")
    m3.get_spec(p3.Foo).path = "Parent/Foo3"
    assert_path(p3, p3.Foo, "3")

    m3.close()
