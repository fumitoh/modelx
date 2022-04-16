
==================================
modelx v0.19.0 (16 April 2022)
==================================

This release introduces the following enhancements and changes.

Enhancements
============

.. currentmodule:: modelx.core

Support for memory-optimized runs
---------------------------------------

This version introduces the following new methods to support
memory-optimized runs.

* :meth:`~model.Model.generate_actions`
* :meth:`~model.Model.execute_actions`

Memory-optimized runs are for calculating specified nodes
by consuming less memory.
A memory-optimized run actually involves two runs.
The first run is for generating a list of actions, and
invoked by calling :meth:`~model.Model.generate_actions`.
The second run is for obtaining the desired results, and
performed by calling :meth:`~model.Model.execute_actions` with the actions
returned by :meth:`~model.Model.generate_actions`.

.. seealso:: `Running a heavy model while saving memory <https://modelx.io/blog/2022/03/26/running-model-while-saving-memory/>`_,
        a blog post on https://modelx.io


Backward Incompatible Changes
=============================

Spyder-modelx users need to update ``spymx-kernels`` to
:doc:`version 0.1.3 <spymx_kernels_relnotes>`.

Bug Fixes
=========

* Error on saving `math.inf`_ and `numpy.inf`_ (`GH62`_).

.. _GH62: https://github.com/fumitoh/modelx/issues/62
.. _math.inf: https://docs.python.org/3/library/math.html#math.inf
.. _numpy.inf: https://numpy.org/devdocs/reference/constants.html#numpy.inf