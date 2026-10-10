"""Behaviour contracts on existing calls that tools rely on.

Section 3.5 of devnotes/ToolAPIDesign.md states contracts on calls that
modelx-bridge, modelx-mcp and spyder-modelx make today, and section 6
(PR 1, "Tests") asks for each to be pinned by a test, together with the
recipes that let a tool compute on modelx 0.33 what later releases will
answer directly.  Every test here pins behaviour of this release;
nothing in this module needs a member that does not exist yet.

* C1(1): ``len(Model.tracegraph)`` counts the stored values of every
  cached Cells, those inside ItemSpaces included, plus one per
  ItemSpace, and the public walk over Spaces, ``_named_itemspaces``,
  Cells and ``node(*args).preds`` gives the same links as the graph.
  The counts measured on lifelib's BasicTerm_S are checked only on the
  copy of the model they were measured on.
* C1(2): the Cells members that never run a formula, on stored values,
  on absent values and on Cells that hold no value, checked by the
  trace graph and by counting formula runs.
* C1(4): under ``use_formula_error(False)`` the exception a caller
  catches is ``mx.get_error()``; a call refused before any formula runs
  leaves ``get_error()`` and ``get_traceback()`` as they were.
* C2(3): ``get_models()`` keeps returning the same Model object when a
  read or a new model displaces it to ``<name>_BAK<n>``, and across a
  rename.
* C2(6): ``get_object`` resolves a trailing attribute that is not a
  modelx object, such as ``'.cells'``.
* The 0.33 fallback recipes: resolving an ``_idtuple`` with
  ``node(*args).has_value()``/``.value``, which creates nothing, and the
  inheritance state of Cells and the scope of References computed from
  the tool API alone, against tables written out by hand.
* Frozen S1 and S2 members whose behaviour no other test checks:
  ``Model._get_from_name`` resolves every Space and Cells from its
  ``_idstr``, and ``_is_dynamic()``, ``_is_static()`` and ``_is_root()``
  tell the kinds of Space apart.

Each recipe is checked against the conftest inheritance fixture
(``cache_sample``) and ItemSpace fixture (``make_testmodel_for_clear``),
the serializer-compat fixture model, and a model built here with
multiple inheritance, overriding members, nested ItemSpaces and a Space
formula that returns ``refs`` and ``base``.
"""

import hashlib
import pathlib
import warnings

import pytest

import modelx as mx
from modelx.tests.testdata.serializer_compat import fixturemodel


# --------------------------------------------------------------------------
# Walks used by the contracts and recipes. They use the tool API only.

def iter_spaces(model):
    """Every Space of ``model``, depth first.

    Child Spaces through ``spaces``, and ItemSpaces through
    ``_named_itemspaces``, at every level, so the DynamicSpaces inside
    an ItemSpace and the ItemSpaces of those are included.
    """
    for space in model.spaces.values():
        yield from _iter_space(space)


def _iter_space(space):
    yield space
    for child in space.spaces.values():
        yield from _iter_space(child)
    for item in space._named_itemspaces.values():
        yield from _iter_space(item)


def iter_spaces_by_kind(model):
    """``(space, kind)`` for every Space of ``model``, as ``iter_spaces``.

    ``kind`` is how the walk reached the Space: ``'user'`` through
    ``spaces`` outside any ItemSpace, ``'item'`` through
    ``_named_itemspaces``, and ``'dynamic'`` through ``spaces`` inside
    an ItemSpace.
    """
    def walk(space, kind):
        yield space, kind
        for child in space.spaces.values():
            yield from walk(child, "user" if kind == "user" else "dynamic")
        for item in space._named_itemspaces.values():
            yield from walk(item, "item")

    for space in model.spaces.values():
        yield from walk(space, "user")


def iter_cells(model):
    for space in iter_spaces(model):
        yield from space.cells.values()


def count_itemspaces(model):
    return sum(len(s._named_itemspaces) for s in iter_spaces(model))


def count_values(model):
    return sum(len(c) for c in iter_cells(model))


def node_args(cells, key):
    """The arguments of a key from ``cells.keys()``.

    A Cells with one parameter keys its values by the argument itself,
    any other Cells by the tuple of arguments. Telling them apart by the
    number of parameters, not by ``isinstance(key, tuple)``, also reads
    a one-parameter Cells whose argument is a tuple.
    """
    return (key,) if len(cells.parameters) == 1 else key


def public_links(model):
    """Name pairs ``(precedent, dependent)`` of the Cells nodes in the
    trace graph, read through ``node(*args).preds`` (a property)."""
    links = set()
    for cells in iter_cells(model):
        for key in cells.keys():
            for pred in cells.node(*node_args(cells, key)).preds:
                if pred.obj.name != cells.name:
                    links.add((pred.obj.name, cells.name))
    return links


def graph_links(model):
    """The same pairs read from the trace graph's own nodes (internal)."""
    links = set()
    for u, v in model.tracegraph.edges():
        if u[0].name != v[0].name:
            links.add((u[0].name, v[0].name))
    return links


def model_key(obj):
    """``_evalrepr`` without the name of the Model, such as
    ``'Parent(1).Child'``."""
    return obj._evalrepr.partition(".")[2]


# --------------------------------------------------------------------------
# Fixtures

@pytest.fixture
def compat_model():
    """The serializer-compat fixture model, with the ItemSpace Params[3].

    It has a global Reference, a Reference that Sub overrides, and
    Cells and References that Sub inherits.
    """
    m = fixturemodel.build_fixture_model(name="ToolContractsCompat")
    m.Params[3]
    yield m
    m._impl._check_sanity()
    m.close()


