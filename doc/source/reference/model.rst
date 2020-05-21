Model
=======================

.. currentmodule:: modelx.core.model

.. autoclass:: Model


Model properties
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.name
  ~Model.fullname
  ~Model.doc
  ~Model.model
  ~Model.parent
  ~Model.allow_none
  ~Model.properties
  ~Model.spaces
  ~Model.refs
  ~Model.tracegraph

Model operations
----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.close
  ~Model.rename
  ~Model.set_property


Saving operations
-----------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.write
  ~Model.backup
  ~Model.save


Child Space operations
----------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.cur_space
  ~Model.import_module
  ~Model.new_space
  ~Model.new_space_from_csv
  ~Model.new_space_from_excel
  ~Model.new_space_from_module
  ~Model.new_space_from_pandas
