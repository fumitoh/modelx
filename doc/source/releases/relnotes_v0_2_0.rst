.. currentmodule:: modelx

.. _release-v0.2.0:

================================
modelx v0.2.0 (13 December 2019)
================================

.. contents:: What's new in v0.2.0
   :depth: 1
   :local:

This release includes enhancements in reading and writing models,
as well as some spec changes.

Enhancements
============

**Enhanced model serializer**

The API functions :func:`write_model` and :func:`read_model` are based
on an updated and improved serializer.

Dynamic spaces assigned to references are also serialized by :func:`write_model`
and deserialized by :func:`read_model` (`GH25`_),
as well as input values of cells in dynamic spaces if any::

    import modelx as mx
    m = mx.new_model()
    SpaceA = m.new_space('SpaceA', formula=lambda t: None)

    @mx.defcells
    def foo(x):
        return x

    m.new_space('SpaceB', refs={'RefA': m.SpaceA[0]})
    SpaceA[1].foo[2] = 3

    mx.write_model(m, "testdir")
    m2 = mx.read_model("testdir")

    m2.SpaceB.RefA is m2.SpaceA[0]   # => True
    m2.SpaceA[1].foo[2]              # => 3

Models written by :ref:`modelx v0.1.0 <release-v0.1.0>` or
:ref:`modelx v0.0.25 <release-v0.0.25>` can still be read by this version.

**Simplified serialization**

The previous serializer stores the object IDs of pickled references
in separate files. The updated serializer writes the object IDs
directly in the output files of the parent spaces.

**Option to activate dependent cells recalculation**

Recalculation of dependent cells introduced in
:ref:`modelx v0.1.0 <release-v0.1.0>` is deactivated
at modelx startup due to user request (`GH24`_).
Instead, two API functions, :func:`set_recalc` and :func:`get_recalc`,
are introduced for the users to explicitly set and get recalculation mode.


**Double-quoted strings in CellNode repr**

Strings in CellNode's repr, whether as arguments or values, are double-quoted,
as in ``m.s.a(name="World")="Hello World"`` (`GH27`_).


.. _GH25: https://github.com/fumitoh/modelx/issues/25
.. _GH24: https://github.com/fumitoh/modelx/issues/24
.. _GH27: https://github.com/fumitoh/modelx/issues/27


Backward Incompatible Changes
=============================

* Recalculation of dependent cells is deactivated at startup as
  explained in `Enhancements`_ section (`GH24`_). The user needs to explicitly
  activate it by :func:`set_recalc`.

.. py:currentmodule:: modelx.core.space

* :meth:`~UserSpace.static_spaces` is renamed to :meth:`~UserSpace.named_spaces`.
  :meth:`~UserSpace.static_spaces` is still
  available for backward compatibility, but is now deprecated and removed
  in future releases.

* Dynamic spaces that are direct children of user spaces are now of
  the :class:`RootDynamicSpace` type, which is a subclass of the :class:`DynamicSpace` type.


Bug Fixes
=========

.. py:currentmodule:: modelx.core.model

* Fix :meth:`Model.write` method.
* Fix error when writing spaces whose names are single characters.