@pytest.fixture
def inheritance_model():
    """
    ToolContractsInh---B0---k0, r0
                    |--B1(B0)---k0 (overrides B0.k0), k1, r1
                    |--B2---k2, r0
                    |--D(B1, B2)---k2 (overrides B2.k2), r1 (overrides B1.r1)
                    |--P[i, j=2]---h, k, rel     formula returns refs {'fr'}
                    |    +--Child[n]---w
                    |--Q[x]---D                  formula returns base D
                    +--glob = 7

    ItemSpaces: P[1, 2], P[1, 2].Child[3], Q[4]
    """
    m = mx.new_model("ToolContractsInh")
    b0 = m.new_space("B0")
    b0.new_cells("k0", formula=lambda: 0)
    b0.r0 = 0
    b1 = m.new_space("B1", bases=b0)
    b1.new_cells("k1", formula=lambda: 1)
    b1.k0.formula = lambda: 10
    b1.r1 = 1
    b2 = m.new_space("B2")
    b2.new_cells("k2", formula=lambda: 2)
    b2.r0 = 20
    d = m.new_space("D", bases=[b1, b2])
    d.r1 = 100
    d.k2.formula = lambda: 22
    m.glob = 7
    p = m.new_space("P", formula=lambda i, j=2: {"refs": {"fr": i * j}})
    p.new_cells("h", formula=lambda: i + fr + k)
    p.k = 5
    p.rel = None
    child = p.new_space("Child")
    child.parameters = ("n",)
    child.new_cells("w", formula=lambda: n + i)
    q = m.new_space("Q", formula=lambda x: {"base": D})
    q.D = d

    assert p[1].h() == 8
    assert p[1].Child[3].w() == 4
    assert q[4].k2() == 22

    yield m
    m._impl._check_sanity()
    m.close()


@pytest.fixture
def valued_model():
    """
    ToolContractsValues---S[i]---f(x), g(t, k=1), z(), r(), u(t) uncached,
                     |       |   e(), d(t=1)        never calculated
                     |       |   i = 0
                     |       +--Child[n]---w()
                     +--calls = []

    Every formula appends to the list in the global Reference ``calls``
    when it runs, so ``len(m.calls)`` counts the formula runs, including
    a run whose value is not stored.

    Values: S.f(1), S.f(2) and the input S.f[10]; S.g(1), S.g(2, 3); S.z();
    S.r(); S[1].f(1), S[1].g(1); S.Child[7].w(); S[2].Child[8].w().
    ItemSpaces: S[1], S[2], S.Child[7], S[2].Child[8].
    """
    m = mx.new_model("ToolContractsValues")
    m.calls = []
    s = m.new_space("S", formula=lambda i: None)
    s.i = 0
    s.new_cells("f", formula=lambda x: calls.append("f") or 2 * x + i)
    s.new_cells("g", formula=lambda t, k=1: calls.append("g") or f(t) * k)
    s.new_cells("z", formula=lambda: calls.append("z") or 42)
    s.new_cells("r", formula=lambda: calls.append("r") or i)
    u = s.new_cells("u", formula=lambda t: calls.append("u") or t)
    u.is_cached = False
    s.new_cells("e", formula=lambda: calls.append("e") or 5)
    s.new_cells("d", formula=lambda t=1: calls.append("d") or t)
    child = s.new_space("Child", formula=lambda n: None)
    child.new_cells("w", formula=lambda: calls.append("w") or n)

    s.g(1)
    s.g(2, 3)
    s.z()
    s.r()
    s.f[10] = 7
    s[1].g(1)
    s.u(1)
    s[1].u(2)
    s.Child[7].w()
    s[2].Child[8].w()

    yield m
    m._impl._check_sanity()
    m.close()


INHERITANCE_FIXTURES = [
    "cache_sample",
    "make_testmodel_for_clear",
    "compat_model",
    "inheritance_model",
]


@pytest.fixture(params=INHERITANCE_FIXTURES)
def any_model(request):
    return request.param, request.getfixturevalue(request.param)


# --------------------------------------------------------------------------
# C1(1): what len(Model.tracegraph) counts

def test_tracegraph_len_counts_values_and_itemspaces(valued_model):
    """C1(1): ``len(Model.tracegraph)`` is the number of values held by
    cached Cells, inputs and values inside ItemSpaces included, plus one
    per ItemSpace. Uncached Cells and References add none."""
    m = valued_model
    s = m.S

    assert len(s.u) == 0 and len(s[1].u) == 0      # uncached: nothing held
    assert count_values(m) == 11
    assert count_itemspaces(m) == 4
    assert len(m.tracegraph) == count_values(m) + count_itemspaces(m) == 15

    # S[3].r() reads only the Reference i: the new ItemSpace and the value
    # of r are added, and nothing for the Reference.
    before = len(m.tracegraph)
    assert s[3].r() == 3
    assert len(m.tracegraph) == before + 2

    # Deleting S[2] removes it, its nested S[2].Child[8] and the value
    # inside that.
    del s[2]
    assert count_itemspaces(m) == 3
    assert len(m.tracegraph) == count_values(m) + count_itemspaces(m) == 14

    m.clear_all()
    assert len(m.tracegraph) == count_values(m) + count_itemspaces(m) == 0


