from textwrap import dedent
import pytest

from modelx import *
from modelx.core.errors import NoneReturnedError

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

    def func1(x):
        return 5 * x

    def func2(y):
        return 6 * y

    func1, func2 = defcells(func1, func2)

    # @defcells
    # def double_double(x):
    #     return 2 * double[x]

    return space

# def test_double_double(sample_space):
#     assert sample_space.double_double[2] == 8

def test_defcells_funcs(sample_space):
    assert sample_space.func1[2] == 10 \
        and sample_space.func2[2] == 12

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
    # fibo = sample_space.fibo
    sample_space.fibo.clear_value(3)
    assert set(sample_space.fibo) == {(0,), (1,), (2,)}


def test_clear_value_source(sample_space):

    space = sample_space

    f1 = dedent("""\
        def source(x):
            if x == 1:
                return 1
            else:
                return source(x - 1) + 1""")

    f2 = dedent("""\
        def dependant(x):
            return 2 * source(x)""")

    space.create_cells(func=f1)
    space.create_cells(func=f2)

    errors = []
    space.dependant(2)
    if not set(space.dependant) == {(2,)}:
        errors.append("error with dependant")
    if not set(space.source) == {(1,), (2,)}:
        errors.append("error with source")

    space.source.clear_value(1)
    if not set(space.source) == set():
        errors.append("clear error with source")
    if not set(space.dependant) == set():
        errors.append("clear error with dependant")

    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_clear_formula(sample_space):

    space = sample_space
    f1 = dedent("""\
        def clear_source(x):
            if x == 1:
                return 1
            else:
                return clear_source(x - 1) + 1""")

    f2 = dedent("""\
        def clear_dependant(x):
            return 2 * clear_source(x)""")

    source = space.create_cells(func=f1)
    dependant = space.create_cells(func=f2)

    errors = []
    dependant(2)
    if not set(dependant) == {(2,)}:
        errors.append("error with dependant")
    if not set(source) == {(1,), (2,)}:
        errors.append("error with source")

    source.clear_formula()
    if not set(source) == set():
        errors.append("clear error with source")
    if not set(dependant) == set():
        errors.append("clear error with dependant")

    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_set_formula(sample_space):

    space = sample_space
    f1 = dedent("""\
        def clear_source(x):
            if x == 1:
                return 1
            else:
                return clear_source(x - 1) + 1""")

    f2 = dedent("""\
        def clear_dependant(x):
            return 2 * clear_source(x)""")

    f3 = dedent("""\
        def replace_source(x):
            if x == 1:
                return 2
            else:
                return clear_source(x - 1) + 1""")

    source = space.create_cells(func=f1)
    dependant = space.create_cells(func=f2)

    errors = []
    dependant(2)
    if not set(dependant) == {(2,)}:
        errors.append("error with dependant")
    if not set(source) == {(1,), (2,)}:
        errors.append("error with source")

    source.set_formula(f3)
    result = dependant(2)
    if not set(source) == {(1,), (2,)}:
        errors.append("clear error with source")
    if not set(dependant) == {(2,)}:
        errors.append("clear error with dependant")
    if not result == 6:
        errors.append("invalid result")

    assert not errors, "errors occured:\n{}".format("\n".join(errors))


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


# -----------------------------------------------------------------
# Test errors


def test_none_returned_error():

    errfunc = dedent("""\
        def return_none(x, y):
            return None""")

    space = create_model(name='ErrModel').create_space(name='ErrSpace')
    cells = space.create_cells(func=errfunc)
    cells.can_return_none = False
    with pytest.raises(NoneReturnedError) as errinfo:
        cells(1, 3)

    errmsg = dedent("""
        None returned from ErrModel.ErrSpace.return_none(x=1, y=3).
        Call stack traceback:
        0: ErrModel.ErrSpace.return_none(x=1, y=3)
        """)

    assert errinfo.value.args[0] == errmsg
