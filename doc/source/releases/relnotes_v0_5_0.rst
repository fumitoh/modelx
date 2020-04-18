.. currentmodule:: modelx

.. _release-v0.5.0:

================================
modelx v0.5.0 (18 April 2020)
================================

This release is mainly for adding API functions and methods needed
for :ref:`spyder-modelx v0.3.0 <release-mxplugin-v0.3.0>`.
This release also introduce backward incompatible
changes, one of which is the elimination of implicit conversion of
Cells as arguments to their values.
The calculation speed is improved by 10% due to the change.

.. warning::

    Due to the introduction of the backward incompatible changes in this release,
    the source code of `lifelib`_ models based on the past lifelib versions needs
    manual changes to work with version of modelx. See `commit 605802a`_ and
    `commit df083f6`_ for where and how to make changes in your lifelib source code.

.. _commit 605802a: https://github.com/fumitoh/lifelib/commit/605802a0ea52d8fbec9a7380b6a0a0717de9bd71
.. _commit df083f6: https://github.com/fumitoh/lifelib/commit/df083f681752eab16508e676c63f9e2f6ae7ca4f
.. _lifelib: https://lifelib.io

.. contents::
   :depth: 1
   :local:


Enhancements
============

* bases is added to :attr:`~core.space.UserSpace._baseattrs`.

* Spaces now function as ItemProxy factories, and implement such properties
  as :attr:`~core.space.UserSpace.node`, :attr:`~core.space.UserSpace.preds`,
  and :attr:`~core.space.UserSpace.succs`.

* :meth:`~core.model.Model._get_from_name` method is added :class:`~core.model.Model`.

* ``as_proxy`` paramter is added to :func:`get_object` function to specify whether
  to return ReferenceProxy for a Reference.

* ``_namedid`` property is added to interfaces.

Backward Incompatible Changes
=============================

* Implicit conversion of a Cells with no parameters to its value,
  when passed as an argument to another Cells, is removed.
  It must be passed as value explicitly, by adding ``()``.

* :func:`~open_model` is renamed to :func:`~restore_model` for clarity.
  :func:`~open_model` is still available but a deprecation warning message appears,
  and it will be removed in a future release.

* The items in RefView._baseattrs are changed.

* :meth:`~core.space.UserSpace._to_attrdict` recursively calls arguments
  ``_to_attrdict`` only when its defined.

* :attr:`~core.cells.Cells.is_input` is moved to Cells

* ``CellNode`` is renamed to :class:`~core.node.ItemProxy`


Bug Fixes
=========

* Error when a model is restored and immediately saved (`GH30`_).
* An incomplete model is left when :func:`~read_model` fails.
* :func:`~get_object` can operate on properties too.

.. _GH30: https://github.com/fumitoh/modelx/issues/30

