====================================
modelx v0.34.0 (unreleased)
====================================

This release is in development, and these notes are not complete yet.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Backward Incompatible Changes
==============================

* ``(key, value) in cells.items()`` reads only the stored values of the
  Cells, as :meth:`Cells.items<modelx.core.cells.Cells.items>` itself does.
  It is :obj:`False` when no value is stored for ``key``; it used to run
  the formula for ``key``, store the value and compare it. Like
  ``key in cells``, it no longer applies default arguments: for a Cells
  ``g(t, k=1)`` that returns ``(t, k)`` and holds ``g(1)``,
  ``((1,), (1, 1)) in g.items()`` used to be :obj:`True` and is now
  :obj:`False`, while ``((1, 1), (1, 1)) in g.items()`` is :obj:`True`
  as before.


Bug Fixes
============

* :meth:`Cells.values<modelx.core.cells.Cells.values>` and
  :meth:`Cells.items<modelx.core.cells.Cells.items>` now return the stored
  values of a Cells with one parameter whose argument is a tuple, and of a
  Cells with ``*args`` after another parameter.
  They used to look each key up again as ``cells[key]``, which reads a
  tuple as the tuple of all the arguments. For a Cells ``h(x)``, with
  ``h((1, 2))`` stored they raised :obj:`TypeError`; with ``h((1,))``
  stored they returned the value of ``h(1)`` in its place, or, when
  ``h(1)`` was not stored, ran its formula, stored the value and raised
  :obj:`RuntimeError`. For a Cells ``f(a, *args)``, they ran the formula
  and raised :obj:`RuntimeError` whatever the arguments.
  Each value is now read by the key it is stored under, which also makes
  ``values()`` about 40% and ``items()`` about 30% faster: 53 ms instead
  of 95 ms for ``list(h.values())`` over 100,000 values.
  ``values()`` and ``items()`` return ``CellsValuesView`` and
  ``CellsItemsView`` objects, which are instances of
  :class:`collections.abc.ValuesView` and
  :class:`collections.abc.ItemsView`.

  ``key in cells``, ``cells[key]``, ``cells.get(key)`` and
  ``dict(cells)`` still read a tuple key as the tuple of all the
  arguments; see :ref:`cells-value-operations`.