def test_tracegraph_len_on_fixtures(any_model):
    """C1(1): the count holds on the inheritance and ItemSpace fixtures."""
    name, m = any_model
    if name == "cache_sample":
        assert m.Sub.baz(3) == 6       # values in inherited Cells
    assert len(m.tracegraph) == count_values(m) + count_itemspaces(m)
    assert len(m.tracegraph) > 0


def test_tracegraph_public_walk_links(valued_model):
    """C1(1): the public walk (Spaces through ``_named_itemspaces``, each
    Cells ``c`` and key ``k`` in ``c.keys()``, ``c.node(*args).preds``)
    finds the same links as the trace graph and evaluates nothing,
    including for a one-parameter Cells whose argument is a tuple."""
    m = valued_model
    assert public_links(m) == graph_links(m) == {("f", "g")}

    s = m.S
    s.new_cells("tp", formula=lambda a: f(a[0]))
    assert s.tp((1, 2)) == 2
    assert s.g(1) == 2      # new_cells may have cleared it
    assert list(s.tp.keys()) == [(1, 2)]
    before = len(m.tracegraph)
    assert public_links(m) == graph_links(m) == {("f", "g"), ("f", "tp")}
    assert len(m.tracegraph) == before


# The SHA-256 of the files of the BasicTerm_S that lifelib 0.17.2 creates,
# by model_digest(). The counts in test_tracegraph_on_basicterm_s were
# measured on it; lifelib's master branch at b706d8b has the same
# files. modelx's CI installs lifelib from that branch, so a later change
# to the model there changes the counts without any change in modelx.
BASICTERM_S_SHA256 = (
    "88e6b31d970846146e06d0625ef4a809ee28ad685727bff7ce2df6919fd1e7bf")


