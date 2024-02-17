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
  ~Model.path
  ~Model.model
  ~Model.parent
  ~Model.allow_none
  ~Model.properties
  ~Model.spaces
  ~Model.refs
  ~Model.iospecs
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
  ~Model.export


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

  ~Model.new_pandas
  ~Model.new_module
  ~Model.new_excel_range
  ~Model.update_pandas
  ~Model.update_module
  ~Model.get_spec
  ~Model.del_spec


Run operations
--------------------

.. autosummary::
  :toctree: generated/
  :template: mxbase.rst

  ~Model.generate_actions
  ~Model.execute_actions
