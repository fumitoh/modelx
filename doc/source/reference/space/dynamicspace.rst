Dynamic Space
=============

.. currentmodule:: modelx.core.space

.. autoclass:: DynamicSpace

Basic properties
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~DynamicSpace.name
  ~DynamicSpace.fullname
  ~DynamicSpace.doc
  ~DynamicSpace.allow_none
  ~DynamicSpace.model
  ~DynamicSpace.parent
  ~DynamicSpace.properties
  ~DynamicSpace.refs
  ~DynamicSpace.has_params
  ~DynamicSpace.set_property

Inheritance operations
----------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~DynamicSpace.bases


Child Space operations
----------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~DynamicSpace.spaces
  ~DynamicSpace.named_spaces
  ~DynamicSpace.cur_space


Child Cells operations
----------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~DynamicSpace.cells

ItemSpace operations
---------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~DynamicSpace.itemspaces
  ~DynamicSpace.parameters
  ~DynamicSpace.formula
  ~DynamicSpace.clear_all
  ~DynamicSpace.clear_at
  ~DynamicSpace.node
  ~DynamicSpace.preds
  ~DynamicSpace.succs


Exporting to Pandas objects
---------------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~DynamicSpace.frame
  ~DynamicSpace.to_frame