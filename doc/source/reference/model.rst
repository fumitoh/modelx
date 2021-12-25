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
  ~Model.dataspecs
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
  ~Model.zip
  ~Model.backup
  ~Model.save


Child Space operations
----------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.cur_space
  ~Model.new_space
  ~Model.clear_all
  ~Model.import_module
  ~Model.new_space_from_csv
  ~Model.new_space_from_excel
  ~Model.new_space_from_module
  ~Model.new_space_from_pandas


Reference operations
--------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.new_excel_range
  ~Model.new_pandas
  ~Model.new_module
  ~Model.update_pandas
  ~Model.update_module
