==================================
modelx v0.25.1 (14 June 2024)
==================================

This release introduces the following backward-incompatible changes and bug fixes.

To update to modelx v0.25.0, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Bug Fixes
============

* NetworkXError during clear_all (`GH127`_)

.. _GH127: https://github.com/fumitoh/modelx/issues/127


Backward Incompatible Changes
==============================

* An ItemSpace can now be created from no more than one base space.




