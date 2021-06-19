.. currentmodule:: modelx.core

===============================
modelx v0.16.0 (19 June 2021)
===============================

This release introduces the following enhancement and changes.

Enhancements
============

.. rubric:: Introduction of clear methods

The following three methods are introduced.

* :meth:`Model.clear_all<model.Model.clear_all>`
* :meth:`Space.clear_cells<space.UserSpace.clear_cells>`
* :meth:`Space.clear_items<space.UserSpace.clear_items>`

:meth:`Model.clear_all<model.Model.clear_all>` deletes all the ItemSpaces
and clears all the Cells in the Model.
To be consistent with :meth:`Model.clear_all<model.Model.clear_all>`,
The behaviour of :meth:`Space.clear_all<space.UserSpace.clear_all>`
has changed. To inherit the previous behaviour of
:meth:`Space.clear_all<space.UserSpace.clear_all>`
:meth:`Space.clear_items<space.UserSpace.clear_items>` has been introduced.

.. rubric:: Introduction of rename methods

The following three methods are introduced.

* :meth:`Space.rename<space.UserSpace.rename>`
* :meth:`Cells.rename<cells.Cells.rename>`

Backward Incompatible Changes
=============================

.. rubric:: Change in Space.clear_all

The behaviour of :meth:`Space.clear_all<space.UserSpace.clear_all>` has changed.
It now clears Cells, in addition to deleting ItemSpaces. Further more,
ItemSpaces in recursive child Spaces are also deleted.
The previous behavior of :meth:`Space.clear_all<space.UserSpace.clear_all>`
is inherited by :meth:`Space.clear_items<space.UserSpace.clear_items>`.


Bug Fixes
=========

* Creating a child Cells in a UserSpace by the
  :meth:`UserSpace.new_cells<space.UserSpace.new_cells>` method
  now deletes ItemSpaces whose base space or any of its child space
  has the UserSpace as its base space.

* Setting the :attr:`~space.UserSpace.formula` of a UserSpace now
  deletes ItemSpaces whose base space or any of its child space
  has the UserSpace as its base space.

* Raise error when trying to set DynamicCells formulas


