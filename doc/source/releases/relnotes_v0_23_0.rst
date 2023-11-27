==================================
modelx v0.23.0 (19 August 2023)
==================================

This release introduces the following enhancements, bug fixes and changes.


To update modelx, run the following command::

    >>> pip install modelx --upgrade

If you're using Anaconda, use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
============

.. py:currentmodule:: modelx

* Pure-Python models exported via :func:`export_model` or :meth:`Model.export<core.model.Model.export>`,
  now accurately differentiate among the 'auto', 'relative' and 'absolute' reference modes.

Bug Fixes
============

* Fixed an issue where saving a model to a zip archive on a network location would fail. (`GH82 <https://github.com/fumitoh/modelx/issues/82>`_)

* Nested parameters in exported models now behave consistently with their original models.

Changes
==========

* Auto-coercion (implicit conversion) of parameterless Cells objects to their values is now deprecated.
  Users will receive a deprecation warning when this conversion occurs.

* Starting with this release, modelx no longer supports Python 3.6,
  given that this version reached its end of life over a year ago.
  While modelx may still function with Python 3.6,
  modelx won't be tested against this version anymore.




