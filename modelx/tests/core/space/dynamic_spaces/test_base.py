import modelx as mx
import pytest

@pytest.mark.parametrize("case", [0, 1, 2, 3])
def test_base(case):

    def param0(x):
        return {}

    def param1(x):
        return {"base": _space}

    def param2(x):
        return {"bases": _space}

    def param3(x):
        return {"bases": [_space]}

    params = {k: v for k, v in enumerate([param0, param1, param2, param3])}
    space = mx.new_space(formula=params[case])
    assert space[1].x == 1