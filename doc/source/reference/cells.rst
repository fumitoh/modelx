Cells
=======================

.. currentmodule:: modelx.core.cells

.. autoclass:: Cells


Basic properties
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.name
  ~Cells.fullname
  ~Cells.doc
  ~Cells.set_doc
  ~Cells.allow_none
  ~Cells.model
  ~Cells.parent
  ~Cells.properties
  ~Cells.set_property
  ~Cells.is_cached


Cells operations
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.rename
  ~Cells.copy


Value operations
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.clear
  ~Cells.clear_all
  ~Cells.clear_at
  ~Cells.is_input
  ~Cells.match
  ~Cells.value


Formula operations
------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.formula
  ~Cells.set_formula
  ~Cells.clear_formula
  ~Cells.parameters



Node operations
------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.node
  ~Cells.preds
  ~Cells.succs
  ~Cells.precedents


Exporting to Pandas objects
---------------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Cells.series
  ~Cells.frame
  ~Cells.to_series
  ~Cells.to_frame
