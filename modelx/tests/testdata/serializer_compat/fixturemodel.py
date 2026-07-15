"""Fixture model for serializer load-compatibility gates.

Phase 0 of the core refactoring (devnotes/CoreRefactorDesign.md):
the same model is saved with serializer versions 4-7 into the
``model_v<N>`` directories next to this module (see ``generate.py``).
``modelx/tests/serialize/test_serializer_compat.py`` loads each saved
copy and compares it against a freshly built fixture — guarding that
models written by old serializers keep loading while the core is
refactored.

The features used here are limited to those supported by serializer
version 4, so that a single builder covers every gated format version.
"""

import modelx as mx


def build_fixture_model(name="SerializerCompat"):
    """
    SerializerCompat---Base---foo(x)        foo has an input at x=0
                   |      +---bar(x)        lambda cells
                   |      +---Child---baz(y)
                   |      +---m = 3
                   |      +---refs to model/space/cells
                   |
                   +---Sub(Base)            derived cells and refs
                   |      +---m = 30        overridden ref
                   |
                   +---Params[i]            parameterized space
                   |
                   +---gref = 12            global ref
    """
    m = mx.new_model(name)
    m.doc = "Fixture model for serializer compatibility gates"

    base = m.new_space("Base")
    base.doc = "Base space"

    @mx.defcells(space=base)
    def foo(x):
        if x == 0:
            return 0
        return foo(x - 1) + m

    foo[0] = 100                    # input value overriding the formula

    base.new_cells(name="bar", formula=lambda x: x * m)

    child = base.new_space("Child")
    child.new_cells(name="baz", formula=lambda y: y + 1)

    base.m = 3

    # refs to modelx objects
    base.self_space = base
    base.the_model = m
    base.the_cells = foo

    # literal refs of various types
    base.s = "abc"
    base.lst = [1, "2", [3, None]]
    base.dct = {"k1": 1, "k2": [2, 3]}
    base.tpl = (1, (2, "x"))

    sub = m.new_space("Sub", bases=base)
    sub.m = 30                      # override the derived ref

    params = m.new_space("Params", formula=lambda i: None)
    params.new_cells(name="qux", formula=lambda t: t * i)

    m.gref = 12
    return m


def check_fixture_model(m):
    """Assertions that must hold for the fixture, freshly built or loaded."""
    # input value preserved, formula evaluation with refs
    assert m.Base.foo[0] == 100
    assert m.Base.foo[2] == 106            # 100 + 3 + 3
    assert m.Base.bar(5) == 15
    assert m.Base.Child.baz(1) == 2

    # inheritance: derived members and the overridden ref
    # (formulas are inherited; input values are not)
    assert m.Sub.foo._impl.is_derived()
    assert m.Sub.foo[0] == 0
    assert m.Sub.foo[2] == 60              # 0 + 30 + 30
    assert m.Sub.bar(5) == 150

    # refs to modelx objects restored by identity
    assert m.Base.self_space is m.Base
    assert m.Base.the_model is m
    assert m.Base.the_cells is m.Base.foo

    # literal refs
    assert m.Base.s == "abc"
    assert m.Base.lst == [1, "2", [3, None]]
    assert m.Base.dct == {"k1": 1, "k2": [2, 3]}

    # parameterized space
    assert m.Params[3].qux(2) == 6

    # global ref
    assert m.gref == 12

    m._impl._check_sanity()
