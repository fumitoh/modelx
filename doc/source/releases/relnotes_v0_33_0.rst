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

* :meth:`Model.export<modelx.core.model.Model.export>` and
  :func:`~modelx.export_model` accept a new ``locked_spaces`` parameter for
  using the exported model from several threads on a free-threaded build of
  Python (3.13t, 3.14t). ItemSpaces are independent of each other, so each
  thread can be given its own range of ItemSpaces, such as ``Projection[i]``
  for a range of model points. Spaces that all the threads share, such as a
  Space holding input data or assumptions, are listed in ``locked_spaces``:
  such a Space, together with the Spaces below it and its ItemSpaces,
  calculates each Cells value and creates each ItemSpace only once when
  several threads ask for it at the same time, by taking a lock shared by all
  the locked Spaces of the model. A cached value is returned without taking
  the lock, so the cost is paid only the first time a value is calculated, and
  Spaces not listed are exported exactly as before. Lock the Spaces whose Cells
  take a bounded set of arguments, not the Space whose ItemSpaces are
  partitioned across the threads, because every calculation in a locked Space
  waits for the one lock. For example, lifelib's ``TradLife_A`` can be exported
  as ``model.export(path, locked_spaces=['InputData', 'Economic', 'Assumptions',
  'PolicyAttrs', 'CommTable'])`` and ``Projection[i]`` computed from a thread
  pool. Measured on Python 3.14.7 free-threaded with the shared Spaces already
  cached, the exported ``TradLife_A`` projects 2.2 times as many model points
  per second with 8 threads as with one, and the same export compiled with
  `modelx-cython <https://github.com/fumitoh/modelx-cython>`_ 3.3 times as
  many; the lock costs nothing measurable single-threaded.
  See :func:`~modelx.export_model` for the guarantees and their limits.


Backward Incompatible Changes
==============================

* Because the exported Space classes declare ``__slots__``, their attributes
  are fixed when the model is exported. A macro or a formula that assigns a
  Reference the model does not already have now raises :obj:`AttributeError`
  in the exported model. Space objects there are also no longer
  weak-referenceable, have no ``__dict__``, and cannot be pickled with pickle
  protocol 0 or 1.
  `modelx-cython <https://github.com/fumitoh/modelx-cython>`_ cannot compile a
  model exported this way either, until it is updated to read ``__slots__``,
  nor a model exported with ``locked_spaces`` until it is updated to
  translate the lock.
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
