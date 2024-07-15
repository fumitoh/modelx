import pytest
import modelx as mx


def param(x):
    return {}

@pytest.fixture
def testmodel():
    m = mx.new_model()
    yield m
    m._impl._check_sanity()
    m.close()

def test_formula_setter(testmodel):

    s = testmodel.new_space()
    assert s.formula is None
    s.formula = param

    assert 'x' in s.parameters
    assert 'x' not in dir(s)


def test_fomula_setter_on_dynamic(testmodel):

    s = testmodel.new_space(formula=param)[1]
    with pytest.raises(AttributeError):
        s.formula = param




