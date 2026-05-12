import json
import pytest
import modelx as mx


def _close_all_models():
    for model in list(mx.get_models().values()):
        model.close()


@pytest.fixture(autouse=True)
def isolate_models():
    _close_all_models()
    yield
    _close_all_models()


def test_macro_roundtrip_funcdef(tmp_path):
    m = mx.new_model("MacroRT")

    @mx.defmacro
    def get_name():
        return mx_model._name

    @mx.defmacro
    def add(a, b):
        return a + b

    mx.write_model(m, tmp_path / "model")
    _close_all_models()

    m2 = mx.read_model(tmp_path / "model")
    assert set(m2.macros) == {"get_name", "add"}
    assert m2.get_name() == "MacroRT"
    assert m2.add(2, 3) == 5


def test_macro_roundtrip_lambda(tmp_path):
    m = mx.new_model("LambdaRT")
    m.new_macro("dbl", lambda x: x * 2)

    mx.write_model(m, tmp_path / "model")
    _close_all_models()

    m2 = mx.read_model(tmp_path / "model")
    assert "dbl" in m2.macros
    assert m2.dbl(5) == 10


def test_macro_calling_another_macro(tmp_path):
    m = mx.new_model("Chain")

    @mx.defmacro
    def base():
        return 21

    @mx.defmacro
    def double_base():
        return base() * 2

    mx.write_model(m, tmp_path / "model")
    _close_all_models()

    m2 = mx.read_model(tmp_path / "model")
    assert m2.double_base() == 42


def test_macro_accesses_mx_model_and_model_name(tmp_path):
    m = mx.new_model("AccessTest")

    @mx.defmacro
    def via_mx_model():
        return mx_model._name

    @mx.defmacro
    def via_model_name():
        return AccessTest._name

    mx.write_model(m, tmp_path / "model")
    _close_all_models()

    m2 = mx.read_model(tmp_path / "model")
    assert m2.via_mx_model() == "AccessTest"
    assert m2.via_model_name() == "AccessTest"


def test_macro_params_and_kwargs(tmp_path):
    m = mx.new_model("ParamsRT")

    @mx.defmacro
    def greet(name, greeting="Hello"):
        return f"{greeting}, {name}!"

    mx.write_model(m, tmp_path / "model")
    _close_all_models()

    m2 = mx.read_model(tmp_path / "model")
    assert m2.greet("World") == "Hello, World!"
    assert m2.greet("World", greeting="Hi") == "Hi, World!"


def test_macro_renamed_via_defmacro_name(tmp_path):
    # @defmacro(name='custom') decorating def original should serialize
    # under the registered name, not the original function name.
    m = mx.new_model("RenameRT")

    @mx.defmacro(model=m, name="custom_name")
    def original_name():
        return mx_model._name

    mx.write_model(m, tmp_path / "model")
    _close_all_models()

    m2 = mx.read_model(tmp_path / "model")
    assert "custom_name" in m2.macros
    assert "original_name" not in m2.macros
    assert m2.custom_name() == "RenameRT"


def test_mixed_macros_cells_refs_spaces(tmp_path):
    m = mx.new_model("Mixed")
    s = m.new_space("S")

    @mx.defcells
    def foo(x):
        return x * 10

    m.scalar = 7

    @mx.defmacro
    def use_space():
        return mx_model.S.foo(3)

    @mx.defmacro
    def use_ref():
        return mx_model.scalar + 1

    mx.write_model(m, tmp_path / "model")
    _close_all_models()

    m2 = mx.read_model(tmp_path / "model")
    assert m2.S.foo(3) == 30
    assert m2.scalar == 7
    assert m2.use_space() == 30
    assert m2.use_ref() == 8


def test_no_macros_no_file_emitted(tmp_path):
    m = mx.new_model("NoMacros")
    m.new_space("S")

    mx.write_model(m, tmp_path / "model")
    assert not (tmp_path / "model" / "_macros.py").exists()

    _close_all_models()
    m2 = mx.read_model(tmp_path / "model")
    assert len(m2.macros) == 0


def test_macros_file_contains_pseudo_python_header(tmp_path):
    m = mx.new_model("HeaderCheck")

    @mx.defmacro
    def f():
        return 1

    mx.write_model(m, tmp_path / "model")
    content = (tmp_path / "model" / "_macros.py").read_text()
    assert "# modelx: pseudo-python" in content
    assert "def f():" in content


def test_serializer_version_unchanged(tmp_path):
    m = mx.new_model("Vcheck")

    @mx.defmacro
    def f():
        return 1

    mx.write_model(m, tmp_path / "model")
    meta = json.loads((tmp_path / "model" / "_system.json").read_text())
    assert meta["serializer_version"] == 7


def test_macro_zip_roundtrip(tmp_path):
    m = mx.new_model("ZipRT")

    @mx.defmacro
    def f():
        return "zipped"

    mx.write_model(m, tmp_path / "model.zip")
    _close_all_models()

    m2 = mx.read_model(tmp_path / "model.zip")
    assert m2.f() == "zipped"
