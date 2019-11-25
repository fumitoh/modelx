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


@pytest.fixture
def ifref_model():
    m, s = mx.new_model("TestModel"), mx.new_space(name='SpaceA')

    @mx.defcells
    def foo(x):
        # Comment
        return x # Comment

    s.another_space = m.new_space(name="SpaceB")
    s.iflist = [foo, s.another_space, m]

    return m


@pytest.mark.parametrize(
    "name",
    [None, "renamed"]
)
def test_reference_identity(ifref_model, tmp_path, name):

    path_ = tmp_path / "testdir"
    write_model(ifref_model, path_)
    m = read_model(path_, name=name)
    assert m.SpaceA.another_space is m.SpaceB
    foo, another, model = m.SpaceA.iflist
    assert foo is m.SpaceA.foo
    assert another is m.SpaceA.another_space
    assert model is m

