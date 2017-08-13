import pytest

from modelx import *


@pytest.fixture
def sample_space():

    space = create_model(name='samplemodel').create_space(name='samplespace')

    funcdef = """def func(x): return 2 * x"""

    space.create_cells(func=funcdef)

    @defcells
    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo(x - 1) + fibo[x - 2]

    @defcells
    def single_value():
        return 5

    @defcells
    def double(x):
        double[x] = 2 * x

    @defcells
    def triple(x):
        triple[x + 1] = 3 * x

    @defcells
    def quadruple(x):
        quadruple[x] = 4 * x
        return 4 * x

    @defcells
    def return_last(x):
        return return_last(x - 1)

    # @defcells
    # def double_double(x):
    #     return 2 * double[x]

    return space

# def test_double_double(sample_space):
#     assert sample_space.double_double[2] == 8

def test_init_from_str(sample_space):
    assert sample_space.func[2] == 4

def test_getitem(sample_space):
    assert sample_space.fibo[10] == 55


def test_call(sample_space):
    assert sample_space.fibo(10) == 55


def test_setitem(sample_space):
    sample_space.fibo[0] = 1
    assert sample_space.fibo[2] == 2


def test_setitem_in_cells(sample_space):
    assert sample_space.double[3] == 6


def test_setitem_in_wrong_cells(sample_space):
    with pytest.raises(KeyError):
        sample_space.triple[3]


def test_duplicate_assignment(sample_space):
    with pytest.raises(ValueError):
        sample_space.quadruple[4]


def test_set_value(sample_space):
    sample_space.return_last[4] = 5
    assert sample_space.return_last(5) == 5


def test_clear_value(sample_space):
    sample_space.fibo[5]
    sample_space.fibo.clear_value(3)
    assert set(sample_space.fibo) == {(0,), (1,), (2,)}


def test_call_single_value(sample_space):
    assert sample_space.single_value() == 5


def test_single_value(sample_space):
    assert sample_space.single_value == 5


def x_test_itr(sample_space):
    sample_space(5)
    x = [i for i in sample_space]
    assert x == [0, 1, 2, 3, 4, 5]


# -----------------------------------------------------------------
# Test _impl methods

def test_fullname(sample_space):
    assert sample_space.fibo._impl.get_fullname() \
           == "samplemodel.samplespace.fibo"


def test_fullname_omit_model(sample_space):
    assert sample_space.fibo._impl.get_fullname(omit_model=True) \
           == "samplespace.fibo"





