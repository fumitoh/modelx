import modelx as mx
import pathlib


def test_model_path(tmp_path):

    m = mx.new_model()
    s = m.new_space("Space1")

    @mx.defcells(space=s)
    def foo():
        return _model.path

    m.path = "."
    assert foo() == pathlib.Path(".")

    m.path = ".."
    assert foo() == pathlib.Path("..")

    m.write(tmp_path / "model")
    assert foo() == tmp_path / "model"

    m.path = "."
    assert foo() == pathlib.Path(".")

    m.close()
    m = mx.read_model(tmp_path / "model")
    assert m.Space1.foo() == tmp_path / "model"

    ref = m.Space1.foo.precedents()[0]
    assert ref.obj.name == "path"
    assert ref.obj.value == tmp_path / "model"



