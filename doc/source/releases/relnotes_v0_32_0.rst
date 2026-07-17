====================================
modelx v0.32.0 (not yet released)
====================================

This release introduces the following enhancements and
backward-incompatible changes.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
==============

.. rubric:: Selective ItemSpace invalidation

Previously, editing a Space that any live
:class:`~modelx.core.space.ItemSpace` depended on deleted **all** the
ItemSpaces of every parameterized Space using the edited Space —
including ItemSpaces built on other, unaffected base Spaces.

ItemSpace deletion is now selective per ItemSpace: an edit (creating,
deleting or renaming a Cells or a Reference, changing a formula, or
adding, removing, renaming or deleting a Space) deletes an ItemSpace
only when the edited Space can actually affect it, namely when the
edited Space is one of:

* a Space that a node of the ItemSpace's dynamic tree is based on,
* a base Space of such a Space, or
* the nearest static Space containing the ItemSpace — the
  parameterized Space itself in the normal case, or its nearest static
  ancestor when the parameterized Space is itself dynamic (nested
  ItemSpace trees).

Changing a Cells formula or renaming a Cells deletes only the
ItemSpaces whose dynamic trees are based on the Cells' Space (or on a
Space inheriting the Cells), as before.

ItemSpaces built on unrelated Spaces — including sibling ItemSpaces of
the same parameterized Space built on other base Spaces — now survive
such edits, which avoids costly recalculation of unaffected dynamic
subtrees in large models.

Deleting a Space that live ItemSpaces are based on now also deletes
those ItemSpaces, which previously survived with dangling references
to the deleted Space.

Assigning or deleting a model-level (global) Reference still deletes
all ItemSpaces in the model.


Backward Incompatible Changes
==============================

* As described above, edits that previously deleted all ItemSpaces of
  the affected parameterized Spaces now delete only the dependent
  ItemSpaces. Code that relied on unrelated ItemSpaces being implicitly
  deleted by an edit should delete them explicitly, for example with
  :meth:`UserSpace.clear_items<modelx.core.space.UserSpace.clear_items>`
  or :meth:`Model.clear_all<modelx.core.model.Model.clear_all>`.
