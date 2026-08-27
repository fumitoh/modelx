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

* Because the exported Space classes declare ``__slots__``, their attributes
  are fixed when the model is exported. A macro or a formula that assigns a
  Reference the model does not already have now raises :obj:`AttributeError`
  in the exported model. Space objects there are also no longer
  weak-referenceable, have no ``__dict__``, and cannot be pickled with pickle
  protocol 0 or 1.
  `modelx-cython <https://github.com/fumitoh/modelx-cython>`_ cannot compile a
  model exported this way either, until it is updated to read ``__slots__``.
  Export with ``use_slots=False`` in any of these cases.

* :meth:`Model.export<modelx.core.model.Model.export>` and
  :func:`~modelx.export_model` now raise :obj:`ValueError` when a name
  assigned as an attribute of a Space is also defined by the generated class,
  because ``__slots__`` cannot declare such a name. In practice that is a
  Cells sharing its name with a parameter of its own Space or of an enclosing
  Space, or with a Reference of the Space including a model-level global; it
  is also a Space parameter named after a member of ``_mx_sys.BaseSpace``,
  such as ``_cells``. Most such names are exported incorrectly today, because
  the attribute is assigned over the method. Rename one of the two, or export
  with ``use_slots=False``.


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
