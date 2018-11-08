import modelx as mx
import pytest


@pytest.fixture
def sample_objects():
    return mx.new_model(), mx.new_space(), mx.cur_space().new_cells()


@pytest.fixture(params=range(3))
def model_obj_pair(request, sample_objects):
    m, s, c = msc = sample_objects
    yield m, msc[request.param]


def test_property_model(model_obj_pair):
    m, obj = model_obj_pair
    assert m is obj.model


def test_slots(model_obj_pair):
    m, obj = model_obj_pair

    with pytest.raises(Exception):
        obj.__dict__
