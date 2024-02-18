==================================
modelx v0.25.0 (18 February 2024)
==================================

This release introduces the following enhancements, backward-incompatible changes and bug fixes.

To update to modelx v0.25.0, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
============

.. py:currentmodule:: modelx

Introduction of a new property Model.path
-------------------------------------------

This release introduces a new property :attr:`~core.model.Model.path` to the :class:`~core.model.Model` class.
This property holds the path from which the model is loaded or to which it is saved,
represented as a `pathlib.Path`_ object.
This property can be accessed within formulas using the special reference ``_model.path``.

This property make it possible for formulas to locate external files
by using paths relative to the model's location.

.. _pathlib.Path:
    https://docs.python.org/3/library/pathlib.html#pathlib.Path

Python 3.12 support
-----------------------

modelx now supports Python 3.12.

Backward Incompatible Changes
==============================

Spec changes due to C-level recursion avoidance
------------------------------------------------------------------

In this release the following two spec changes are introduced:

- The ability to call cells within formulas using the subscription operation ``[]`` will be removed.
  This feature was primarily syntactic sugar, so users can adapt their models to use the call operation ``()`` instead.
- Other methods on :class:`~core.cells.Cells`, such as :meth:`~core.cells.Cells.match`, will not be available anymore.
  If needed, cells can still be accessed directly using ``_space.cell_name``, where ``cell_name`` is the specific name of the cells.

**Rationale for backward-incompatible changes**

In Python versions prior to 3.11, Python's recursion mechanism triggered C-level recursion,
meaning the recursion depth in Python was constrained by the size of the C-stack.

With Python 3.11, there was a significant `change: <https://docs.python.org/3/whatsnew/3.11.html#inlined-python-function-calls>`_
Pure Python recursion won't induce C-level recursion anymore.
This separation appeared to address the issue initially.
However, the introduction of a hardcoded limit on C-level recursion in Python 3.12
revealed that certain dunder methods, like ``__call__`` and ``__getitem__``, still induce C-level recursion.

Since modelx heavily relies on cells objects calling other cells through ``__call__`` or ``__getitem__`` in their formulas,
the recursion limit for modelx formulas is effectively bound by the C-level recursion limit.
Although Python core developers have plans to increase the hardcoded limit on C-level recursion in future Python releases,
it doesn't fully resolve the core issue: the modelx recursion limit remains constrained by the C-stack size,
which varies across different platforms. For instance, on Windows, the default C-stack size is smaller and can't be altered after thread initiation. This limitation has been circumvented by initiating a new thread with a larger stack size for formula execution. In contrast, Linux allows dynamic increase of the C-stack size.

To address this issue comprehensively, a backward-incompatible change is introduced:
In the namespace associated with a modelx space, cell names will now be bound to the ``CellsImpl.call`` method,
bypassing the ``Cells.__call__`` method. This adjustment effectively detaches modelx recursion from C-level recursion,
rendering the recursion in modelx virtually limitless on all supported platforms (Windows, MacOS, Linux).

This restructuring aims to future-proof modelx against recursion limits across different future
Python versions and operating systems.


Bug Fixes
============

* AssertionError during export with Python 3.12 (`GH93`_)
* PermissionError in :func:`read_model` on Windows due to `a known issue <https://github.com/python/cpython/issues/74168>`_.

.. _GH93: https://github.com/fumitoh/modelx/issues/93


