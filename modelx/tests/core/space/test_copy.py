import modelx as mx
import pytest


@pytest.mark.parametrize("name", [None, "Target"])
def test_copy(name):
    """
        Before:
        Base<------Sub      Source[a]
                              |
                             foo
        After:
        Base<------Sub
         |          |
        Source     Source*
         |          |
        foo        foo*
    """
    model = mx.new_model()
    base = model.new_space("Base")
    sub = mx.new_space(bases=base)

    source = mx.new_space("Source")

    @mx.defcells(source)
    def foo(x):
        return x * a

    source.parameters = ("a",)
    source.a = 1
    source.foo[0] = 1
    target = source.copy(base, name)

    name = name or source.name

    assert target is base.spaces[name]

    assert base.spaces[name].foo[0] == 1
    assert base.spaces[name].foo[1] == 1
    assert sub.spaces[name].foo[0] == 0
    assert sub.spaces[name].foo[1] == 1

    assert base.spaces[name][2].foo[1] == 2
    assert sub.spaces[name][2].foo[1] == 2

    model._impl._check_sanity()
    model.close()


def test_copy_error_name_conflict():
    """
        Base<------Sub      Source
          |         |         |
        SpaceA    SpaceA*    foo
    """
    m, base = mx.new_model(), mx.new_space("Base")
    sub = m.new_space(bases=base)
    base.new_space("SpaceA")

    source = mx.new_space("Source")
    source.new_cells("foo")

    with pytest.raises(ValueError):
        source.copy(base, "SpaceA")

    m._impl._check_sanity()
    m.close()

@pytest.mark.parametrize("parent", ["model", "space"])
def test_copy_defined(parent):
    """
        Base----Child---foo
         |
        Sub(Base)----bar

    """

    m, b = mx.new_model(), mx.new_space("Base")
    b.new_space("Child")

    @mx.defcells
    def foo(x):
        return x

    s = m.new_space("Sub", bases=b)

    @mx.defcells
    def bar(y):
        return y

    if parent == "model":
        parent = m
    else:
        parent = m.new_space()

    bc = b.copy(parent, "BaseCopy", True)

    assert "foo" in bc.Child.cells

    sc = s.copy(parent, "SubCopy", True)

    assert "Child" not in sc.spaces
    assert "bar" in sc.cells

    m._impl._check_sanity()
    m.close()

