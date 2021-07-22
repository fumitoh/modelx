
===============================
modelx v0.16.1 (23 July 2021)
===============================

This release fixes bugs and reflects some minor enhancements.

Enhancements
============

* :class:`~modelx.io.baseio.BaseDataClient` classes now have
  descriptive ``repr``.

* :meth:`~modelx.core.model.Model._get_attrdict` includes the ``refs``
  element.


Bug Fixes
=========

* Fix error raised when networkx version numbers include characters(e.g. "2.6rc1").

* Bug in :meth:`~modelx.core.cells.Cells.rename` where
  the name of the underlying function is not renamed.

* Bug where restored models by :func:`~modelx.restore_model`
  miss ``_mx_dataclient`` in pandas objects created by
  :meth:`~modelx.core.space.UserSpace.new_pandas`.

* Bug where global names in generator expressions are
  not reported by :meth:`~modelx.core.cells.Cells.precedents`.

* Fix error with pandas 1.3.0 in :attr:`~modelx.core.cells.Cells.frame`

