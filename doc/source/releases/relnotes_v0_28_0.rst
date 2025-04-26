==================================
modelx v0.28.0 (7 December 2024)
==================================

This release introduces the following enhancements and bug fixes.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
==============


* Reading models by :func:`~modelx.read_model` is now significantly faster than before (`GH165`_).
* Improved error message when no name is found in Space (`GH151`_).

.. _GH165: https://github.com/fumitoh/modelx/discussions/165
.. _GH151: https://github.com/fumitoh/modelx/issues/151



Bug Fixes
============


* Cannot save values with unary "-" as reference variables (`GH159`_)

.. _GH159: https://github.com/fumitoh/modelx/issues/159


