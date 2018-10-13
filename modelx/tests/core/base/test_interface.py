import modelx as mx
import pytest


@pytest.fixture
def sample_objects():
    return mx.new_model(), mx.new_space(), mx.cur_space().new_cells()


@pytest.fixture(params=range(3))
def model_property(request, sample_objects):
    m, s, c = msc = sample_objects
    yield m, msc[request.param]


def test_property_model(model_property):
    m, obj = model_property
    assert m is obj.model