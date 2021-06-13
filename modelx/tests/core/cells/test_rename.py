import modelx as mx
import pytest


def test_rename(sample_for_rename_and_formula):
    """
        model-----Parent---Child1---Foo # rename to Baz
               |         |
               |         +-Child2---Bar
               |
               +--Sub1 <- Parent
               |
               +--Sub2[a] <- {1:Child1, *:Child2}

    """
    model = sample_for_rename_and_formula
    sub1 = model.Sub1
    sub2 = model.Sub2
    foo = model.Parent.Child1.Foo

    with pytest.raises(ValueError):
        sub1.Child1.Foo.rename("Baz")

    foo.rename("Baz")

    assert tuple(sub1.Child1.cells) == ("Baz",)
    assert not len(sub1.Child1.Baz)
    assert tuple(sub2.itemspaces) == (2,)   # sub2[2] not deleted
    assert sub2[1].Baz(1) == 1
    assert sub2[2].Bar(1) == 1
