import modelx as mx
import pytest

def test_rename():
    """
        model-----Parent---Child1---Foo # rename to Baz
               |         |
               |         +-Child2---Bar
               |
               +--Sub1 <- Parent
               |
               +--Sub2[a] <- {1:Child1, *:Child2}

    """
    model = mx.new_model()
    parent = model.new_space('Parent')
    child1 = parent.new_space('Child1')
    child2 = parent.new_space('Child2')
    foo = child1.new_cells('Foo', formula=lambda x: x)
    bar = child2.new_cells('Bar', formula=lambda x: x)
    sub1 = model.new_space('Sub1', bases=parent)

    def _param(a):
        b = Parent.Child1 if a == 1 else Parent.Child2
        return {'bases': b}

    sub2 = model.new_space('Sub2', formula=_param)
    sub2.Parent = parent
    foo(1)
    bar(1)
    sub2[1].Foo(1)
    sub2[2].Bar(1)

    assert tuple(sub1.Child1.cells) == ("Foo",)
    assert tuple(sub2.itemspaces) == (1, 2)

    with pytest.raises(ValueError):
        sub1.Child1.Foo.rename("Baz")

    foo.rename("Baz")

    assert tuple(sub1.Child1.cells) == ("Baz",)
    assert tuple(sub2.itemspaces) == (2,)   # sub2[2] not deleted
    assert sub2[1].Baz(1) == 1
    assert sub2[2].Bar(1) == 1
