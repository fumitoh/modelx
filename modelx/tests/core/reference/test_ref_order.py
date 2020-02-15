import modelx as mx
import pytest


def test_duplicate_model_ref():
    m, s = mx.new_model(), mx.new_space()
    m.x = "model x"
    assert s.x == "model x"
    s.x = "space x"
    assert s.x == "space x"
    del s.x
    assert s.x == "model x"
    del m.x
    with pytest.raises(AttributeError):
        s.x


def test_duplicate_space_ref():
    m, s = mx.new_model(), mx.new_space()
    s.x = "space x"
    assert s.x == "space x"
    m.x = "model x"
    assert s.x == "space x"
    del s.x
    assert s.x == "model x"
    del m.x
    with pytest.raises(AttributeError):
        s.x


def test_overriding_dynamic_ref():
    m = mx.new_model()
    s = m.new_space(formula=lambda i: {"refs": {"x": "dynspace x"}})
    s.x = "space x"
    m.x = "model x"
    assert s[1].x == "dynspace x"


def test_overriding_parameter():
    m = mx.new_model()
    s = m.new_space(formula=lambda x: {"refs": {"x": "dynspace x"}})
    s.x = "space x"
    m.x = "model x"
    assert s["param x"].x == "param x"
