"""Tests for the all-positional fast path in ``get_node``.

``modelx.core.execution.trace.get_node`` short-circuits
``Signature.bind()`` for the all-positional call, which is how virtually
every intra-formula cells reference arrives.  The shortcut must produce
byte-for-byte the key ``_bind_args`` would produce: a disagreement is not
a crash but a silently wrong cache key, so the tests below check the keys
recorded in ``cells._impl.data`` and not only the returned values.
"""
import pickle
import re
import sys

import pytest

import modelx as mx
from modelx.core.execution.trace import get_node, _bind_args
from modelx.core.formula import Formula, NULL_FORMULA
from modelx.core.space import ParamFunc


_HAS_POSONLY = sys.version_info >= (3, 8)

posonly = pytest.mark.skipif(
    not _HAS_POSONLY, reason="positional-only parameters need Python 3.8+"
)


class StubTraceObject:
    """Stand-in for a TraceObject: ``get_node`` only reads ``formula``."""

    def __init__(self, formula):
        self.formula = formula


@pytest.fixture
def space():
    model = mx.new_model()
    yield model.new_space("Space")
    model._impl._check_sanity()
    model.close()


def keys(cells):
    """The set of trace keys ``cells`` has values for."""
    return set(cells._impl.data)


# ---------------------------------------------------------------------------
# Formula._bind_tails


@pytest.mark.parametrize(
    "src, expected",
    [
        ("def f(): pass", ((),)),
        ("def f(x): pass", (None, ())),
        ("def f(x, y, z): pass", (None, None, None, ())),
        ("def f(x=1): pass", ((1,), ())),
        ("def f(x, y=10, z=20): pass", (None, (10, 20), (20,), ())),
        ("def f(x, y, z=30): pass", (None, None, (30,), ())),
        # Kinds the shortcut cannot canonicalise the way bind() does
        ("def f(*args): pass", None),
        ("def f(x, *args): pass", None),
        ("def f(**kw): pass", None),
        ("def f(x, **kw): pass", None),
        ("def f(*, x): pass", None),
        ("def f(x, *, y): pass", None),
        ("def f(x, *, y=5): pass", None),
        ("def f(x, *args, **kw): pass", None),
    ],
)
def test_bind_tails(src, expected):
    assert Formula(src)._bind_tails == expected


@posonly
@pytest.mark.parametrize(
    "src, expected",
    [
        ("def f(x, /): pass", (None, ())),
        ("def f(x, /, y): pass", (None, None, ())),
        ("def f(x, y, /): pass", (None, None, ())),
        ("def f(x, /, y=2): pass", (None, (2,), ())),
        ("def f(x, y=2, /): pass", (None, (2,), ())),
    ],
)
def test_bind_tails_positional_only(src, expected):
    """POSITIONAL_ONLY binds exactly like POSITIONAL_OR_KEYWORD does."""
    assert Formula(src)._bind_tails == expected


def test_parameters_is_the_cached_tuple():
    formula = Formula("def f(x, y=10, z=20): pass")
    assert formula.parameters == ("x", "y", "z")
    assert formula.parameters == tuple(formula.signature.parameters)
    assert formula.parameters is formula.parameters


# ---------------------------------------------------------------------------
# The invariant: get_node() == (obj, _bind_args(obj, args, kwargs))


def _signature_sources():
    heads = [
        "",
        "a",
        "a, b",
        "a, b, c",
        "a=1",
        "a, b=2",
        "a, b=2, c=3",
        "a=1, b=2, c=3",
        "a, b, c=3",
    ]
    if _HAS_POSONLY:
        heads += [
            "a, /",
            "a, /, b",
            "a, b, /",
            "a, /, b=2",
            "a, b=2, /",
            "a, /, b, c=3",
        ]
    tails = [
        "",
        "*args",
        "**kw",
        "*, k",
        "*, k=9",
        "*args, **kw",
        "*args, k=9",
        "*args, k=9, **kw",
    ]
    srcs = []
    for head in heads:
        for tail in tails:
            params = ", ".join(p for p in (head, tail) if p)
            src = "def f(%s): pass" % params
            try:
                compile(src, "<sig>", "exec")
            except SyntaxError:
                continue
            srcs.append(src)
    return srcs


