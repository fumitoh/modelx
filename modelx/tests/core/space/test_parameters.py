import pytest
import modelx as mx



@pytest.fixture
def sample_no_params():
    m = mx.new_model()
    m.new_space("Sample")
    yield m
    m._impl._check_sanity()
    m.close()


@pytest.fixture
def sample_with_params(sample_no_params):

    s = sample_no_params.Sample
    assert s.parameters is None
    s.parameters = ('x', 'y', 'Z')
    return sample_no_params


def test_parameters_setter(sample_no_params):

    s = sample_no_params.Sample
    assert s.parameters is None
    s.parameters = ('x', 'y', 'Z')
    assert s.parameters == ('x', 'y', 'Z')


def test_parameters_deleter(sample_with_params):

    s = sample_with_params.Sample
    assert s.parameters == ('x', 'y', 'Z')
    del s.parameters
    assert s.parameters is None





