.. currentmodule:: modelx

.. _release-v0.3.0:

================================
modelx v0.3.0 (18 February 2020)
================================

.. contents:: What's new in v0.3.0
   :depth: 1
   :local:

This release introduces some backward incompatible changes
to make modelx design clearer and easier to understand.

.. note::

    spyder-modelx needs to be updated to v0.2.0 for this version
    of modelx.

Backward Incompatible Changes
=============================

* Reassigning values to existing references in UserSpaces are now
  allowed without first deleting the references.
* References in Spaces can be defined as different types of references.
  If a name in a Space is defined as different types
  of references, the referenced value for the name is determined
  based on the following order of reference types
  from the highest priority to the lowest.

  - Arguments
  - Parent arguments
  - Dynamically defined references
  - Statically references
  - Global references

.. py:currentmodule:: modelx.core.space

* :class:`RootDynamicSpace` is now renamed to :class:`ItemSpace`.
* :meth:`~UserSpace.all_spaces` is renamed to :meth:`~UserSpace._all_spaces`.
* :class:`ItemSpace` objects are auto-named with two leading underscores
  (for example, ``__Space1`` and ``__Space2``).
* :attr:`~UserSpace.dynamic_spaces` is renamed to :attr:`~UserSpace._named_itemspaces`.



Bug Fixes
=========

* Fix the issue of dynamic spaces not inheriting base refs created
  after them (`GH25`_).
* Fix :attr:`~UserSpace._direct_bases`

.. _GH25: https://github.com/fumitoh/modelx/issues/25