def model_digest(path):
    """SHA-256 of the files in a model folder, by their paths relative to
    it, with CRLF read as LF and ``__pycache__`` folders left out."""
    path = pathlib.Path(path)
    files = {}
    for file in path.rglob("*"):
        rel = file.relative_to(path)
        if file.is_file() and "__pycache__" not in rel.parts:
            files[rel.as_posix()] = file
    digest = hashlib.sha256()
    for rel in sorted(files):       # by str, the same on every platform
        digest.update(rel.encode("utf-8") + b"\0")
        digest.update(
            files[rel].read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()


def test_tracegraph_on_basicterm_s(tmp_path):
    """C1(1) on lifelib's BasicTerm_S: after ``pv_net_cf()`` and
    ``Projection[2].pv_net_cf()`` the graph holds the values in
    Projection and Projection[2] and the ItemSpace itself; after the
    workload of modelx-bridge's test_trace (``point_id = 1``,
    ``result_pv()``, ``result_cf()``) both walks agree with the graph.

    On the BasicTerm_S that the counts were measured on, the graph holds
    5,465 nodes, 1,832 values in Projection and 3,632 in Projection[2],
    and the public walk finds test_trace's 77 links. On another copy of
    the model only the invariants are checked."""
    lifelib = pytest.importorskip("lifelib")
    lifelib.create("basiclife", tmp_path / "basiclife")
    path = tmp_path / "basiclife" / "BasicTerm_S"
    measured = model_digest(path) == BASICTERM_S_SHA256
    if not measured:
        warnings.warn(
            "lifelib's BasicTerm_S is not the copy that the counts of"
            " test_tracegraph_on_basicterm_s were measured on (SHA-256 %s);"
            " only the invariants are checked" % model_digest(path))

    m = mx.read_model(path, name="ToolContractsBasicTermS")
    try:
        proj = m.Projection
        proj.pv_net_cf()
        proj[2].pv_net_cf()
        assert count_itemspaces(m) == 1
        assert len(m.tracegraph) == count_values(m) + 1
        assert public_links(m) == graph_links(m)
        if measured:
            assert sum(len(c) for c in proj.cells.values()) == 1832
            assert sum(len(c) for c in proj[2].cells.values()) == 3632
            assert len(m.tracegraph) == 5465
    finally:
        m.close()

    m = mx.read_model(path, name="ToolContractsBasicTermS")
    try:
        proj = m.Projection
        proj.point_id = 1
        proj.result_pv()
        proj.result_cf()
        links = public_links(m)
        assert links == graph_links(m)
        assert len(m.tracegraph) == count_values(m) + count_itemspaces(m)
        if measured:
            assert len(links) == 77
    finally:
        m.close()


# --------------------------------------------------------------------------
# C1(2): Cells members that never evaluate

def state(model):
    """What a read that evaluates would change: the number of nodes in
    the trace graph and the number of formula runs (the valued fixture's
    ``calls``)."""
    return len(model.tracegraph), len(model.calls)


def non_evaluating_reads(cells, key):
    """The members C1(2) lists, for a ``key`` that ``cells`` holds."""
    args = node_args(cells, key)
    return [
        ("len", lambda: len(cells)),
        ("iter", lambda: list(iter(cells))),
        ("keys", lambda: list(cells.keys())),
        ("in", lambda: key in cells),
        ("values", lambda: list(cells.values())),
        ("items", lambda: list(cells.items())),
        ("series", lambda: cells.series),
        ("frame", lambda: cells.frame),
        ("to_series()", lambda: cells.to_series()),
        ("to_frame()", lambda: cells.to_frame()),
        ("node.has_value", lambda: cells.node(*args).has_value()),
        ("node.value", lambda: cells.node(*args).value),
        ("is_input", lambda: cells.is_input(*args)),
        # Also listed as non-evaluating on cells.rst.
        ("preds", lambda: cells.preds(*args)),
        ("succs", lambda: cells.succs(*args)),
        ("precedents", lambda: cells.precedents(*args)),
        # The C1(1) walk reads these.
        ("node.preds", lambda: cells.node(*args).preds),
        ("node.succs", lambda: cells.node(*args).succs),
        ("node.precedents", lambda: cells.node(*args).precedents),
    ]


VALUED_CELLS = {
    "S.f": lambda m: m.S.f,
    "S.g": lambda m: m.S.g,
    "S.z": lambda m: m.S.z,
    "S[1].f": lambda m: m.S[1].f,
    "S[1].g": lambda m: m.S[1].g,
    "S.Child[7].w": lambda m: m.S.Child[7].w,
    "S[2].Child[8].w": lambda m: m.S[2].Child[8].w,
}


@pytest.mark.parametrize("cellsname", list(VALUED_CELLS))
def test_cells_reads_never_evaluate(valued_model, cellsname):
    """C1(2): ``len``, ``iter``, ``keys``, ``in``, ``values()``,
    ``items()``, ``series``, ``frame``, ``to_series()`` and ``to_frame()``
    without arguments, ``node(*a).has_value()``, ``node(*a).value`` and
    ``is_input``, and ``preds``, ``succs`` and ``precedents``, which
    cells.rst also lists, run no formula and leave
    ``len(model.tracegraph)`` unchanged."""
    m = valued_model
    cells = VALUED_CELLS[cellsname](m)
    keys = list(cells.keys())
    assert keys
    for key in keys:
        for label, read in non_evaluating_reads(cells, key):
            before = state(m)
            read()
            assert state(m) == before, (cellsname, key, label)
    assert len(m.tracegraph) == count_values(m) + count_itemspaces(m)


EMPTY_CELLS = {
    "S.e": lambda m: m.S.e,        # no parameters
    "S.d": lambda m: m.S.d,        # d(t=1): every parameter has a default
    "S[1].e": lambda m: m.S[1].e,
    "S[1].d": lambda m: m.S[1].d,
}


@pytest.mark.parametrize("cellsname", list(EMPTY_CELLS))
def test_cells_reads_of_empty_cells(valued_model, cellsname):
    """C1(2) on a Cells that holds no value and that can be called
    without arguments, where a read that evaluated would have a value to
    calculate: the reads without arguments run no formula and store
    nothing, and those that need a stored value raise ValueError."""
    m = valued_model
    cells = EMPTY_CELLS[cellsname](m)
    assert len(cells) == 0

    reads = [
        ("len", lambda: len(cells)),
        ("iter", lambda: list(iter(cells))),
        ("keys", lambda: list(cells.keys())),
        ("in", lambda: () in cells),
        ("values", lambda: list(cells.values())),
        ("items", lambda: list(cells.items())),
        ("series", lambda: cells.series),
        ("frame", lambda: cells.frame),
        ("to_series()", lambda: cells.to_series()),
        ("to_frame()", lambda: cells.to_frame()),
        ("node.has_value", lambda: cells.node().has_value()),
    ]
    for label, read in reads:
        before = state(m)
        read()
        assert state(m) == before, (cellsname, label)

    raising = [
        ("node.value", lambda: cells.node().value),
        ("is_input", lambda: cells.is_input()),
        ("preds", lambda: cells.preds()),
        ("succs", lambda: cells.succs()),
        ("precedents", lambda: cells.precedents()),
        ("node.preds", lambda: cells.node().preds),
        ("node.succs", lambda: cells.node().succs),
        ("node.precedents", lambda: cells.node().precedents),
    ]
    for label, read in raising:
        before = state(m)
        with pytest.raises(ValueError):
            read()
        assert state(m) == before, (cellsname, label)

    assert len(cells) == 0 and not cells.node().has_value()


def test_cells_reads_of_absent_values(valued_model):
    """C1(2): reads of a value that is not stored evaluate nothing.
    ``in`` applies no defaults; ``node(*a).value``, ``is_input``,
    ``preds``, ``succs`` and ``precedents``, and the node's ``preds``,
    ``succs`` and ``precedents``, raise ValueError; and "is it cached" is
    ``node(*args).has_value()`` for Cells and Spaces alike: ``in`` on a
    Space tests member names."""
    m = valued_model
    s = m.S
    before = state(m)

    assert list(s.f.keys()) == [1, 2, 10]          # one parameter: bare keys
    assert list(s.g.keys()) == [(1, 1), (2, 3)]    # defaults bound
    assert list(s.z.keys()) == [()]

    assert (1, 1) in s.g
    assert (1,) not in s.g                         # no default applied
    assert 5 not in s.f
    assert not s.f.node(5).has_value()
    assert not s.g.node(5).has_value()             # g(5, 1) is not stored
    assert s.f.is_input(10) and not s.f.is_input(1)

    raising = [
        ("node.value", lambda c, *a: c.node(*a).value),
        ("is_input", lambda c, *a: c.is_input(*a)),
        ("preds", lambda c, *a: c.preds(*a)),
        ("succs", lambda c, *a: c.succs(*a)),
        ("precedents", lambda c, *a: c.precedents(*a)),
        ("node.preds", lambda c, *a: c.node(*a).preds),
        ("node.succs", lambda c, *a: c.node(*a).succs),
        ("node.precedents", lambda c, *a: c.node(*a).precedents),
    ]
    for cells, args in [(s.f, (5,)), (s.g, (5,)), (s[1].f, (5,))]:
        for label, read in raising:
            with pytest.raises(ValueError):
                read(cells, *args)
            assert state(m) == before, (cells, args, label)
        assert args not in cells and args[0] not in cells

    assert s.node(1).has_value()
    assert s.node(1).value is s[1]
    assert not s.node(9).has_value()
    assert 1 not in s and (1,) not in s            # member names only

    assert state(m) == before


def test_cells_members_that_evaluate(valued_model):
    """C1(2): ``[]``, ``get``, a call, ``to_series``/``to_frame`` with
    arguments, ``match`` and ``value`` run the formula for a value that
    is not stored, and store it."""
    m = valued_model
    s = m.S
    f = s.f
    f.allow_none = True        # match needs it
    graph = m.tracegraph

    evaluating = [
        (lambda: f[20], 20),
        (lambda: f.get(21), 21),
        (lambda: f(22), 22),
        (lambda: f.to_series([23]), 23),
        (lambda: f.to_frame([24]), 24),
        (lambda: f.match(25), 25),
    ]
    for run, key in evaluating:
        before = len(graph)
        assert key not in f
        run()
        assert key in f
        assert len(graph) == before + 1

    del s.z.value
    before = len(graph)
    assert s.z.value == 42
    assert len(graph) == before + 1


# --------------------------------------------------------------------------
# C1(4): get_error() and get_traceback() under use_formula_error(False)

@pytest.fixture
def formula_error_off():
    orig = mx.use_formula_error()
    mx.use_formula_error(False)
    try:
        yield
    finally:
        mx.use_formula_error(orig)


@pytest.fixture
def error_model():
    m = mx.new_model("ToolContractsErrors")
    s = m.new_space("S")
    s.new_cells("f", formula=lambda x: f(x - 1) if x > 0 else 1 / 0)
    s.new_cells("t", formula=lambda x: x + "a")
    s.new_cells("ok", formula=lambda x: x)
    yield m
    m.close()


def frames(traceback):
    # By name: Cells.__eq__ evaluates a Cells without parameters and
    # raises TypeError against anything but a Cells.
    return [(node.obj._idstr, node.args, line) for node, line in traceback]


def test_formula_error_off_caught_is_get_error(error_model, formula_error_off):
    """C1(4): under ``use_formula_error(False)`` the exception the caller
    catches is ``mx.get_error()``, ``get_traceback()`` describes it, and a
    call refused before any formula runs leaves both as they were."""
    s = error_model.S
    f = s.f

    with pytest.raises(ZeroDivisionError) as excinfo:
        f(5)
    exc = excinfo.value
    assert exc is mx.get_error()
    tb = frames(mx.get_traceback())
    assert tb == [("S.f", (x,), 1) for x in (5, 4, 3, 2, 1, 0)]

    refused = [
        lambda: f(1, 2),
        lambda: f(),
        lambda: f(x=1, y=2),
        lambda: f[1, 2],
    ]
    for call in refused:
        with pytest.raises(TypeError) as refusal:
            call()
        assert refusal.value is not mx.get_error()
        assert mx.get_error() is exc
        assert frames(mx.get_traceback()) == tb

    # A TypeError raised inside a formula is the formula's own error.
    with pytest.raises(TypeError) as inside:
        s.t(1)
    assert inside.value is mx.get_error()
    assert frames(mx.get_traceback()) == [("S.t", (1,), 1)]

    # The next top-level run resets both.
    assert s.ok(1) == 1
    assert mx.get_error() is None
    assert mx.get_traceback() == []


# --------------------------------------------------------------------------
# C2(3): get_models() identity across displacement and rename

@pytest.fixture
def close_new_models():
    before = set(mx.get_models().values())
    yield
    for model in list(mx.get_models().values()):
        if model not in before:
            model.close()


def test_get_models_identity_across_bak(tmp_path, close_new_models):
    """C2(3): ``get_models()`` returns the same Model object each time.
    A model displaced to ``<name>_BAK<n>`` by ``read_model`` or
    ``new_model`` of its name stays the same object under its new name,
    and so does a renamed model."""
    name = "ToolContractsDup"
    m1 = mx.new_model(name)
    m1.new_space("S").x = 1
    m1.write(tmp_path / name)
    assert mx.get_models()[name] is m1
    assert mx.get_models()[name] is mx.get_models()[name]

    with pytest.warns(UserWarning, match="renamed to"):
        m2 = mx.read_model(tmp_path / name)
    models = mx.get_models()
    assert m2 is not m1
    assert models[name] is m2
    assert m1.name.startswith(name + "_BAK")
    assert models[m1.name] is m1
    assert [v for v in models.values() if v is m1] == [m1]
    assert m1._is_valid() and m1.S.x == 1

    with pytest.warns(UserWarning, match="renamed to"):
        m3 = mx.new_model(name)
    models = mx.get_models()
    assert models[name] is m3
    assert m2.name.startswith(name + "_BAK") and models[m2.name] is m2
    assert models[m1.name] is m1

    m3.rename("ToolContractsRenamed")
    models = mx.get_models()
    assert models["ToolContractsRenamed"] is m3
    assert name not in models


# --------------------------------------------------------------------------
# C2(6): get_object's leaf path

def same_members(view, other):
    """Same names and the same objects. Compared by identity, because
    Cells.__eq__ evaluates a Cells without parameters and raises
    TypeError against anything but a Cells."""
    return (list(view) == list(other)
            and all(view[name] is other[name] for name in view))


def test_get_object_leaf_path():
    """C2(6): ``get_object`` resolves a trailing attribute that is not a
    modelx object: ``'M.S.cells'`` gives the Space's CellsView, as
    ``_get_object`` documents for spyder-modelx."""
    m = mx.new_model("ToolContractsLeaf")
    try:
        s = m.new_space("S", formula=lambda i: None)
        foo = s.new_cells("foo", formula=lambda x: 2 * x)
        s.new_space("Child")
        s.k = 5
        item = s[1]
        graph = m.tracegraph
        before = len(graph)

        for space in (s, item, item.Child):
            cells = mx.get_object(space.fullname + ".cells")
            assert type(cells) is type(space.cells)
            assert same_members(cells, space.cells)
            assert same_members(mx.get_object(space.fullname + ".spaces"),
                                space.spaces)
            assert same_members(
                m._get_object(space.fullname.partition(".")[2] + ".cells"),
                space.cells)

        assert same_members(mx.get_object("ToolContractsLeaf.S.cells"),
                            {"foo": foo})
        assert mx.get_object(foo.fullname + ".formula") is foo.formula
        assert mx.get_object(item.foo.fullname + ".formula") is foo.formula
        assert mx.get_object(foo.fullname + ".parameters") == ("x",)
        assert dict(mx.get_object("ToolContractsLeaf.S.refs"))["k"] == 5
        assert len(graph) == before
    finally:
        m.close()


# --------------------------------------------------------------------------
# 0.33 fallback recipe: the _idtuple walk

def resolve_idtuple(idtuple, as_proxy=False):
    """Resolve an ``_idtuple`` without creating an ItemSpace.

    A tuple segment holds the arguments of an ItemSpace, which is found
    with ``node(*args).has_value()`` and ``node(*args).value`` of the
    Space before it. Returns None on a miss.
    """
    models = mx.get_models()
    if idtuple[0] not in models:
        return None
    obj = models[idtuple[0]]
    rest = list(idtuple[1:])
    while rest:
        segment = rest.pop(0)
        if isinstance(segment, tuple):
            node = obj.node(*segment)
            if not node.has_value():
                return None
            obj = node.value
        else:
            obj = obj._get_object(segment, as_proxy=as_proxy and not rest)
    return obj


def all_reference_proxies(model):
    """A proxy for each name in the ``refs`` of the Model and of each
    Space, except ``__builtins__``."""
    proxies = [model._get_object(n, as_proxy=True)
               for n in model.refs if n != "__builtins__"]
    for space in iter_spaces(model):
        proxies.extend(space._get_object(n, as_proxy=True)
                       for n in space.refs if n != "__builtins__")
    return proxies


def test_idtuple_walk(any_model):
    """0.33 fallback (design minimal/m03): every Model, Space, ItemSpace,
    DynamicSpace, Cells and Reference resolves back from its ``_idtuple``
    through ``node(*args).has_value()``/``.value``, and the walk creates
    no ItemSpace and no value."""
    name, m = any_model
    nodes, items = len(m.tracegraph), count_itemspaces(m)

    objects = [m] + list(iter_spaces(m)) + list(iter_cells(m))
    for obj in objects:
        assert resolve_idtuple(obj._idtuple) is obj, obj

    for proxy in all_reference_proxies(m):
        found = resolve_idtuple(proxy._idtuple, as_proxy=True)
        assert found._idstr == proxy._idstr, proxy
        assert found.parent is proxy.parent, proxy
        assert found.value is proxy.value, proxy

    assert (len(m.tracegraph), count_itemspaces(m)) == (nodes, items)


def test_idtuple_walk_misses_create_nothing(inheritance_model):
    """0.33 fallback (design minimal/m03): an ``_idtuple`` naming an
    ItemSpace that does not exist resolves to nothing and creates
    nothing. An ItemSpace contributes its arguments, defaults bound, and
    a nested item each level's."""
    m = inheritance_model
    nodes, items = len(m.tracegraph), count_itemspaces(m)

    assert m.P[1]._idtuple == ("ToolContractsInh", "P", (1, 2))
    assert m.P[1].Child[3]._idtuple == (
        "ToolContractsInh", "P", (1, 2), "Child", (3,))
    assert resolve_idtuple(("ToolContractsInh", "P", (9, 2))) is None
    assert resolve_idtuple(
        ("ToolContractsInh", "P", (1, 2), "Child", (4,))) is None
    assert resolve_idtuple(("ToolContractsInh", "Q", (5,), "k2")) is None

    assert (len(m.tracegraph), count_itemspaces(m)) == (nodes, items)


# --------------------------------------------------------------------------
# 0.33 fallback recipes: inheritance state of Cells, scope of References

def static_space(space):
    """The static Space whose members ``space`` has: ``space`` itself, or
    for an ItemSpace or a DynamicSpace its only base."""
    return space.bases[0] if space._is_dynamic() else space


def member_is_derived(obj):
    """``_is_derived()`` where the class defines it (Cells); the 0.33
    ``is_derived()`` of a ReferenceProxy otherwise."""
    if getattr(type(obj), "_is_derived", None) is not None:
        return obj._is_derived()
    return obj.is_derived()


def member_state(static, name, members):
    """``(state, defined_in)`` of member ``name`` of a static Space.

    ``members(space)`` maps names to members of one kind. ``state`` is
    'derived' (inherited), 'overriding' (defined here and in a base) or
    'defined'. ``defined_in`` is the Space whose definition is in use:
    the Space itself, or the first base in ``bases`` (the MRO) whose
    member is not derived.
    """
    if member_is_derived(members(static)[name]):
        for base in static.bases:
            found = members(base)
            if name in found and not member_is_derived(found[name]):
                return "derived", base
        return "derived", None
    if any(name in members(base) for base in static.bases):
        return "overriding", static
    return "defined", static


def own_ref_proxies(space):
    return {n: space._get_object(n, as_proxy=True) for n in space._own_refs}


def argument_names(space):
    """Names of the ItemSpace arguments a dynamic Space sees: those of
    each ItemSpace from ``space`` up, from its parent's ``parameters``."""
    names = []
    while space._is_dynamic():
        if space._is_root():
            names.extend(n for n in space.parent.parameters
                         if n not in names)
        space = space.parent
    return names


def cells_recipe(space):
    static = static_space(space)
    return {name: member_state(static, name, lambda s: s.cells)
            for name in space.cells}


def refs_recipe(space):
    """``{name: (scope, state, defined_in)}`` for each name in ``refs``.

    Scope is 'argument', 'formula' (a ref the Space formula returned),
    'base' (a Reference of the static Space, seen in a dynamic one),
    'space', 'global' or 'builtins', in the order a name is looked up.
    """
    static = static_space(space)
    dynamic = space._is_dynamic()
    args = argument_names(space) if dynamic else []
    result = {}
    for name in space.refs:
        if name == "__builtins__":
            result[name] = ("builtins", None, None)
        elif name in args:
            result[name] = ("argument", None, None)
        elif name in space._own_refs:
            if dynamic:
                result[name] = ("formula", None, None)
            else:
                result[name] = ("space",) + member_state(
                    static, name, own_ref_proxies)
        elif dynamic and name in static._own_refs:
            result[name] = ("base",) + member_state(
                static, name, own_ref_proxies)
        else:
            assert name in space.model.refs
            result[name] = ("global", None, space.model)
    return result


def by_idstr(table):
    """Replace each Space or Model in a recipe table by its ``_idstr``."""
    return {
        name: tuple(v._idstr if hasattr(v, "_idstr") else v for v in row)
        for name, row in table.items()
    }


B, G = ("builtins", None, None), ("global", None, "")

EXPECTED_CELLS = {
    "cache_sample": {
        "Base": {"foo": ("defined", "Base"), "bar": ("defined", "Base"),
                 "baz": ("defined", "Base")},
        "Sub": {"foo": ("derived", "Base"), "bar": ("derived", "Base"),
                "baz": ("derived", "Base")},
    },
    "make_testmodel_for_clear": {
        "Parent": {"Foo": ("defined", "Parent")},
        "Parent.Child": {"Bar": ("defined", "Parent.Child")},
        "Parent.Child(1)": {"Bar": ("defined", "Parent.Child")},
        "Parent(1)": {"Foo": ("defined", "Parent")},
        "Parent(1).Child": {"Bar": ("defined", "Parent.Child")},
    },
    "compat_model": {
        "Base": {"foo": ("defined", "Base"), "bar": ("defined", "Base")},
        "Base.Child": {"baz": ("defined", "Base.Child")},
        "Sub": {"foo": ("derived", "Base"), "bar": ("derived", "Base")},
        "Params": {"qux": ("defined", "Params")},
        "Params(3)": {"qux": ("defined", "Params")},
    },
    "inheritance_model": {
        "B0": {"k0": ("defined", "B0")},
        "B1": {"k0": ("overriding", "B1"), "k1": ("defined", "B1")},
        "B2": {"k2": ("defined", "B2")},
        "D": {"k0": ("derived", "B1"), "k1": ("derived", "B1"),
              "k2": ("overriding", "D")},
        "P": {"h": ("defined", "P")},
        "P.Child": {"w": ("defined", "P.Child")},
        "P(1, 2)": {"h": ("defined", "P")},
        "P(1, 2).Child": {"w": ("defined", "P.Child")},
        "P(1, 2).Child(3)": {"w": ("defined", "P.Child")},
        "Q": {},
        "Q(4)": {"k0": ("derived", "B1"), "k1": ("derived", "B1"),
                 "k2": ("overriding", "D")},
    },
}

_COMPAT_BASE_REFS = ("m", "self_space", "the_model", "the_cells",
                     "s", "lst", "dct", "tpl")

EXPECTED_REFS = {
    "cache_sample": {"Base": {"__builtins__": B}, "Sub": {"__builtins__": B}},
    "make_testmodel_for_clear": {
        "Parent": {"__builtins__": B},
        "Parent.Child": {"__builtins__": B},
        "Parent.Child(1)": {"__builtins__": B,
                            "n": ("argument", None, None)},
        "Parent(1)": {"__builtins__": B, "a": ("argument", None, None)},
        "Parent(1).Child": {"__builtins__": B,
                            "a": ("argument", None, None)},
    },
    "compat_model": {
        "Base": dict({"__builtins__": B, "gref": G},
                     **{n: ("space", "defined", "Base")
                        for n in _COMPAT_BASE_REFS}),
        "Base.Child": {"__builtins__": B, "gref": G},
        "Sub": dict({"__builtins__": B, "gref": G},
                    **{n: ("space", "derived", "Base")
                       for n in _COMPAT_BASE_REFS if n != "m"},
                    m=("space", "overriding", "Sub")),
        "Params": {"__builtins__": B, "gref": G},
        "Params(3)": {"__builtins__": B, "gref": G,
                      "i": ("argument", None, None)},
    },
    "inheritance_model": {
        "B0": {"__builtins__": B, "glob": G,
               "r0": ("space", "defined", "B0")},
        "B1": {"__builtins__": B, "glob": G,
               "r0": ("space", "derived", "B0"),
               "r1": ("space", "defined", "B1")},
        "B2": {"__builtins__": B, "glob": G,
               "r0": ("space", "defined", "B2")},
        "D": {"__builtins__": B, "glob": G,
              "r0": ("space", "derived", "B0"),
              "r1": ("space", "overriding", "D")},
        "P": {"__builtins__": B, "glob": G,
              "k": ("space", "defined", "P"),
              "rel": ("space", "defined", "P")},
        "P.Child": {"__builtins__": B, "glob": G},
        "P(1, 2)": {"__builtins__": B, "glob": G,
                    "i": ("argument", None, None),
                    "j": ("argument", None, None),
                    "fr": ("formula", None, None),
                    "k": ("base", "defined", "P"),
                    "rel": ("base", "defined", "P")},
        "P(1, 2).Child": {"__builtins__": B, "glob": G,
                          "i": ("argument", None, None),
                          "j": ("argument", None, None)},
        "P(1, 2).Child(3)": {"__builtins__": B, "glob": G,
                             "i": ("argument", None, None),
                             "j": ("argument", None, None),
                             "n": ("argument", None, None)},
        "Q": {"__builtins__": B, "glob": G,
              "D": ("space", "defined", "Q")},
        "Q(4)": {"__builtins__": B, "glob": G,
                 "x": ("argument", None, None),
                 "r0": ("base", "derived", "B0"),
                 "r1": ("base", "overriding", "D")},
    },
}


def test_cells_state_recipe(any_model):
    """0.33 fallback (design minimal/m06): the state of every Cells,
    'defined', 'overriding' or 'derived', and the Space whose definition
    is in use, computed from ``_is_derived()``, ``bases`` and ``cells``;
    a dynamic Space reports its static Space's states."""
    name, m = any_model
    got = {model_key(s): by_idstr(cells_recipe(s)) for s in iter_spaces(m)}
    assert got == EXPECTED_CELLS[name]


def test_ref_scope_recipe(any_model):
    """0.33 fallback (design minimal/m06): the scope of every name in a
    Space's ``refs``, and the state of the Space's own References,
    computed from ``refs``, ``_own_refs``, ``bases``, ``parameters``,
    ``_is_dynamic()``, ``_is_root()`` and ``is_derived()``. A ref that a
    Space formula returns is in the ItemSpace's ``_own_refs``."""
    name, m = any_model
    got = {model_key(s): by_idstr(refs_recipe(s)) for s in iter_spaces(m)}
    assert got == EXPECTED_REFS[name]


def test_cells_dynamic_recipe(any_model):
    """0.33 fallback (design T2, minimal/m06): a Cells is dynamic exactly
    when its parent Space's ``_is_dynamic()`` is True, that is, when it
    is in an ItemSpace or in a DynamicSpace inside one, and a dynamic
    Cells is derived."""
    name, m = any_model
    seen = 0
    for space, kind in iter_spaces_by_kind(m):
        for c in space.cells.values():
            seen += 1
            assert c.parent is space
            assert c.parent._is_dynamic() is (kind != "user"), c
            if kind != "user":
                assert c._is_derived(), c
    assert seen


# --------------------------------------------------------------------------
# S1 and S2 members whose signatures alone the surface golden pins

def test_space_kind_flags(any_model):
    """``_is_dynamic()`` is True for an ItemSpace and a DynamicSpace and
    False for a UserSpace, ``_is_static()`` is always its negation, and
    ``_is_root()`` is True only for an ItemSpace, including an ItemSpace
    of a DynamicSpace."""
    name, m = any_model
    kinds = list(iter_spaces_by_kind(m))
    assert kinds
    for space, kind in kinds:
        assert space._is_dynamic() is (kind != "user"), space
        assert space._is_static() is (not space._is_dynamic()), space
        assert space._is_root() is (kind == "item"), space


def test_get_from_name_round_trip(any_model):
    """``model._get_from_name(obj._idstr) is obj`` for every UserSpace,
    ItemSpace (by its ``__SpaceN`` name), DynamicSpace and Cells, and the
    lookup creates nothing. A first part that is not a Space of the
    Model, such as ``''`` or the name of a global Reference, raises
    KeyError."""
    name, m = any_model
    nodes, items = len(m.tracegraph), count_itemspaces(m)

    objects = list(iter_spaces(m)) + list(iter_cells(m))
    assert objects
    for obj in objects:
        assert m._get_from_name(obj._idstr) is obj, obj

    for missing in [""] + list(m.refs):
        with pytest.raises(KeyError):
            m._get_from_name(missing)

    assert (len(m.tracegraph), count_itemspaces(m)) == (nodes, items)


def test_get_from_name_references(inheritance_model):
    """A last part that names a Reference gives its value, in a Space
    and in an ItemSpace, arguments and formula refs included."""
    m = inheritance_model
    item = m.P[1]
    assert m._get_from_name("P.k") == 5
    assert m._get_from_name(item._idstr + ".k") == 5
    assert m._get_from_name(item._idstr + ".i") == 1
    assert m._get_from_name(item._idstr + ".j") == 2
    assert m._get_from_name(item._idstr + ".fr") == 2
    assert m._get_from_name("Q.D") is m.D
