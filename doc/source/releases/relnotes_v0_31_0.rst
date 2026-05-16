====================================
modelx v0.31.0 (17 May 2026)
====================================

This release introduces the following enhancements, backward-incompatible
changes and bug fixes.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
==============

* Macros are now saved and loaded together with the model by
  :func:`~modelx.write_model` and :func:`~modelx.read_model` (`GH229`_).
* A pseudo-Python header is now added to serialized Python files for better
  editor and IDE integration (`GH217`_).

.. _GH229: https://github.com/fumitoh/modelx/pull/229
.. _GH217: https://github.com/fumitoh/modelx/pull/217


Backward Incompatible Changes
==============================

* This release introduces a new version of the model serializer (serializer
  version 7). Models saved by this version of modelx **cannot be read by
  previous versions of modelx**. To save a model in a format that earlier
  versions (modelx v0.30.x and before) can read, pass ``version=6`` to
  :func:`~modelx.write_model` or :func:`~modelx.zip_model`::

      >>> modelx.write_model(model, "model_dir", version=6)


Bug Fixes
============

* Docstrings containing special characters (backslashes, embedded or trailing
  quotes) now round-trip correctly during serialization (`GH228`_).
* :attr:`~modelx.core.cells.Cells.preds`,
  :attr:`~modelx.core.cells.Cells.succs` and
  :attr:`~modelx.core.cells.Cells.precedents` now raise a clear ``ValueError``
  instead of an internal ``NetworkXError`` when no value is cached for the
  given arguments.
* :func:`~modelx.read_model` now raises a clear error when the given path is
  not a modelx model, instead of a confusing ``FileNotFoundError``.
* Fixed a crash in the exporter when spaces inherit model-level (global)
  references.
* Fixed a crash when formatting formula errors for uncached cells called with
  unhashable arguments.

.. _GH228: https://github.com/fumitoh/modelx/pull/228
