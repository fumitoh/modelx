.. currentmodule:: modelx

.. _release-v0.1.0:

================================
modelx v0.1.0 (1 December 2019)
================================

.. contents:: What's new in v0.1.0
   :depth: 1
   :local:

This release introduces major spec changes and enhancements,
as well as a few minor bug fixes.

Enhancements
============

**Input and calculated values**

A Cells holds values either input by the user, or calculated by its formula.
The former are now called input values, and distinguished from tha latter::

    @mx.defcells
    def foo(x): return x * foo(x-1)

    foo[0] = 5
    foo[5]   # Calculated buy the formula

``foo[0]`` in this example holds an input value of 5,
while ``foo[5]`` holds a calculated value of 120.
To check whether a node of a Cells has an input value,
:meth:`~core.cells.CellNode.is_input` is now available.::

    >>> foo.node(0).is_input()
    True
    >>> foo.node(5).is_input()
    False

.. py:currentmodule:: modelx.core.cells

**Change in Cells.clear and introduction of Cells.clear_all and Cells.clear_at**

With the introduction of the input value concept,
:meth:`Cells.clear` method now only clears calculated values, but not input values.
:meth:`Cells.clear_all` method is introduced for clearing both input and calculated values.
Another new method :meth:`Cells.clear_at` is introduced for clearing
the value of a specific Cells node, whether it's an input value or a calculated value.

**Recalculation upon input change**

Before version 0.1.0, when a new input value is assigned to a node of a Cells,
the values of the nodes depending on the input cells are cleared.
From version 0.1.0, those values are recalculated.
Continuing the previous example::

    >>> foo.series
    x
    0      1
    1      1
    2      2
    3      6
    4     24
    5    120
    Name: foo, dtype: int64

    >>> foo[0] = 2
    >>> foo.series
    x
    0      2
    1      2
    2      4
    3     12
    4     48
    5    240
    Name: foo, dtype: int64


**Models available as modelx attirbutes**

*Only available with Python 3.7 or newer*

.. currentmodule:: modelx

In addition to :func:`get_models`, models can also be acquired
through modelx attribute access::

    >>> m1 = mx.get_models["Model1"]
    >>> m2 = mx.Model1
    >>> m1 is m2
    True


**defcells and new_space creates new model/space if no current model/space is available**

Previously, if the current model and/or the current space don't exist,
the user needs to create a model and/or a space manually.
From version 0.1.0, if the current model and/or the current space are
missing when calling :func:`defcells` and :func:`new_space` API decorator/functions,
a new model and/or a new space are created automatically, and
are assigned to the current model and/or the current space, so
the user does not need to create them explicitly beforehand.

**New serializer for reading/writing models**

Serializer is an internal part of modelx to implement the functionality of
reading models from and writing models to files in a human-readable format.
The initial version of modelx serializer (version 1) was introduced in modelx v0.0.22.
The version 1 serializer had limited functionality.

modelx v0.1.0 comes with almost completely rewritten serializer (version 2).
The version 2 serializer reflects the following improvements.

* Output files with ".py" extension are syntactically correct Python scripts,
  and also importable.
* The new format of the output files is more readable.
* When writing a model to an existing directory, the existing directory
  is renamed with the prefix of "_BAK1".
* Any `picklable`_ objects as references can be stored in binary data files.
* Input values of Cells are also stored. Input values can be any `picklable`_ objects.
* Object identities among the stored `picklable`_ objects are preserved.

.. _picklable: https://docs.python.org/3/library/pickle.html

:func:`read_model` of modelx v0.1.0 still supports reading files written
in the version 1 format.

**Other enhancements**

* :func:`~defcells` can now be used to update existing cells formulas,
  in addition to creating a new cells.

* `maxlen` parameter is added to :func:`~start_stacktrace`, to specify the
  maximum length of traces to be kept (`GH13`_).

.. _GH13: https://github.com/fumitoh/modelx/issues/13

Backward Incompatible Changes
=============================

.. py:currentmodule:: modelx.core.cells

* The behaviour of :meth:`Cells.clear` has changed. See `Enhancements`_ section.
* The behaviour of the value assignment operation on :class:`Cells` has changed.
  See `Enhancements`_ section.

.. py:currentmodule:: modelx

* The behaviour or :func:`defcells` and :func:`new_space` API functions have changed.
  See `Enhancements`_ section.
* The new format of :func:`write_model` is introduced. See `Enhancements`_ section.


Bug Fixes
=========

* :func:`cur_space` is set to None when the current model is deleted.
* The current space attribute of a models is now saved and restored
  by :meth:`~core.model.Model.save` method and :func:`open_model`.
* Fix the error raised from a package supporting IPython's auto complete
  feature when used in Windows command prompt console.
* Fix the error raised when attempting to delete refs by the `del` statement.
* Fix missing source file info from restored cells.
* Fix crash with Python 3.8 on Windows due to stack overflow.


