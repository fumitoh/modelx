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


def test_rename_funcname():
    """
        Space1---foo(rename to bar)

        Space2<--Space1
    """

    m = mx.new_model()
    s1 = m.new_space('Space1')
    s2 = m.new_space('Space2', bases=s1)

    @mx.defcells(space=s1)
    def foo(x):
        return x

    s1.foo.rename('bar')

    for c in (s1.bar, s2.bar):
        assert c.formula.source.split("\n")[0][:7] == "def bar"

    m._impl._check_sanity()
    m.close()
