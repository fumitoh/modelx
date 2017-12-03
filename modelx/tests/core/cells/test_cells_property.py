from itertools import product
import pytest

from modelx import *
from modelx.core.errors import NoneReturnedError

paramx = [[False, False, True],
          [False, True, None],
          [True, None, None]]
paramy = ['get', 'set']
param = [x + [y] for x, y in product(paramx, paramy)]

@pytest.mark.parametrize("model_param, space_param, cells_param, op", param)
def test_with_sapce_can_have_none_true(model_param,
                                       space_param,
                                       cells_param,
                                       op):
    model, space = new_model(), new_space()
    cells = space.new_cells(func="def test1(x): return None")

    model.can_have_none = model_param
    space.can_have_none = space_param
    cells.can_have_none = cells_param

    if op == 'get':
        assert cells[1] is None
    else:
        cells[0] = None # Check no error is raised
        assert True


paramx = [[False, False, False],
          [False, False, None],
          [False, None, None]]
paramy = ['get', 'set']
param = [x + [y] for x, y in product(paramx, paramy)]

@pytest.mark.parametrize("model_param, space_param, cells_param, op", param)
def test_with_sapce_can_have_none_false(model_param,
                                        space_param,
                                        cells_param,
                                        op):
    model, space = new_model(), new_space()
    cells = space.new_cells(func="def test1(x): return None")

    model.can_have_none = model_param
    space.can_have_none = space_param
    cells.can_have_none = cells_param

    with pytest.raises(NoneReturnedError) as errinfo:
        if op == 'get':
            assert cells[1] == None
        else:
            cells[1] = None
