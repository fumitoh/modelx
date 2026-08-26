====================================
modelx v0.33.0 (not yet released)
====================================

This release introduces the following bug fix.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Bug Fixes
============

* On Python 3.12 and later,
  :meth:`Model.export<modelx.core.model.Model.export>` and
  :func:`~modelx.export_model` no longer generate wrong code for a name
  inside a list, dict or set comprehension when the same formula contains a
  generator expression, a lambda or a nested ``def`` ahead of the
  comprehension.

  Since Python 3.12, such comprehensions are compiled into the enclosing
  function instead of into a nested one, and no longer produce a symbol
  table of their own. The exporter located the symbol table of the enclosing
  scope by position rather than lexically, and generator expressions,
  lambdas and nested ``def``\ s do still produce symbol tables of their own,
  so a comprehension that followed one of them was resolved against that
  scope instead of against the formula.

  Two kinds of wrong code could result. A reference to a Cells or a
  Reference could lose the ``self.`` prefix it needs, in which case the
  exported formula raised ``NameError`` the first time it was called.
  Conversely, a comprehension's own loop variable could gain a ``self.``
  prefix it must not have, when it happened to share its name with a Cells
  or a Reference. ``for self.x in ...`` is valid Python, so in that case the
  exported model imported and ran, but silently rebound the member on the
  Space object, and later calls to that member failed with errors pointing
  nowhere near the formula that broke it.

  Python 3.11 and earlier are not affected, because comprehensions produce
  symbol tables of their own there.