SIGNATURE_SOURCES = _signature_sources()

CALL_ARGS = [(), (1,), (1, 2), (1, 2, 3), (1, 2, 3, 4), [1, 2]]

# The values deliberately differ from the defaults declared in the
# generated signatures, so that a fast path wrongly accepting keyword
# arguments produces a visibly different key.
CALL_KWARGS = [
    None,
    {},
    {"a": 91},
    {"b": 92},
    {"a": 91, "b": 92, "c": 93},
    {"k": 99},
    {"zzz": 0},
]


def _outcome(func):
    """Return a comparable result-or-exception marker for ``func()``."""
    try:
        return ("value", func())
    except Exception as exc:      # noqa: BLE001 - the type is part of the result
        return ("raised", type(exc), str(exc))


def test_signature_sources_are_not_empty():
    # Guards against the generator silently degenerating to a handful of
    # shapes and the invariant test below testing nothing.
    assert len(SIGNATURE_SOURCES) > 60


@pytest.mark.parametrize("src", SIGNATURE_SOURCES)
def test_get_node_agrees_with_bind_args(src):
    """The fast path must never disagree with the slow path it bypasses."""
    obj = StubTraceObject(Formula(src))

    for args in CALL_ARGS:
        for kwargs in CALL_KWARGS:
            slow = _outcome(
                lambda a=args, k=kwargs: (
                    obj, _bind_args(obj, a, {} if k is None else k))
            )
            fast = _outcome(lambda a=args, k=kwargs: get_node(obj, a, k))
            assert fast == slow, "%s with args=%r kwargs=%r" % (
                src, args, kwargs)


def test_get_node_with_no_args_returns_object_node():
    obj = StubTraceObject(Formula("def f(x): pass"))
    assert get_node(obj, None, None) == (obj,)


def test_get_node_without_formula_is_unchanged():
    """A formula-less object keeps raising on the slow path."""
    obj = StubTraceObject(None)
    with pytest.raises(AttributeError, match=re.escape(
            "'NoneType' object has no attribute 'signature'")):
        get_node(obj, (1,), None)


# ---------------------------------------------------------------------------
# Decision table, checked through real Cells (value *and* cache key)


def test_no_param(space):
    f = space.new_cells(name="f", formula="def f(): return 1")
    assert f() == 1
    assert keys(f) == {()}


def test_single_param_positional(space):
    f = space.new_cells(name="f", formula="def f(x): return x")
    assert f(1) == 1
    assert keys(f) == {(1,)}


def test_single_param_keyword_keys_the_same(space):
    f = space.new_cells(name="f", formula="def f(x): return x")
    assert f(x=1) == 1
    assert keys(f) == {(1,)}
    assert f(1) == 1
    assert keys(f) == {(1,)}


def test_mult_params_positional(space):
    f = space.new_cells(name="f", formula="def f(x, y, z): return (x, y, z)")
    assert f(1, 2, 3) == (1, 2, 3)
    assert keys(f) == {(1, 2, 3)}


def test_mult_params_keyword_orders_do_not_split_the_cache(space):
    f = space.new_cells(name="f", formula="def f(x, y, z): return (x, y, z)")
    assert f(1, 2, 3) == (1, 2, 3)
    assert f(z=3, x=1, y=2) == (1, 2, 3)      # out-of-order keywords
    assert f(1, 2, z=3) == (1, 2, 3)          # mixed
    assert keys(f) == {(1, 2, 3)}


def test_defaults_called_short_and_full(space):
    f = space.new_cells(
        name="f", formula="def f(x, y=10, z=20): return (x, y, z)")
    assert f(1) == (1, 10, 20)
    assert keys(f) == {(1, 10, 20)}
    assert f(1, 2, 3) == (1, 2, 3)
    assert keys(f) == {(1, 10, 20), (1, 2, 3)}
    # A short call and the equivalent full call share one entry
    assert f(1, 10, 20) == (1, 10, 20)
    assert keys(f) == {(1, 10, 20), (1, 2, 3)}


