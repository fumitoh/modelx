import modelx as mx
from modelx.testing.testutil import SuppressFormulaError
import pytest


@pytest.fixture
def refmodel():
    """
    m------SpaceA----bar
        +--baz    +--foo
    """
    m = mx.new_model()
    m.baz = 1
    s = m.new_space("SpaceA")

    def foo():
        return bar * baz

    s.new_cells(formula=foo)
    s.bar = 3
    assert s.foo() == 3
    return m


@pytest.fixture(params=[True, False])
def refspace(request, refmodel, tmpdir_factory):

    model = refmodel
    if request.param:
        file = str(tmpdir_factory.mktemp("data").join("refmodel.mx"))
        model.save(file)
        model.close()
        model = mx.restore_model(file)

    yield model.SpaceA
    model.close()


def test_update_ref(refspace):

    refspace.bar = 5
    assert refspace.foo() == 5


def test_delete_ref(refspace):

    del refspace.bar

    with SuppressFormulaError():
        with pytest.raises(NameError):
            refspace.foo()


def test_override_global(refspace):

    assert refspace.foo() == 3
    refspace.baz = 5
    assert refspace.foo() == 15


def test_delete_global(refspace):

    assert refspace.foo() == 3
    del refspace.model.baz
    with SuppressFormulaError():
        with pytest.raises(NameError):
            refspace.foo()

