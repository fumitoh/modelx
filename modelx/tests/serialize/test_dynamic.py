import pytest
import modelx as mx


def t_arg(t):
    pass

@pytest.fixture
def dynmodel():
    """
    DynModel-----SpaceA[t]-----foo(x)
              |             |
              |             +--SpaceA[1]---foo(2) == 3
              |
              +--SpaceB-----RefSpaceA = SpaceA[0]

    """
    m = mx.new_model("DynModel")
    s1 = m.new_space('SpaceA', formula=t_arg)

    @mx.defcells
    def foo(x):
        return x

    m.new_space('SpaceB', refs={'RefSpaceA': m.SpaceA(0)})
    s1[1].foo[2] = 3
    return m


def test_dynmodel(dynmodel, tmp_path):

    path_ = tmp_path / "testdir"
    mx.write_model(dynmodel, path_)
    m = mx.read_model(path_)

    assert m.SpaceA[0] is m.SpaceB.RefSpaceA
    assert m.SpaceA[1].foo[2] == 3


class Tot_func:
    def __init__(self, space, cell):
        self.cell = cell
        self.space = space

    def Sum(self, *args):
        return sum([self.space(id).cells[self.cell](*args) for id in range(0, 10)])


def s_arg(id):
    if id == -1:
        refs = {cell: m.Tot_func(m.s_base, cell).Sum for cell in m.s_base.cells}
    else:
        refs = {cell: m.s_base(id).cells[cell] for cell in m.s_base.cells}
    return {'refs': refs}


@pytest.fixture
def dyntotal():
    """
    Model-----s_base[id]-----a(i)
           |              +--b(i, j)
           +--s[id]
           |
           +--Tot_func
           |
           +--m
    """
    m = mx.new_model()
    s_base = mx.new_space('s_base', formula=lambda id: None)

    @mx.defcells
    def a(i):
        return i

    @mx.defcells
    def b(i, j):
        return i * j

    m.Tot_func = Tot_func
    m.m = m

    s = mx.new_space('s', formula=s_arg)
    return m


def test_dyntotal(dyntotal, tmp_path):

    path_ = tmp_path / "testdir"
    mx.write_model(dyntotal, path_)
    m = mx.read_model(path_)

    assert m.s(-1).a(2) == 2 * 10
    assert m.s(0).a(2) == 2
    assert m.s(-1).b(2, 3) == 2 * 3 * 10
    assert m.s(0).b(2, 3) == 2 * 3