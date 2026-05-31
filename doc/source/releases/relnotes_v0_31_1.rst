====================================
modelx v0.31.1 (31 May 2026)
====================================

This release introduces the following enhancement.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
==============

* The ``info`` property, available on each subclass of
  :class:`~modelx.core.base.Interface`, returns a lightweight wrapper whose
  ``repr`` displays a human-readable snapshot of the object -- such as the
  cells' signature, formula source, cached values and input values for a
  cells, or the parameters and child item spaces for a space. The property
  is available on the following classes:

  * :attr:`Model.info <modelx.core.model.Model.info>`
  * :attr:`UserSpace.info <modelx.core.space.UserSpace.info>`
  * :attr:`ItemSpace.info <modelx.core.space.ItemSpace.info>`
  * :attr:`DynamicSpace.info <modelx.core.space.DynamicSpace.info>`
  * :attr:`Cells.info <modelx.core.cells.Cells.info>`

  This is an experimental feature. Its output format and behavior may
  change in future releases without notice.
