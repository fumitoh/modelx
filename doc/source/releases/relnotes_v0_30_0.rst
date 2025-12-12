====================================
modelx v0.30.0 (12 December 2025)
====================================

This release introduces the following enhancements and bug fixes.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
==============

This release introduces the Macro feature, which enables users to define and store Python functions 
as part of a model. Macros are simple Python functions that can be used for running and manipulating the model itself.
Macros are saved and loaded with the model,
making it easier to package related code alongside model definitions.

* Add :class:`~modelx.core.macro.Macro` class for representing Python functions stored within models (`GH206`_).
* Add :func:`~modelx.defmacro` decorator for defining macros directly within model code (`GH206`_).
* Add :meth:`~modelx.core.model.Model.new_macro` method for programmatically creating macros in models (`GH206`_).
* Add :attr:`~modelx.core.model.Model.macros` property to access all macros defined in a model (`GH206`_).


Bug Fixes
============

None

.. _GH206: https://github.com/fumitoh/modelx/pull/206