def test_keyword_overriding_a_default(space):
    """A keyword argument must beat the default, not the other way round."""
    f = space.new_cells(
        name="f", formula="def f(x, y=10): return (x, y)")
    assert f(1, y=99) == (1, 99)
    assert keys(f) == {(1, 99)}
    assert f(1) == (1, 10)
    assert keys(f) == {(1, 99), (1, 10)}


def test_default_only_param(space):
    f = space.new_cells(name="f", formula="def f(x=1): return x")
    assert f() == 1
    assert keys(f) == {(1,)}
    assert f(1) == 1
    assert keys(f) == {(1,)}


@posonly
def test_positional_only(space):
    f = space.new_cells(name="f", formula="def f(x, /, y): return x - y")
    assert f(1, 2) == -1
    assert keys(f) == {(1, 2)}
    with pytest.raises(TypeError, match="positional-only"):
        f(x=1, y=2)


@pytest.mark.parametrize(
    "src, call",
    [
        ("def f(*, x): return x", (1,)),
        ("def f(x, *, y): return x", (1, 2)),
        ("def f(x, *, y=5): return x", (1, 2)),
    ],
)
def test_keyword_only_still_raises(space, src, call):
    """KEYWORD_ONLY makes an arity-only guard swallow a TypeError."""
    f = space.new_cells(name="f", formula=src)
    assert f._impl.formula._bind_tails is None
    with pytest.raises(TypeError, match="too many positional arguments"):
        f(*call)
    assert keys(f) == set()


def test_var_positional_does_not_alias(space):
    """``f(1, 2)`` and ``f((1, 2))`` must stay distinct cache entries."""
    f = space.new_cells(name="f", formula="def f(*args): return args")
    assert f._impl.formula._bind_tails is None
    assert f(1, 2) == ((1, 2),)
    assert keys(f) == {((1, 2),)}
    assert f((1, 2)) == (((1, 2),),)
    assert keys(f) == {((1, 2),), (((1, 2),),)}


def test_var_keyword_still_raises(space):
    """``bind().apply_defaults()`` yields an unhashable dict; unchanged."""
    f = space.new_cells(name="f", formula="def f(**kw): return kw")
    assert f._impl.formula._bind_tails is None
    with pytest.raises(TypeError, match="unhashable type: 'dict'"):
        f()


def test_too_few_args(space):
    f = space.new_cells(name="f", formula="def f(x, y): return x + y")
    with pytest.raises(TypeError, match=re.escape(
            "missing a required argument: 'y'")):
        f(1)
    assert keys(f) == set()


def test_too_many_args(space):
    f = space.new_cells(name="f", formula="def f(x, y): return x + y")
    with pytest.raises(TypeError, match="too many positional arguments"):
        f(1, 2, 3)
    assert keys(f) == set()


def test_no_param_too_many_args(space):
    f = space.new_cells(name="f", formula="def f(): return 1")
    with pytest.raises(TypeError, match="too many positional arguments"):
        f(1)
    assert keys(f) == set()


@pytest.mark.parametrize(
    "src, args",
    [
        ("def f(x, y): return x", (1,)),
        ("def f(x, y): return x", (1, 2, 3)),
        ("def f(): return 1", (1,)),
        ("def f(x, y=2): return x", ()),
        ("def f(x, y=2): return x", (1, 2, 3)),
    ],
)
def test_error_message_matches_the_slow_path(space, src, args):
    """Rejected calls fall through and raise the very same TypeError."""
    f = space.new_cells(name="f", formula=src)
    impl = f._impl

    with pytest.raises(TypeError) as fast:
        get_node(impl, args, None)
    with pytest.raises(TypeError) as slow:
        _bind_args(impl, args, {})

    assert str(fast.value) == str(slow.value)


# ---------------------------------------------------------------------------
# The traps of section 5 of the plan


@pytest.mark.parametrize(
    "args, masked, value",
    [
        ((1, 2, 3), (1, 2, 3), 123),
        ((1, 2, 4), (1, 2, None), 120),
        ((2, 3, 4), (None, None, None), 0),
    ],
)
def test_match_with_masked_list(space, args, masked, value):
    """``find_match`` calls ``get_value`` with a *list*, not a tuple.

    Returning it unchanged would make an unhashable cache key, so
    ``get_node`` requires ``args`` to be an exact tuple.
    """
    f = space.new_cells(name="f", formula="def f(x, y, z): return None")
    f.allow_none = True
    f[1, 2, 3] = 123
    f[1, 2, None] = 120
    f[None, None, None] = 0

    retargs, retvalue = f.match(*args)
    assert retargs == masked
    assert retvalue == value


