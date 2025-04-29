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

   ~get_models
   ~get_object
   ~cur_model
   ~cur_space


Creating objects
----------------

.. autosummary::
   :toctree: generated/

   ~new_model
   ~new_space
   ~defcells
   ~uncached
   ~cached


Saving Models
-------------

.. autosummary::
   :toctree: generated/

   ~write_model
   ~zip_model
   ~export_model
   ~read_model


Recursion limit
---------------

.. autosummary::
   :toctree: generated/

   ~get_recursion
   ~set_recursion


Recalculation mode
------------------

.. autosummary::
   :toctree: generated/

   ~get_recalc
   ~set_recalc


IPython configuration
---------------------

.. autosummary::
   :toctree: generated/

   ~setup_ipython
   ~restore_ipython



Tracing the call stack
----------------------

.. autosummary::
   :toctree: generated/

   ~start_stacktrace
   ~stop_stacktrace
   ~get_stacktrace
   ~clear_stacktrace


Error reporting
---------------

.. autosummary::
   :toctree: generated/

   ~get_error
   ~get_traceback
   ~trace_locals
   ~use_formula_error
   ~handle_formula_error
