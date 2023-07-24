modelx module
================

The top-level module :mod:`modelx` includes API functions.
By convention, :mod:`modelx` is assigned to the name ``mx`` in
the global namespace::

    >> import modelx as mx



.. automodule:: modelx

.. _function_reference:


Getting objects
---------------

.. autosummary::
   :toctree: generated/

   ~modelx.get_models
   ~modelx.get_object
   ~modelx.cur_model
   ~modelx.cur_space


Creating objects
----------------

.. autosummary::
   :toctree: generated/

   ~modelx.new_model
   ~modelx.new_space
   ~modelx.defcells


Saving Models
-------------

.. autosummary::
   :toctree: generated/

   ~modelx.write_model
   ~modelx.zip_model
   ~modelx.export_model
   ~modelx.read_model
   ~modelx.restore_model
   ~modelx.open_model


Recursion limit
---------------

.. autosummary::
   :toctree: generated/

   ~modelx.get_recursion
   ~modelx.set_recursion


Recalculation mode
------------------

.. autosummary::
   :toctree: generated/

   ~modelx.get_recalc
   ~modelx.set_recalc


IPython configuration
---------------------

.. autosummary::
   :toctree: generated/

   ~modelx.setup_ipython
   ~modelx.restore_ipython



Tracing the call stack
----------------------

.. autosummary::
   :toctree: generated/

   ~modelx.start_stacktrace
   ~modelx.stop_stacktrace
   ~modelx.get_stacktrace
   ~modelx.clear_stacktrace


Error reporting
---------------

.. autosummary::
   :toctree: generated/

   ~modelx.get_error
   ~modelx.get_traceback
   ~modelx.trace_locals
   ~modelx.use_formula_error
   ~modelx.handle_formula_error
