import pytest
import modelx as mx


def param(x):
    return {}

@pytest.fixture
def testmodel():
    return mx.new_model()


def test_formula_setter(testmodel):

    s = testmodel.new_space()
    s.formula = param

    assert 'x' in s.parameters
    assert 'x' not in dir(s)


def test_fomula_setter_on_dynamic(testmodel):

    s = testmodel.new_space(formula=param)[1]
    with pytest.raises(AttributeError):
        s.formula = param




