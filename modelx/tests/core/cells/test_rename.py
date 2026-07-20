import modelx as mx
import pytest

from modelx.core.errors import FormulaError


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

    # with pytest.raises(ValueError):
    #     sub1.Child1.Foo.rename("Baz")

    foo.rename("Baz")

    # assert tuple(sub1.Child1.cells) == ("Baz",)
    # assert not len(sub1.Child1.Baz)
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


@pytest.fixture
def rename_ns_model():
    m = mx.new_model()
    yield m
    m._impl._check_sanity()
    m.close()


def test_rename_rebinds_namespace(rename_ns_model):
    """Renaming rebinds the space's namespace: the old name stops
    resolving and the new name resolves (GH220)."""
    space = rename_ns_model.new_space("Space")

    @mx.defcells(space=space)
    def foo(x):
        return x * 2

    @mx.defcells(space=space)
    def bar(x):
        return foo(x) + 1

    assert space.bar(3) == 7

    space.foo.rename("foo_renamed")

    # bar's formula still references the old name; it must fail
    # loudly instead of evaluating against the stale binding (GH220).
    with pytest.raises(FormulaError):
        space.bar(3)

    assert space.foo_renamed(3) == 6

    def baz(x):
        return foo_renamed(x) + 10

    space.new_cells(name="baz", formula=baz)
    assert space.baz(3) == 16


def test_rename_rebinds_sub_space_namespace(rename_ns_model):
    """Renaming a base cells rebinds the namespaces of derived sub
    spaces, not only the edited space's own."""
    base = rename_ns_model.new_space("Base")

    @mx.defcells(space=base)
    def foo(x):
        return x * 2

    @mx.defcells(space=base)
    def bar(x):
        return foo(x) + 1

    sub = rename_ns_model.new_space("Sub", bases=base)
    assert sub.bar(3) == 7

    base.foo.rename("foo_renamed")

    with pytest.raises(FormulaError):
        sub.bar(3)

    assert sub.foo_renamed(5) == 10


def test_rename_to_sub_defined_cells_rejected(rename_ns_model):
    """Renaming a base cells onto a name owned by a sub's own defined
    cells must be rejected instead of silently destroying it."""
    m = rename_ns_model
    A = m.new_space("A")
    A.new_cells(name="foo", formula=lambda x: x)
    B = m.new_space("B", bases=A)
    B.new_cells(name="baz", formula=lambda x: x + 100)
    assert B.baz(1) == 101

    with pytest.raises(
            ValueError,
            match=r"cannot rename '.*A\.foo' to 'baz': "
                  r"'.*B\.baz' is already defined"):
        A.foo.rename("baz")

    assert B.baz(1) == 101
    assert B.baz._impl.is_defined()
    assert list(A._impl.cells) == ["foo"]
    assert sorted(B._impl.cells) == ["baz", "foo"]


def test_rename_to_other_base_cells_rejected(rename_ns_model):
    """Renaming onto a name a sub derives from another base must be
    rejected: the sub's derived copy would be overwritten and the
    inheritance links left inconsistent."""
    m = rename_ns_model
    A = m.new_space("A")
    A.new_cells(name="foo", formula=lambda x: x)
    A2 = m.new_space("A2")
    A2.new_cells(name="qux", formula=lambda x: x + 200)
    B = m.new_space("B", bases=[A, A2])
    assert B.qux(1) == 201

    with pytest.raises(
            ValueError,
            match=r"cannot rename '.*A\.foo' to 'qux': "
                  r"'.*B\.qux' is already defined"):
        A.foo.rename("qux")

    assert B.qux(1) == 201
    assert list(A._impl.cells) == ["foo"]


def test_rename_to_deep_sub_defined_cells_rejected(rename_ns_model):
    """The collision check reaches subs of subs."""
    m = rename_ns_model
    A = m.new_space("A")
    A.new_cells(name="foo", formula=lambda x: x)
    B = m.new_space("B", bases=A)
    C = m.new_space("C", bases=B)
    C.new_cells(name="baz", formula=lambda x: x + 300)
    assert C.baz(1) == 301

    with pytest.raises(
            ValueError,
            match=r"cannot rename '.*A\.foo' to 'baz': "
                  r"'.*C\.baz' is already defined"):
        A.foo.rename("baz")

    assert C.baz(1) == 301
    assert list(A._impl.cells) == ["foo"]


def test_rename_base_with_sub_override(rename_ns_model):
    """Renaming a base cells that a sub overrides under the OLD name
    still succeeds and renames the override along, keeping the link."""
    m = rename_ns_model
    A = m.new_space("A")
    A.new_cells(name="foo", formula=lambda x: x)
    B = m.new_space("B", bases=A)
    B.foo.formula = lambda x: x + 50
    assert B.foo._impl.is_defined()
    assert B.foo(1) == 51

    A.foo.rename("bar")

    assert list(A._impl.cells) == ["bar"]
    assert list(B._impl.cells) == ["bar"]
    assert B.bar(1) == 51
    assert B.bar._impl.is_defined()
    assert B.bar._impl.bases[0] is A.bar._impl


def test_rename_to_sub_ref_rejected(rename_ns_model):
    """Non-Cells collisions in subs stay rejected by the pre-existing
    _can_add check."""
    m = rename_ns_model
    A = m.new_space("A")
    A.new_cells(name="foo", formula=lambda x: x)
    B = m.new_space("B", bases=A)
    B.myref = 42

    with pytest.raises(ValueError, match="cannot create cells 'myref'"):
        A.foo.rename("myref")

    assert B.myref == 42
    assert list(A._impl.cells) == ["foo"]


def test_rename_to_same_name_rejected(rename_ns_model):
    """Renaming to the current name fails as a user-facing ValueError,
    not the internal rename_item RuntimeError."""
    m = rename_ns_model
    A = m.new_space("A")
    A.new_cells(name="foo", formula=lambda x: x)

    with pytest.raises(ValueError, match="cannot create cells 'foo'"):
        A.foo.rename("foo")
