import modelx as mx
import pytest


@pytest.fixture
def curmodel():
    m = mx.new_model()
    assert m is mx.cur_model()
    return m


@pytest.fixture
def curspacemodel(curmodel):
    s = curmodel.new_space()
    assert mx.cur_space() is s
    return curmodel, s


def test_cur_model_on_new_model(curmodel):
    m2 = mx.new_model()
    assert mx.cur_model() is m2
    m = mx.cur_model(curmodel.name)
    assert m is mx.cur_model() is curmodel


def test_cur_model_on_del_model(curmodel):
    curmodel.close()
    assert mx.cur_model() is None


def test_cur_space_on_del_model(curspacemodel):
    m, s = curspacemodel
    m.close()
    assert mx.cur_space() is None


def test_cur_space_on_del_space(curspacemodel):
    m, s = curspacemodel
    del m.spaces[s.name]
    assert mx.cur_space() is None
