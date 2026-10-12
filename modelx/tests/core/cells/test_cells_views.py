"""Tests for ``Cells.values()`` and ``Cells.items()``.

Before these views, both came from ``collections.abc.Mapping``, which
looks each key that ``iter(cells)`` yields up again as ``cells[key]``.
``Cells.__getitem__`` reads a tuple as the whole argument tuple, so for
a Cells ``h(x)`` whose argument is a tuple the key was read as other
arguments: with ``h((1, 2))`` stored, values() and items() raised
TypeError; with only ``h((1,))`` stored, they ran the formula for
``h(1)``, stored it, and raised RuntimeError (dictionary changed size
during iteration); with both stored, they gave ``h(1)``'s value for the
key ``(1,)``. Their ``in`` read ``cells[key]`` too, so
``(key, value) in cells.items()`` ran the formula for a key that was
not stored.

Every test checks that the views run no formula: each formula appends
to the global Reference ``calls``, so ``len(m.calls)`` counts the
formula runs, including a run whose value is not stored, and
``len(m.tracegraph)`` counts the stored values.
"""
import pytest

import modelx as mx


@pytest.fixture
def model():
    """
    CellsViews---S[i]---h(x), g(t, k=1), two(x, y), z(), one_def(x=0),
            |       |   va(*args), a_va(a, *args), u(x) uncached
            |       +---Child---w(x)
            +--calls = []

    No value is stored; each test stores the values it reads.
    """
    m = mx.new_model("CellsViews")
    m.calls = []
    s = m.new_space("S", formula=lambda i: None)
    s.new_cells("h", formula=lambda x: calls.append("h") or "h got " + repr(x))
    s.new_cells("g", formula=lambda t, k=1: calls.append("g") or (t, k))
    s.new_cells("two", formula=lambda x, y: calls.append("two") or x * y)
    s.new_cells("z", formula=lambda: calls.append("z") or 42)
    s.new_cells("one_def", formula=lambda x=0: calls.append("one_def") or x)
    s.new_cells("va", formula=lambda *args: calls.append("va") or args)
    s.new_cells(
        "a_va", formula=lambda a, *args: calls.append("a_va") or (a, args))
    u = s.new_cells("u", formula=lambda x: calls.append("u") or x)
    u.is_cached = False
    child = s.new_space("Child")
    child.new_cells("w", formula=lambda x: calls.append("w") or ("w", x))
    yield m
    m._impl._check_sanity()
    m.close()


def state(m):
    """What a read that runs a formula changes: the number of stored
    values (nodes in the trace graph) and the number of formula runs."""
    return len(m.tracegraph), len(m.calls)


def node_args(cells, key):
    """The arguments of a key that ``iter(cells)`` yields, for
    ``cells.node(*args)``: ``(key,)`` for one parameter, ``key``
    otherwise."""
    return (key,) if len(cells.parameters) == 1 else key


def check_views(m, cells, expected):
    """Every read through ``values()`` and ``items()`` of ``cells`` gives
    ``expected``, a list of ``(key, value)`` in storing order, and runs
    no formula."""
    before = state(m)
    keys = list(cells.keys())

    assert list(cells.items()) == expected
    assert list(cells.values()) == [v for _, v in expected]
    assert [k for k, _ in cells.items()] == list(cells) == keys
    assert len(cells.items()) == len(cells.values()) == len(expected)
    assert dict(cells.items()) == dict(expected)

    for key, value in expected:
        assert value in cells.values()
        assert (key, value) in cells.items()
        assert (key, ("not", value)) not in cells.items()
    assert ("not stored",) not in cells.values()

    # The Set methods of ItemsView go through __iter__ and __contains__.
    pairs = set(expected)
    assert cells.items() == pairs
    assert cells.items() <= pairs and cells.items() >= pairs
    assert (cells.items() & pairs) == pairs
    assert not cells.items().isdisjoint(pairs) or not pairs
    assert (cells.items() - pairs) == set()

    assert state(m) == before
    assert list(cells.keys()) == keys


# --------------------------------------------------------------------------
# The three cases of the defect


def test_tuple_argument(model):
    """h((1, 2)) stored: values() and items() raised TypeError."""
    h = model.S.h
    h((1, 2))
    check_views(model, h, [((1, 2), "h got (1, 2)")])


def test_one_element_tuple_argument_alone(model):
    """Only h((1,)) stored: values() and items() ran h(1), stored it,
    and raised RuntimeError."""
    h = model.S.h
    h((1,))
    check_views(model, h, [((1,), "h got (1,)")])
    assert not h.node(1).has_value()
    assert (1, "h got 1") not in h.items()
    assert "h got 1" not in h.values()


def test_one_element_tuple_argument_and_bare_argument(model):
    """h((1,)) and h(1) stored: values() and items() gave h(1)'s value
    for the key (1,)."""
    h = model.S.h
    h((1,))
    h(1)
    check_views(model, h, [((1,), "h got (1,)"), (1, "h got 1")])
    assert ((1,), "h got 1") not in h.items()


