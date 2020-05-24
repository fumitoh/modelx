

===============================
modelx v0.7.0 (24 May 2020)
===============================

This release introduces some new features and fixes bugs around updating
objects and values upon model changes.

Enhancements
============
.. currentmodule:: modelx.core.space

.. rubric:: Introduction of :attr:`UserSpace.formula` setter and deleter

The :attr:`UserSpace.formula` property now supports assignment
and deletion operations, such as::

    >>> Space.formula = lambda x, y: None

    >>> del Space.formula

When the Formula of a UserSpace is reassigned or deleted,
existing child ItemSpaces are deleted.

.. rubric:: Introduction of :attr:`UserSpace.parameters` setter

The :attr:`UserSpace.parameters` property now supports assignment
operation, such as::

    >>> Space.parameters = ('x', 'y=0')

The assignment to :attr:`UserSpace.parameters` is a syntactic sugar
and the code above is equivalent to::

    >>> Space.set_formula(lambda x, y=0: None)

.. rubric:: Other enhancements
.. currentmodule:: modelx.core

* :attr:`~space.UserSpace.itemspaces` to return a mapping of
  arguments to child :class:`~space.ItemSpace` object.
* :meth:`~space.UserSpace.clear_all` and :meth:`~space.UserSpace.clear_at`
  methods on :class:`~space.UserSpace`.
* :meth:`~model.Model.backup` is added as an alias to :meth:`~model.Model.save`.


.. currentmodule:: modelx

Backward Incompatible Changes
=============================

* :func:`~get_object` now returns :obj:`NameError` when the name is not found.
* :class:`~core.node.ItemProxy` renamed to :class:`~core.node.Element`.
* Only tuples are interpreted as multiple indexes in subscription expression.


Bug Fixes
=========

* References not being updated for reassigned Formulas.
* Sub spaces directly under Model not being updated after its bases' deletion.
* Dependents values not being cleared at Cells' deletion.

