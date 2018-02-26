from modelx import *
import pytest


def test_dynamic_spaces():

    def params(x, y):
        return {'bases': _self}

    space = new_model().new_space(name='base', formula=params)

    @defcells
    def distance():
        return (x ** 2 + y ** 2) ** 0.5

    space[3, 4].distance()

    assert space.dynamic_spaces == {'Space1': space[3, 4]}

