====================================
modelx v0.33.0 (not yet released)
====================================

This release introduces the following enhancements, backward-incompatible
changes and bug fixes.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
============

* The Space classes that
  :meth:`Model.export<modelx.core.model.Model.export>` and
  :func:`~modelx.export_model` generate now declare ``__slots__``.
  CPython keeps slotted attributes in a fixed-size array instead of an
  instance dictionary and specialises the bytecode that reads them, so the
  exported model runs faster and takes less memory.
  Measured on ``BasicTerm_SC`` of the ``basiclife`` library of
  `lifelib <https://lifelib.io>`_, 3,000 model points per round and the best
  of three rounds, the run is 21% faster on Python 3.13 and 28% faster on
  Python 3.14, and an ItemSpace of ``Projection`` takes 616 bytes instead of
  1,632.

  Pass ``use_slots=False`` to
  :meth:`Model.export<modelx.core.model.Model.export>` or
  :func:`~modelx.export_model` to generate the same output as modelx v0.32.0.


Backward Incompatible Changes
==============================

* Because the exported Space classes declare ``__slots__``, Space objects in
  an exported model are no longer weak-referenceable, and attributes cannot
  be added to them at run time.
  `modelx-cython <https://github.com/fumitoh/modelx-cython>`_ also cannot
  compile a model exported this way until it is updated to read ``__slots__``.
  Export with ``use_slots=False`` in either case.

* :meth:`Model.export<modelx.core.model.Model.export>` and
  :func:`~modelx.export_model` now raise :obj:`ValueError` when a name
  assigned as an attribute of a Space is also the name of a method of the
  generated class, which in practice means a Cells sharing its name with a
  parameter of its own Space or of an enclosing Space. Such a name has always
  been exported incorrectly, because the parameter value is assigned over the
  method, and it cannot be declared in ``__slots__`` at all. Rename one of the
  two, or export with ``use_slots=False``.


Bug Fixes
============

* On Python 3.12 and later,
  :meth:`Model.export<modelx.core.model.Model.export>` and
  :func:`~modelx.export_model` no longer drop the ``self.`` prefix from a
  Cells or a Reference used inside a list, dict or set comprehension when
  the same formula contains a generator expression, a lambda or a nested
  ``def`` ahead of the comprehension. The exported formula raised
  ``NameError`` the first time it was called. Since Python 3.12 such
  comprehensions no longer produce a symbol table of their own, and the
  exporter located the symbol table of the enclosing scope by position
  rather than lexically.

* :meth:`Model.export<modelx.core.model.Model.export>` and
  :func:`~modelx.export_model` no longer prefix the loop variable of a list,
  dict or set comprehension with ``self.`` when it shares its name with a
  Cells or a Reference. ``for self.x in ...`` is valid Python, so the
  exported model imported and ran, but silently rebound the member on the
  Space object, and every later use of that member failed with an error
  pointing nowhere near the formula that broke it.
