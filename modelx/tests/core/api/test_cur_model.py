import modelx as mx
import pytest


@pytest.fixture
def curmodel():
    m = mx.new_model('curmodel')
    assert m is mx.cur_model()
    yield m
    if m in mx.models.values():
        m._impl._check_sanity()
        m.close()


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
    m2.close()


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


def test_cur_model_change_after_new_space(curmodel):
    m1 = curmodel
    m2 = mx.new_model()
    c1 = m1.new_space()
    assert mx.cur_model() is m1
    assert mx.cur_space() is c1
    m2.close()


def test_cur_model_change_after_cur_space(curmodel):
    m1 = curmodel
    c1 = m1.new_space()
    m2 = mx.new_model()
    mx.cur_space(c1)
    assert mx.cur_model() is m1
    assert mx.cur_space() is c1
    m2.close()
