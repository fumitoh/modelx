import modelx as mx
import pytest

@pytest.fixture
def testmodel():
    """
        base.x
         | +----base[1].x
        sub.x  (derived)
         | +----sub[1].x
        gsub.x (defined)
    """
    m, base = mx.new_model(), mx.new_space("base")

    base.formula = lambda i: None
    base.x = 1

    sub = mx.new_space("sub", bases=base)
    sub.formula = base.formula
    gsub = mx.new_space("gsub", bases=sub)

    assert base(1).x == 1
    assert sub(1).x == 1

    gsub.x = 3      # defined

    return m


def test_change_baseref(testmodel):
    m = testmodel
    m.base.x = 2
    assert m.base[1].x == 2
    assert m.sub[1].x == 2
    assert m.gsub.x == 3


def test_multinherit_change_baseref():
    """
        base1.x    base2.x
          +-----+---+
                |
             sub.x
    """
    m, base1 = mx.new_model(), mx.new_space("base1")
    base2 = mx.new_space("base2")

    base1.x = 1
    base2.x = 2

    sub = mx.new_space(bases=[base1, base2])
    assert sub.x == 1
    base2.x = 3
    assert sub.x == 1
    del base1.x
    assert sub.x == 3
