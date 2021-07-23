.. currentmodule:: modelx

.. _release-v0.4.0:

================================
modelx v0.4.0 (15 March 2020)
================================

This release introduces major improvement in calculation tracing
as well as some bug fixes. The calculation speed is also improved
by 15% to 20%.

Enhancements
============

**Reference tracing**

References are now traced.
Prior to this release, when References were reassigned or deleted,
the values of Cells calculated by referring the References in their formulas
remained unchanged.
From this release, the dependent values are cleared when
References in their formulas change::

    SpaceA.bar = 3

    @mx.defcells(SpaceA)
    def foo():
        return bar

    foo()   # ==> 3
    SpaceA.bar = 4
    foo()   # ==> 4

Unlike Cells tracing, all the values of dependent Cells are cleared,
whether they are actually used in the calculation of the values or not,
as long as the References are referenced in the formulas of the Cells.
In the example blow, ``foo(0)`` is not dependent on ``SpaceA.bar``
but its value is cleared upon the reassignment to ``SpaceA.bar``::

    SpaceA.bar = 3

    @mx.defcells(SpaceA)
    def foo(x):
        if x > 0:
            return bar
        else:
            return 0

    foo(0)      # ==> 0
    foo(1)      # ==> 3
    dict(foo)   # ==> {0: 0, 1: 3}

    SpaceA.bar = 4
    dict(foo)    # ==> {}   (Both foo(0) and foo(1) are cleared.)


**Attribute reference tracing**

When References are referenced in formulas as attributes of Spaces,
they are also traced, but unlike the case above,
the dependency is determined based on whether the attributes are used
in then calculation, in the same way as Cells tracing.
In the example below, ``foo(0)`` is not dependent on ``SpaceA.SpaceB.bar``,
so they are not cleared upon the reassignment to  ``SpaceA.SpaceB.bar``::

    SpaceA.SpaceB.bar = 3

    @mx.defcells(SpaceA)
    def foo(x):
        if x > 0:
            return SpaceB.bar   # bar is referenced as an attribute of SpaceB
        else:
            return 0

    foo(0)      # ==> 0
    foo(1)      # ==> 3
    dict(foo)   # ==> {0: 0, 1: 3}

    SpaceA.SpaceB.bar = 4
    dict(foo)    # ==> {0: 0}   (Only foo(1) is cleared)


**Space formula tracing**

Cells and References in Space formulas are now also traced.
When the values of Cells or References in Space formulas are updated,
all the ItemSpaces created from the formula are cleared::

    def formula(i):
        return {"refs": {"foo0": bar(), "foo1": baz}}

    SpaceA = mx.new_space("SpaceA", formula=formula)

    @mx.defcells
    def foo(x):
        return 2 if x > 1 else foo1 if x > 0 else foo0

    @mx.defcells
    def bar():
        return 0

    SpaceA.baz = 1

    SpaceA[1].foo(2)    # ==> 2
    SpaceA[1].foo(1)    # ==> 1
    SpaceA[1].foo(0)    # ==> 0
    dict(SpaceA[1].foo)     # ==> {2: 2, 1: 1, 0: 0}

    SpaceA.bar = 2
    dict(SpaceA[1].foo)     # ==> {}

    SpaceA[1].foo(2)    # ==> 2
    SpaceA[1].foo(1)    # ==> 1
    SpaceA[1].foo(0)    # ==> 2
    dict(SpaceA[1].foo)     # ==> {2: 2, 1: 1, 0: 2}

    SpaceA.baz = 3
    dict(SpaceA[1].foo)     # ==> {}

    SpaceA[1].foo(2)    # ==> 2
    SpaceA[1].foo(1)    # ==> 3
    SpaceA[1].foo(0)    # ==> 2
    dict(SpaceA[1].foo)     # ==> {2: 2, 1: 3, 0: 2}

Bug Fixes
=========

* Bug with Spyder modelx plug-in which MxAnalyzer did not trace
  Cells in ItemSpaces properly.

