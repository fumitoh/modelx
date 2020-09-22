import itertools
import zipfile
import pytest
from modelx import (
    write_model,
    read_model)
from modelx.testing import testutil
import modelx as mx


@pytest.fixture
def testmodel():
    """
    TestModel-----TestSpace[a]-----foo
                                |
                                +--m = 1
                                +--n = "abc"
                                +--t = nested sequences
                                +--u = dict
                                +--v = TestModel
                                +--w = foo
                                |
                                +--Another
                                +s = Another

    """
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
    ["name", "version", "as_method", "write_method"],
    itertools.product(
        [None, "renamed"],
        [2, 3, 4],
        [True, False],
        ["write", "zip"]
    )
)
def test_read_write_model(testmodel, tmp_path, name, version, as_method,
                          write_method):

    path_ = tmp_path / "testdir"
    if as_method:
        getattr(testmodel, write_method)(path_)
    else:
        if as_method == "zip":
            kwargs = dict(compression=zipfile.ZIP_STORED, version=version)
        else:
            kwargs = {}
        getattr(mx, write_method + "_model")(
            testmodel, path_, **kwargs)
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
    """
    TestModel---SpaceA-----foo(x)
                        +--lambdacells(x)
                        |
                        +--SpaceB--ou = [o, u]
                        |
                        +--o = list
                        +--u = dict
                        +--iflist = [foo, SpaceB, TestModel]
                        +--ifwrap = InterfaceWrapper(foo, SpaceB, TestModel)
    """
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
    "name, write_method",
    [[None, "write_model"], ["renamed", "zip_model"]]
)
def test_reference_identity(pickletest, tmp_path, name, write_method):

    path_ = tmp_path / "testdir"
    getattr(mx, write_method)(pickletest, path_)
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


@pytest.fixture(params=range(2))
def combined_testmodel_fixture(testmodel, pickletest, request):
    return [testmodel, pickletest][request.param]


@pytest.mark.parametrize("meth_or_func, compression",
                         itertools.product(["meth", "func"],
                                           [zipfile.ZIP_DEFLATED,
                                            zipfile.ZIP_STORED]))
def test_zip_compression(
        combined_testmodel_fixture, tmp_path, meth_or_func, compression):

    model = combined_testmodel_fixture

    if meth_or_func == "meth":
        model.zip(tmp_path / "model.zip",
                       compression=compression)
    else:
        mx.zip_model(model, tmp_path / "model.zip",
                     compression=compression)

    archive = zipfile.ZipFile(tmp_path / "model.zip")

    for info in archive.infolist():
        assert info.compress_type == compression


@pytest.mark.parametrize("write_method", ["write_model", "zip_model"])
def test_nested_space(tmp_path, write_method):

    m, s = mx.new_model(), mx.new_space()
    ns = s.new_space()

    @mx.defcells
    def foo(x):
        return x

    foo[0] = 2

    getattr(mx, write_method)(m, tmp_path / "model")
    m2 = read_model(tmp_path / "model")

    testutil.compare_model(m, m2)


@pytest.mark.parametrize("write_method", ["write_model", "zip_model"])
def test_nested_derived(tmp_path, write_method):
    """
        m---A---B
            |
            C---B*
    """
    m = mx.new_model()
    A = m.new_space('A')
    B = A.new_space('B')
    C = m.new_space('C', bases=A)

    assert C.B._is_derived()

    getattr(mx, write_method)(m, tmp_path / "model")
    m2 = read_model(tmp_path / "model")

    testutil.compare_model(m, m2)