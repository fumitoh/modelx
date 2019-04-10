import modelx as mx

import pytest

@pytest.fixture
def testmodel():

    m = mx.new_model('Model')
    m.new_space('Parent').new_space('Child').new_cells('foo')

    m.Parent.formula = lambda x: None
    m.Parent.Child.formula = lambda y, z: None
    m.Parent.Child.foo.formula = lambda i: 2 * i

    m.new_space('NoArgs').new_cells('foo')
    m.NoArgs.formula = lambda: None

    return m


params_static = [
    [True, True, "Model.Parent.Child.foo(i)"],
    [True, False, "Model.Parent.Child.foo"],
    [False, True, "foo(i)"],
    [False, False, "foo"]
]


@pytest.mark.parametrize("fullname, add_params, expected", params_static)
def test_fullname(testmodel, fullname, add_params, expected):

    m = testmodel
    assert m.Parent.Child.foo._get_repr(
        fullname=fullname,
        add_params=add_params
    ) == expected



params_dynamic = [
    [True, True, "Model.Parent[1].Child[2, 3].foo(i)"],
    [True, False, "Model.Parent[1].Child[2, 3].foo"],
    [False, True, "foo(i)"],
    [False, False, "foo"]
]


@pytest.mark.parametrize("fullname, add_params, expected", params_dynamic)
def test_fullname(testmodel, fullname, add_params, expected):

    m = testmodel
    assert m.Parent[1].Child[2, 3].foo._get_repr(
        fullname=fullname,
        add_params=add_params
    ) == expected


def test_evalrepr(testmodel):
    m = testmodel
    assert m.Parent.Child.foo._evalrepr == "Model.Parent.Child.foo"
    assert (m.Parent[1].Child[2, 3].foo._evalrepr
            == "Model.Parent(1).Child(2, 3).foo")
    assert m.NoArgs().foo._evalrepr == "Model.NoArgs().foo"