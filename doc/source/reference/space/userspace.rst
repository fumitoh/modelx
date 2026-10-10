UserSpace
=========

.. currentmodule:: modelx.core.space

.. autoclass:: UserSpace

Basic properties
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~UserSpace.name
  ~UserSpace.fullname
  ~UserSpace.doc
  ~UserSpace.allow_none
  ~UserSpace.model
  ~UserSpace.parent
  ~UserSpace.properties
  ~UserSpace.refs
  ~UserSpace.has_params
  ~UserSpace.set_property
  ~UserSpace.info

Space operations
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~UserSpace.copy
  ~UserSpace.rename

.. _userspace-inheritance:

Inheritance
-----------

A UserSpace can be derived from other UserSpaces, its *base* Spaces,
given by the ``bases`` parameter of
:meth:`Model.new_space <modelx.core.model.Model.new_space>` and
:meth:`UserSpace.new_space <UserSpace.new_space>`, or by
:meth:`UserSpace.add_bases <UserSpace.add_bases>`.
The derived Space is called a *sub* Space.
Only Cells and References are inherited:

* **Cells and References.**
  For each Cells and each Reference of its bases that the sub Space does
  not define itself, the sub Space has an inherited one, with the same
  formula or value. A Cells or a Reference added to a base later
  appears in the sub Space too, and a change to the formula or the value
  in the base is seen in the sub Space.

* **Overriding.**
  Assigning a formula to an inherited Cells, or a value to an inherited
  Reference, makes it the sub Space's own,
  and later changes in the base no longer reach it.
  An inherited Cells cannot be deleted from the sub Space:
  ``del`` raises :obj:`ValueError`.
  Delete it from the base, or remove the base by
  :meth:`UserSpace.remove_bases <UserSpace.remove_bases>`.

* **Several bases.**
  When more than one base defines a name, the sub Space inherits it from
  the first of them in :attr:`~UserSpace.bases`.

* **Child Spaces are not inherited.**
  Since modelx 0.24.0 (see :doc:`/releases/relnotes_v0_24_0`),
  the child Spaces of a base are not copied into the sub Space.
  To have one in the sub Space, create it there with the base's child
  Space as its base, as in ``sub.new_space("Child", bases=base.Child)``.

* **The formula is not inherited.**
  A sub Space has no formula unless one is set on it,
  even when its base has one: its :attr:`~UserSpace.formula` and
  :attr:`~UserSpace.parameters` are :obj:`None`, and it has no ItemSpaces.
  Set a formula on the sub Space to create ItemSpaces from it.

ItemSpaces are made differently.
Unless the Space formula returns a ``'base'``,
an :class:`~modelx.core.space.ItemSpace` is a dynamic copy of its Space:
it has the Space's Cells, References and child Spaces,
and shares the Space's formula.

Inheritance operations
----------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~UserSpace.bases
  ~UserSpace.add_bases
  ~UserSpace.remove_bases


Child Space operations
----------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~UserSpace.spaces
  ~UserSpace.named_spaces
  ~UserSpace.static_spaces
  ~UserSpace.cur_space
  ~UserSpace.import_module
  ~UserSpace.new_space
  ~UserSpace.new_space_from_csv
  ~UserSpace.new_space_from_excel
  ~UserSpace.new_space_from_module
  ~UserSpace.new_space_from_pandas
  ~UserSpace.reload
  ~UserSpace.clear_all


Child Cells operations
----------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~UserSpace.cells
  ~UserSpace.new_cells
  ~UserSpace.new_cells_from_csv
  ~UserSpace.new_cells_from_excel
  ~UserSpace.new_cells_from_module
  ~UserSpace.new_cells_from_pandas
  ~UserSpace.import_funcs
  ~UserSpace.clear_cells
  ~UserSpace.sort_cells

Reference operations
--------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~UserSpace.set_ref
  ~UserSpace.absref
  ~UserSpace.relref
  ~UserSpace.new_excel_range
  ~UserSpace.new_pandas
  ~UserSpace.new_module


ItemSpace operations
---------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~UserSpace.itemspaces
  ~UserSpace.parameters
  ~UserSpace.formula
  ~UserSpace.set_formula
  ~UserSpace.del_formula
  ~UserSpace.clear_items
  ~UserSpace.clear_at
  ~UserSpace.node
  ~UserSpace.preds
  ~UserSpace.succs
  ~UserSpace.precedents

Exporting to Pandas objects
---------------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~UserSpace.frame
  ~UserSpace.to_frame