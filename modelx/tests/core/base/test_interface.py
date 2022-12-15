import modelx as mx
import pytest


@pytest.fixture
def sample_objects():
    m, s, c = mx.new_model(), mx.new_space(), mx.cur_space().new_cells()
    yield m, s, c
    m._impl._check_sanity()
    m.close()

@pytest.fixture(params=range(3))
def model_obj_pair(request, sample_objects):
    m, s, c = msc = sample_objects
    return m, msc[request.param]


def test_property_model(model_obj_pair):
    m, obj = model_obj_pair
    assert m is obj.model


def test_slots(model_obj_pair):
    _, obj = model_obj_pair

    with pytest.raises(AttributeError):
        object.__getattribute__(obj, "__dict__")


def test_baseattrs(model_obj_pair):
    _, obj = model_obj_pair

    baseattrs = {
        "type": type(obj).__name__,
        "id": id(obj._impl),
        "name": obj.name,
        "fullname": obj.fullname,
        "repr": obj._get_repr(),
    }

    result = obj._baseattrs

    for key in baseattrs:
        assert baseattrs[key] == result[key]
