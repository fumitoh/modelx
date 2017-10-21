import pytest

from modelx import *


@pytest.fixture
def testmodel():
    return new_model()

def test_set_formula_base(testmodel):

    base = new_space('base')

    @defcells
    def f1(x):
        return x

    def f2(x):
        return 2 * x

    derived = new_space(name='derived', bases=base)
    before_set = derived.f1(3)
    base.f1.set_formula(f2)
    after_set = derived.f1(3)

    assert before_set == 3 and after_set == 6






