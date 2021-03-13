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


@pytest.mark.parametrize("write_method, rename",
                         zip(["write_model", "zip_model"], [False, True]))
def test_dynmodel(dynmodel, tmp_path, write_method, rename):

    path_ = tmp_path / "testdir"
    getattr(mx, write_method)(dynmodel, path_)
    if rename:
        m = mx.read_model(path_, name="renamed")
    else:
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


@pytest.mark.parametrize("write_method, rename",
                         zip(["write_model", "zip_model"], [False, True]))
def test_dyntotal(dyntotal, tmp_path, write_method, rename):

    path_ = tmp_path / "testdir"
    getattr(mx, write_method)(dyntotal, path_)
    if rename:
        m = mx.read_model(path_, name="renamed")
    else:
        m = mx.read_model(path_)

    assert m.s(-1).a(2) == 2 * 10
    assert m.s(0).a(2) == 2
    assert m.s(-1).b(2, 3) == 2 * 3 * 10
    assert m.s(0).b(2, 3) == 2 * 3


@pytest.mark.parametrize("write_method", ["write_model", "zip_model"])
def test_assign_dynamic_space_to_ref(tmp_path, write_method):
    """
        m-+-s1-s3-b<-s2(0)
          |
          +-s2(t)-a

    """
    # https://github.com/fumitoh/modelx/issues/25

    m, s1 = mx.new_model(), mx.new_space("s1")

    def t_arg(t):
        pass

    m.new_space(name='s2', formula=t_arg, refs={'a': 1})
    s3 = s1.new_space(name='s3')
    s3.b = m.s2(0)
    path_ = tmp_path / "assign_dynamic_space_to_ref"
    getattr(mx, write_method)(m, path_)
    m2 = mx.read_model(path_)
    assert m2.s2.a == 1
    assert m2.s2(0).a == 1


@pytest.mark.parametrize("write_method", ["write_model", "zip_model"])
def test_assign_dynamic_space_to_ref2(tmp_path, write_method):
    """
       m-+-a-d-c<-c()
         |
         +-b
         |
         +-c()-x<-b
    """
    # https://github.com/fumitoh/modelx/issues/37

    m = mx.new_model()
    m.new_space('a')

    def t_arg():
        pass

    m.new_space('b')
    m.new_space('c', formula=t_arg, refs={'x': m.b})
    m.a.new_space('d',refs={'c':m.c()})
    path_ = tmp_path / "model"
    getattr(mx, write_method)(m, path_)
    m2 = mx.read_model(path_)
    assert m2.a.d.c is m2.c()