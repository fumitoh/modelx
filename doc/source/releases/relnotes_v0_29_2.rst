====================================
modelx v0.29.2 (6 December 2025)
====================================

This release introduces the following bug fix.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
==============

* Add :meth:`~modelx.core.model.Model.new_space_from_model` to copy a model into another model as a space.


Bug Fixes
============

* Fix issue where creating a new child space in a parameterized parent space that already has ItemSpaces 
  would not properly clear the ItemSpaces and update the namespace (`GH203`_).

.. _GH203: https://github.com/fumitoh/modelx/issues/203