def test_items_contains_runs_no_formula_for_a_key_not_stored(model):
    """``(key, value) in cells.items()`` read ``cells[key]``, which ran
    the formula when nothing was stored for the key."""
    h = model.S.h
    h(1)
    before = state(model)
    assert (2, "h got 2") not in h.items()
    assert ((2,), "h got 2") not in h.items()
    assert ((3, 4), "h got (3, 4)") not in h.items()
    assert state(model) == before
    assert list(h) == [1]


# --------------------------------------------------------------------------
# Signatures


def test_one_parameter(model):
    h = model.S.h
    for arg in [1, (1, 2), (1,), "a", ()]:
        h(arg)
    check_views(model, h, [(arg, "h got " + repr(arg))
                           for arg in [1, (1, 2), (1,), "a", ()]])
    for key, value in h.items():
        assert h.node(*node_args(h, key)).value == value


def test_no_parameters(model):
    z = model.S.z
    check_views(model, z, [])
    z()
    check_views(model, z, [((), 42)])


def test_two_parameters(model):
    two = model.S.two
    two(1, 2)
    two((1, 2), 3)
    two(y=4, x=5)
    check_views(model, two, [
        ((1, 2), 2), (((1, 2), 3), (1, 2, 1, 2, 1, 2)), ((5, 4), 20)])
    for key, value in two.items():
        assert two.node(*node_args(two, key)).value == value


def test_defaults_are_stored_and_not_applied_by_in(model):
    """Keys hold the bound defaults; ``(key, value) in items()``, like
    ``key in cells``, applies none."""
    g, one_def = model.S.g, model.S.one_def
    g(1)
    g(2, 5)
    one_def()
    check_views(model, g, [((1, 1), (1, 1)), ((2, 5), (2, 5))])
    check_views(model, one_def, [(0, 0)])

    before = state(model)
    assert ((1,), (1, 1)) not in g.items()
    assert (1, (1, 1)) not in g.items()
    assert ((), 0) not in one_def.items()
    assert state(model) == before


def test_var_positional(model):
    """A Cells whose only parameter is ``*args`` has one parameter, so
    iter() yields the stored tuple of arguments, and items() gives the
    same keys. a_va(a, *args): values() and items() ran the formula and
    raised RuntimeError."""
    va, a_va = model.S.va, model.S.a_va
    va_values = [va(), va(1), va(1, 2)]
    a_va_values = [a_va(1), a_va(1, 2)]

    check_views(model, va, list(zip(list(va), va_values)))
    check_views(model, a_va, list(zip(list(a_va), a_va_values)))


def test_uncached(model):
    """An uncached Cells stores nothing: its views are empty, and their
    ``in`` runs no formula, even for a key that cannot be stored."""
    u = model.S.u
    assert u(1) == 1
    check_views(model, u, [])

    before = state(model)
    assert (1, 1) not in u.items()
    assert ([1], [1]) not in u.items()
    assert 1 not in u.values()
    assert state(model) == before


def test_itemspace(model):
    """In an ItemSpace and in a DynamicSpace, as in a UserSpace."""
    h = model.S[1].h
    w = model.S[2].Child.w
    for arg in [(1, 2), (1,), 1]:
        h(arg)
        w(arg)
    check_views(model, h, [
        ((1, 2), "h got (1, 2)"), ((1,), "h got (1,)"), (1, "h got 1")])
    check_views(model, w, [
        ((1, 2), ("w", (1, 2))), ((1,), ("w", (1,))), (1, ("w", 1))])


# --------------------------------------------------------------------------
# Dependencies


def test_reads_in_a_formula_record_dependencies(model):
    """Inside a formula, a Cells name is the bound CellsImpl.call, but a
    Reference to a Cells is the Cells itself. values() and items() read
    through it record an edge from each node they read, as cells[key]
    did, so the formula is cleared when one of those values changes."""
    s = model.S
    s.r = s.h
    s.new_cells("vals", formula=lambda: list(r.values()))
    s.new_cells("pairs", formula=lambda: list(r.items()))
    h = s.h
    h((1, 2))
    h(3)

    assert s.vals() == ["h got (1, 2)", "h got 3"]
    assert s.pairs() == [((1, 2), "h got (1, 2)"), (3, "h got 3")]
    for name in ["vals", "pairs"]:
        preds = s.cells[name].node().preds
        assert [(p.obj.name, p.args) for p in preds] == [
            ("h", ((1, 2),)), ("h", (3,))]

    h[((1, 2),)] = "input"     # h[(1, 2)] = ... would raise TypeError
    assert not s.vals.node().has_value()
    assert not s.pairs.node().has_value()
    # A replaced value is stored again, so it comes last.
    assert s.vals() == ["h got 3", "input"]
    assert s.pairs() == [(3, "h got 3"), ((1, 2), "input")]
