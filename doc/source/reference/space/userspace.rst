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

Space operations
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~UserSpace.copy
  ~UserSpace.rename

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
  ~UserSpace.update_pandas
  ~UserSpace.update_module

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