import itertools
import pytest
from modelx import (
    write_model,
    read_model)
from modelx.testing import testutil
import modelx as mx
from . import SERIALIZE_VERS


@pytest.fixture
def testmodel():
    m, s = mx.new_model("TestModel"), mx.new_space(name='TestSpace')

    @mx.defcells
    def foo(x):
        # Comment
        return x # Comment

    s.formula = lambda a: None

    s.m = 1
    s.n = "abc"
    s.o = [1, "2"]
    s.t = (1, 2, "藍上夫", (3, 4.33), [5, None, (7, 8, [9, 10], "ABC")])
    s.u = {3: '4',
           '5': ['6', 7]}

    # modelx objects as refs
    s.v = m
    s.w = foo
    an = m.new_space(name="Another")
    s.s = an

    return m


@pytest.mark.parametrize(
    ["name", "version"],
    itertools.product([None, "renamed"], SERIALIZE_VERS)
)
def test_read_write_model(testmodel, tmp_path, name, version):

    path_ = tmp_path / "testdir"
    write_model(testmodel, path_, version=version)
    m = read_model(path_, name=name)

    assert m.name == (name if name else "TestModel")
    if name is None:
        testutil.compare_model(testmodel, m)

    # Check identities of modelx objects as refs
    assert m is m.TestSpace.v
    assert m.TestSpace.foo is m.TestSpace.w
    assert m.TestSpace.s is m.Another


class InterfaceWrapper:

    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c


@pytest.fixture
def pickletest():
    m, s = mx.new_model("TestModel"), mx.new_space(name='SpaceA')

    @mx.defcells
    def foo(x):
        # Comment
        return x # Comment

    c = s.new_cells(name="lambdacells", formula=lambda x: 2 * x)

    s.another_space = m.new_space(name="SpaceB")

    # modelx objects in other objects
    s.iflist = [foo, s.another_space, m]
    s.ifwrap = InterfaceWrapper(foo, s.another_space, m)

    # same objects
    s.o = [1, "2"]
    s.u = {3: '4',
           '5': ['6', 7]}
    s.another_space.ou = [s.o, s.u]

    # Cells input data
    foo[0] = 0
    foo[1] = m
    c[0] = "123"
    c[s] = 3

    return m


@pytest.mark.parametrize(
    "name",
    [None, "renamed"]
)
def test_reference_identity(pickletest, tmp_path, name):

    path_ = tmp_path / "testdir"
    write_model(pickletest, path_)
    m = read_model(path_, name=name)

    assert m.SpaceA.another_space is m.SpaceB
    foo, another, model = m.SpaceA.iflist
    assert foo is m.SpaceA.foo
    assert another is m.SpaceA.another_space
    assert model is m

    assert m.SpaceA.ifwrap.a is foo
    assert m.SpaceA.ifwrap.b is m.SpaceA.another_space
    assert m is m.SpaceA.ifwrap.c

    # same objects
    assert m.SpaceA.o is m.SpaceB.ou[0]
    assert m.SpaceA.u is m.SpaceB.ou[1]

    # Cells input data
    assert dict(m.SpaceA.foo) == {0: 0, 1: m}
    assert dict(m.SpaceA.lambdacells) == {0: "123", m.SpaceA: 3}
