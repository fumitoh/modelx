====================================
modelx v0.33.0 (not yet released)
====================================

This release introduces the following bug fixes.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


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