def test_get_node_with_list_args_keys_as_a_tuple(space):
    f = space.new_cells(name="f", formula="def f(x, y): return x + y")
    node = get_node(f._impl, [1, 2], None)
    assert node[1] == (1, 2)
    assert node[1].__class__ is tuple


def test_paramfunc_copy_populates_the_slots():
    """``ParamFunc.__slots__ = ()`` must not defeat ``_copy_other``."""
    paramfunc = ParamFunc(NULL_FORMULA, name="_formula")
    assert paramfunc.source == NULL_FORMULA.source
    assert paramfunc.signature is NULL_FORMULA.signature
    assert paramfunc.parameters == ()
    assert paramfunc._bind_tails == ((),)


def test_space_without_formula_error_is_unchanged():
    model = mx.new_model()
    try:
        s = model.new_space("S")
        with pytest.raises(AttributeError, match=re.escape(
                "'NoneType' object has no attribute 'signature'")):
            s[1]
    finally:
        model.close()


# ---------------------------------------------------------------------------
# Derived state must never go stale


def test_bind_tails_refreshed_when_the_formula_changes(space):
    f = space.new_cells(name="f", formula="def f(x): return x")
    assert f(1) == 1
    assert keys(f) == {(1,)}

    f.formula = "def f(x, y=2): return x + y"
    assert f(1) == 3
    assert keys(f) == {(1, 2)}

    f.formula = "def f(*args): return args"
    assert f(1, 2) == ((1, 2),)
    assert keys(f) == {((1, 2),)}


def test_bind_tails_survives_pickling():
    formula = Formula("def f(x, y=2): return x + y")
    restored = pickle.loads(pickle.dumps(formula))
    assert restored._bind_tails == (None, (2,), ())
    assert restored.parameters == ("x", "y")


def test_bind_tails_of_a_copied_formula(space):
    """Cells constructed from an existing Formula copy the derived state."""
    original = Formula("def f(x, y=2): return x + y")
    f = space.new_cells(name="f", formula=original)
    assert f._impl.formula is not original
    assert f._impl.formula._bind_tails == (None, (2,), ())
    assert f(1) == 3
    assert keys(f) == {(1, 2)}


def test_itemspace_keys_match_the_slow_path():
    """Spaces bind through the same ``get_node``; dynamic cells dominate."""
    model = mx.new_model()
    try:
        s = model.new_space("S", formula=lambda t, kind=None: None)
        s.new_cells(name="f", formula="def f(x): return (t, kind, x)")

        assert s[1].f(0) == (1, None, 0)
        assert s(2, "a").f(0) == (2, "a", 0)
        assert set(s._impl.param_spaces) == {(1, None), (2, "a")}

        assert get_node(s._impl, (1,), None) == (
            s._impl, _bind_args(s._impl, (1,), {}))
        assert get_node(s._impl, (2, "a"), None) == (
            s._impl, _bind_args(s._impl, (2, "a"), {}))
    finally:
        model.close()


def test_cells_invariant_over_a_model(space):
    """``get_node`` == ``(obj, _bind_args(...))`` for real cells impls."""
    sources = [
        "def c0(): return 0",
        "def c1(x): return x",
        "def c2(x, y): return x",
        "def c3(x, y=10, z=20): return x",
        "def c4(*args): return args",
        "def c5(**kw): return kw",
        "def c6(x, *, y=1): return x",
    ]
    impls = [
        space.new_cells(name=src[4:src.index("(")], formula=src)._impl
        for src in sources
    ]

    for impl in impls:
        for args in CALL_ARGS:
            for kwargs in CALL_KWARGS:
                slow = _outcome(
                    lambda o=impl, a=args, k=kwargs: (
                        o, _bind_args(o, a, {} if k is None else k))
                )
                fast = _outcome(
                    lambda o=impl, a=args, k=kwargs: get_node(o, a, k))
                assert fast == slow, "%s args=%r kwargs=%r" % (
                    impl.name, args, kwargs)
