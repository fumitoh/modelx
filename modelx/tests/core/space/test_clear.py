import pytest
import itertools
import modelx as mx

# @pytest.fixture
# def samplemodel():
#     pass


def test_clear_all(make_testmodel_for_clear):
    space = make_testmodel_for_clear.Parent
    space.clear_all()

    assert not len(space.Foo)
    assert not len(space.Child.Bar)
    assert not len(space.itemspaces)
    assert not len(space.Child.itemspaces)



@pytest.mark.parametrize(
    "clear_input, recursive",
    itertools.product([True, False], [True, False])
)
def test_clear_cells(make_testmodel_for_clear, clear_input, recursive):

    space = make_testmodel_for_clear.Parent
    space.clear_cells(clear_input=clear_input, recursive=recursive)

    if clear_input:
        assert not len(space.Foo)
    else:
        assert len(space.Foo) == 1

    if recursive:
        if clear_input:
            assert not len(space.Child.Bar)
        else:
            assert len(space.Child.Bar) == 1
    else:
        assert len(space.Child.Bar) == 2

    assert len(space.itemspaces)
    assert len(space.Child.itemspaces)