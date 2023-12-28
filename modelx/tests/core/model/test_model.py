import pytest

from modelx.core.api import *
from modelx.core.node import get_node
from modelx.testing.testutil import SuppressFormulaError


@pytest.fixture
def simplemodel():

    model = new_model(name="simplemodel")
    space = model.new_space()

    @defcells
    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo(x - 1) + fibo(x - 2)

    model.bar = 3

    yield model
    model._impl._check_sanity()
    model.close()


def test_clear_all(make_testmodel_for_clear):
    m = make_testmodel_for_clear
    m.clear_all()
    space = m.Parent
    assert not len(space.Foo)
    assert not len(space.Child.Bar)
    assert not len(space.itemspaces)
    assert not len(space.Child.itemspaces)


def test_parent(simplemodel):
    assert simplemodel.parent == None


def test_autoname_space(simplemodel):
    assert simplemodel.cur_space().name == "Space1"


def test_dir(simplemodel):
    names = dir(simplemodel)
    assert "Space1" in names
    assert "__builtins__" in names
    assert "bar" in names


def test_new_space(simplemodel):
    space = simplemodel.new_space()
    assert space in simplemodel.spaces.values()


def test_mro_simple(simplemodel):
    model = simplemodel
    C = model.new_space(name="C")
    A = model.new_space(name="A", bases=C)
    B = model.new_space(name="B", bases=C)
    D = model.new_space(name="D", bases=[A, B])

    assert model._impl.spmgr._graph.get_mro("D") == ["D", "A", "B", "C"]


def test_mro_complicated(simplemodel):
    model = simplemodel
    o = model.new_space(name="o")
    f = model.new_space(name="f", bases=o)
    e = model.new_space(name="e", bases=o)
    d = model.new_space(name="d", bases=o)
    c = model.new_space(name="c", bases=[d, f])
    b = model.new_space(name="b", bases=[e, d])
    a = model.new_space(name="a", bases=[b, c])

    assert model._impl.spmgr._graph.get_mro("a") == (
        ["a", "b", "e", "c", "d", "f", "o"]
    )


def test_tracegraph(simplemodel):
    def get_predec(node):
        return simplemodel._impl.tracegraph.predecessors(node)

    def get_succ(node):
        return simplemodel._impl.tracegraph.successors(node)

    space = simplemodel.spaces["Space1"]

    space.fibo[10]

    for x in range(10):
        fibo = get_node(space.fibo._impl, (x,), {})
        fibo_prev1 = get_node(space.fibo._impl, (x - 1,), {})
        fibo_prev2 = get_node(space.fibo._impl, (x - 2,), {})
        fibo_next1 = get_node(space.fibo._impl, (x + 1,), {})
        fibo_next2 = get_node(space.fibo._impl, (x + 2,), {})

        if x == 0 or x == 1:
            assert list(get_predec(fibo)) == []
            assert fibo_next2 in get_succ(fibo)
        elif x < 9:
            assert fibo_prev1 in get_predec(fibo)
            assert fibo_prev2 in get_predec(fibo)
            assert fibo_next1 in get_succ(fibo)
            assert fibo_next2 in get_succ(fibo)


def test_tracegraph_standalone():
    model, space = new_model(), new_space()

    @defcells(space=space)
    def foo(x):
        return x

    foo(1)
    nodes = model.tracegraph.nodes()
    assert get_node(foo._impl, (1,), {}) in nodes

    model._impl._check_sanity()
    model.close()


def test_refs(simplemodel):
    assert 'bar' in simplemodel.refs
    assert simplemodel.bar == simplemodel.refs['bar']


def test_global_ref_attr(simplemodel):
    model = simplemodel
    space = new_space()

    @defcells(space)
    def func1(x):
        return min(n, x)

    model.n = 2
    assert func1(3) == 2 and model.n == 2


def test_global_ref_delattr():
    model, space = new_model(), new_space()

    @defcells
    def func1(x):
        return min(n, x)

    model.n = 2
    del model.n

    with SuppressFormulaError():
        with pytest.raises(NameError):
            func1(4)

    model._impl._check_sanity()
    model.close()


def test_rename():

    model = new_model(name="oldname")
    model.rename("newname")

    assert get_models()["newname"] == model
    assert model.name == "newname"

    model._impl._check_sanity()
    model.close()


# ---- Test impl ----


def test_get_impl_from_name(simplemodel):

    assert (
        simplemodel._impl.get_impl_from_name("Space1.fibo")
        is simplemodel._impl.spaces["Space1"].cells["fibo"]
    )
