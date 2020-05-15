import modelx as mx
from modelx import defcells
from modelx.testing.testutil import SuppressFormulaError
import pytest


@pytest.fixture
def cells_signatures():

    model = mx.new_model("Model")
    space = model.new_space("Space")

    @defcells
    def no_param():
        return 1

    @defcells
    def single_param(x):
        return x

    @defcells
    def single_param_with_default(x=1):
        return x

    @defcells
    def mult_params(x, y):
        return x + y

    @defcells
    def mult_params_with_default(x, y, z=3):
        return sum([x, y, z])

    yield space
    model.close()


def test_get_too_many_args(cells_signatures):

    space = cells_signatures

    with SuppressFormulaError():

        with pytest.raises(TypeError):
            space.no_param(1)

        with pytest.raises(TypeError):
            space.no_param[1]

        with pytest.raises(TypeError):
            space.single_param(1, 2)

        with pytest.raises(TypeError):
            space.single_param[1, 2]

        with pytest.raises(TypeError):
            space.single_param[(1, 2)]  # Intepreted as [1, 2]


def test_get_too_few_args(cells_signatures):

    space = cells_signatures

    with SuppressFormulaError():

        with pytest.raises(TypeError):
            space.single_param()

        with pytest.raises(TypeError):
            space.mult_params(1)

        with pytest.raises(TypeError):
            space.mult_params[1]


def test_get_default_args(cells_signatures):

    space = cells_signatures
    assert space.single_param_with_default() == 1
    assert space.mult_params_with_default(1, 2) == 6
    assert space.mult_params_with_default[1, 2] == 6
    assert space.mult_params_with_default[(1, 2)] == 6
    with pytest.raises(TypeError):
        assert space.mult_params_with_default[[1, 2]] == 6


def test_getitem_string(cells_signatures):

    space = cells_signatures
    assert space.single_param["foo"] == "foo"
    assert space.single_param_with_default["bar"] == "bar"
    assert space.mult_params["foo", "bar"] == "foobar"
    assert space.mult_params[("foo", "bar")] == "foobar"
    with pytest.raises(TypeError):
        assert space.mult_params[["foo", "bar"]] == "foobar"


def test_scalar_cells_arg(cells_signatures):

    space = cells_signatures
    assert isinstance(space.single_param(space.no_param), type(space.no_param))


def test_cells_as_arg(cells_signatures):

    space = cells_signatures
    assert space.mult_params is space.single_param(space.mult_params)
