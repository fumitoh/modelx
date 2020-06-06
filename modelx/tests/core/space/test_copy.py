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
    base = mx.new_model().new_space("Base")
    sub = mx.new_space(bases=base)

    source = mx.new_space("Source")

    @mx.defcells(source)
    def foo(x):
        return x * a

    source.parameters = ("a",)
    source.a = 1
    source.foo[0] = 1
    source.copy(base, name)

    name = name or source.name

    assert base.spaces[name].foo[0] == 1
    assert base.spaces[name].foo[1] == 1
    assert sub.spaces[name].foo[0] == 0
    assert sub.spaces[name].foo[1] == 1

    assert base.spaces[name][2].foo[1] == 2
    assert sub.spaces[name][2].foo[1] == 2


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


