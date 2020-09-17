
===============================
modelx v0.10.0 (17 Sep 2020)
===============================


This release introduces the following enhancements and changes.

Enhancements
============

.. rubric:: Introduction of reference mode

References now have *reference mode*, an attribute to control how
the values of their derived References are determined when the values
are core modelx objects, such as Spaces or Cells.
The *reference mode* attribute can be set to either "absolute", "relative" or
"auto". Following methods are introduced to set References
by explicitly specifying their *reference modes*.

.. py:currentmodule:: modelx.core.space

* :meth:`UserSpace.absref` for setting *absolute* References
* :meth:`UserSpace.relref` for setting *relative* References
* :meth:`UserSpace.set_ref` for setting a Reference in a specified reference mode

When a Reference is in the *absolute* mode, its derived Reference is bound
to the same object as the base Reference.

When a Reference is in the *relative* mode, its derived Reference is bound
to an object whose relative position to the derived Reference is
consistent to the relative position of the object referenced by the base
Reference to the base Reference. When no such value exists, an Error
is raised.

When a Reference is in the *auto* mode, its derived Reference is bound
relatively when possible, or absolutely when not possible.

**Illustration**

In the diagram below, ``A`` is a UserSpace,
``B`` is a child UserSpace of ``A``, and ``foo`` is a child Cells of ``B``.

The next code defines ``bar`` in ``B`` as an *absolute* Reference to ``foo``::

    >>> B.absref(bar=B.foo)

.. figure:: /images/relnotes/v0_10_0/sample1_base.png

When a new UserSpace ``D`` is derived from ``B``,
the derived Reference ``bar`` in ``D`` is bound to ``foo`` in ``B``::

    >>> D.bar
    <Cells foo(x) in Model1.B>

.. figure:: /images/relnotes/v0_10_0/sample1_absref.png

Alternatively, ``bar`` in ``B`` can be defined as an *relative* Reference
as below::

    >>> B.relref(bar=B.foo)

In this case, the derived Reference ``bar`` in ``D``
is bound to ``foo`` in ``D``::

    >>> D.bar
    <Cells foo(x) in Model1.D>

.. figure:: /images/relnotes/v0_10_0/sample1_relref.png

Alternatively, ``bar`` in ``B`` can be defined as an *auto* Reference
by the assignment operation::

    >>> B.bar = B.foo

Since relative referencing is possible, ``D.bar`` is bound to ``D.foo``::

    >>> D.bar
    <Cells foo(x) in Model1.D>

In the next example, ``B.bar`` can be bound to ``A``
only in *absolute* mode or *auto* mode. Trying to bound ``B.bar``
to ``A`` in *relative* mode will raise an Error, because
``A`` is out of the tree originated from ``B`` and no corresponding
object exists for ``D.bar``::

    >>> B.absref(bar=B.foo)     # in absolute mode, or

    >>> B.bar = B.foo           # in auto mode

.. figure:: /images/relnotes/v0_10_0/sample2_base.png

In either mode, ``D.bar`` is bound to ``A``::

    >>> D.bar
    <UserSpace A in Model1>

.. figure:: /images/relnotes/v0_10_0/sample2_absref.png


Backward Incompatible Changes
=============================

Prior to this version, all References are in the *absolute* mode.
Now, the Reference assignment operation assigns modelx objects in *auto* mode,
which may result in some references being bound to unintended objects
when relative referencing is possible. These References now need to be
set explicitly as *absolute* References either by :meth:`UserSpace.absref`
or :meth:`UserSpace.set_ref`.

Bug Fixes
=========

* Bug where Excel files referenced by :class:`~modelx.io.excelio.ExcelRange`
  were not saved when they were not modified.
