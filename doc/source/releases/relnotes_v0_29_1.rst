====================================
modelx v0.29.1 (22 November 2025)
====================================

This release introduces the following enhancements and bug fixes.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
==============

* Add :func:`~modelx.export_members` API function to export space members to a module's global namespace.

* Add :meth:`~modelx.core.model.Model.compare_cells` method to compare cells with the same name across different spaces in a model. This is a tentative feature based on user request (`GH196`_).

.. _GH196: https://github.com/fumitoh/modelx/discussions/196


Bug Fixes
============

* Fix system references being incorrectly included in :attr:`~modelx.core.space.UserSpace.refs` property.


