====================================
modelx v0.34.0 (unreleased)
====================================

This release is in development. The notes below record the changes made
so far.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Bug Fixes
============

* :meth:`Cells.values<modelx.core.cells.Cells.values>` and
  :meth:`Cells.items<modelx.core.cells.Cells.items>` now return the stored
  values of a Cells with one parameter whose argument is a tuple.
  They used to look each key up again as ``cells[key]``, which reads a
  tuple as the tuple of all the arguments. For a Cells ``h(x)``, with
  ``h((1, 2))`` stored they raised :obj:`TypeError`; with ``h((1,))``
  stored they returned the value of ``h(1)`` in its place, or, when
  ``h(1)`` was not stored, ran its formula, stored the value and raised
  :obj:`RuntimeError`. Each value is now read by the key it is stored
  under, which also makes ``values()`` about 40% and ``items()`` about
  30% faster: 53 ms instead of 95 ms for ``list(h.values())`` over
  100,000 values.

  ``(key, value) in cells.items()`` now reads only stored values as
  well. It is :obj:`False` when no value is stored for ``key``, where it
  used to run the formula and store the value, and, like
  ``key in cells``, it applies no default arguments.
  ``values()`` and ``items()`` return ``CellsValuesView`` and
  ``CellsItemsView`` objects, which are instances of
  :class:`collections.abc.ValuesView` and
  :class:`collections.abc.ItemsView`.

  ``key in cells``, ``cells[key]`` and ``dict(cells)`` still read a
  tuple key as the tuple of all the arguments; see
  :ref:`cells-value-operations`.
