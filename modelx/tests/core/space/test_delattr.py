import pytest
import modelx as mx
from modelx import defcells, new_space


@pytest.fixture
def testmodel():
    return mx.new_model()


def test_delattr_cells(testmodel):

    space = new_space()

    @defcells
    def foo(x):
        return 2 * x

    foo(3)
    del space.foo

    with pytest.raises(AttributeError):
        space.foo(3)

    with pytest.raises(RuntimeError):
        foo(3)


def test_delattr_space(testmodel):

    space = new_space()
    child = space.new_space("Child")
    del space.Child
    assert space.static_spaces == {}


def test_delattr_ref(testmodel):

    s = testmodel.new_space()
    s.x = 3
    assert s.x == 3
    del s.x
    with pytest.raises(AttributeError):
        s.x