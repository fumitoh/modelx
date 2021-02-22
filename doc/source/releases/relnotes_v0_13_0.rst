
===============================
modelx v0.13.0 (23 Feb 2021)
===============================

This release introduces the following enhancements.

* `Introduction of the new_module method`_
* `Direct assignment of DataFrame/Series by new_pandas`_

Enhancements
============

Introduction of the new_module method
-------------------------------------

modelx has allowed to reference modules from within Models
just by assigning modules to References.
For example, to reference `numpy`_ from a Space,
the user can just assign the module to a Reference::

    >>> import numpy as np

    >>> space.np = np

This works for modules in the Python standard library and in third-party packages,
such as `math`_ and `numpy`_. When Models
referencing these modules are saved, those modules themselves are
not saved within the Models but the names of the modules are.
When the Models are read back,
the Python interpreter is able to find
those modules thanks to Python's import system, and the modules
are properly referenced again.

However, the user would also want to reference modules written
by the user (user modules). User modules are usually not
installed as packages in the Python's import system.
Rather, they are located in the user's current directory.
Referencing such modules in Models by the same assignment operation is problematic,
because when such Models are saved and read back, the current directory
may have changed or the referenced modules may have been moved or deleted
by the user.

To make user modules portable,
the :meth:`Model.new_module<modelx.core.model.Model.new_module>` and
:meth:`UserSpace.new_module<modelx.core.space.UserSpace.new_module>`
methods are introduced. The methods allow the user
to define a Reference, assign a user module to the Reference, and
associate the user module with a source file of the module in
the model directory, so that the module's source code can be saved
within the containing model.

.. rubric:: Example

Suppose the following code is saved in "sample.py" in the
current directory.

.. code-block:: python

    def triple(x)
        return 3 * x

The code below creates a Reference named "foo" in ``space``::

    >>> space.new_module("foo", "modules/sample.py", "sample.py")

The module becomes accessible as ``foo`` in ``space``::

    >>> space.foo
    <module 'sample' from 'C:\\path\\to\\samplemodule.py'>

    >>> @mx.defcells(space)
    ... def bar(y):
            return foo.triple(y)

    >>> space.foo.bar(3)
    9

Let ``model`` be the ultimate parent model of ``space``. The next code
creates a directory named "model" under the current directory,
and within the "model" directory, the module is saved
as "sample.py" in the "modules" sub-directory of the "model" dir,
as specified by the ``path`` parameter to this method.

    >>> model.write("model")


Direct assignment of DataFrame/Series by new_pandas
----------------------------------------------------------

:meth:`UserSpace.new_pandas<modelx.core.space.UserSpace.new_pandas>`
,the previously introduced method,
as well as :meth:`Model.new_pandas<modelx.core.model.Model.new_pandas>` now has
a new default behaviour of assigning
a pandas DataFrame/Series object passed as the ``data`` parameter
to a Reference,
instead of assigning the PandasData object associated with the pandas object.
By passing ``False`` to the
newly introduced ``expose_data`` parameter,
the default behaviour can be altered to be consistent with the previous
behavior, which is to assign
the PandasData object to the Reference instead of
the pandas object itself.


Backward Incompatible Changes
=============================

* Models saved by the previous modelx version (v0.12.1) works perfectly
  fine with this version. However, the default behaviour of
  :meth:`UserSpace.new_pandas<modelx.core.space.UserSpace.new_pandas>`
  and :meth:`Model.new_pandas<modelx.core.model.Model.new_pandas>`
  has changed and they assign
  pandas objects(`DataFrame`_ or `Series`_) to References directly instead of
  assigning :class:`~modelx.io.pandasio.PandasData` objects.
  If ``False`` is given to the ``exposed_data`` parameter,
  the behaviour of the methods are consistent with the previous version,
  which is to assign :class:`~modelx.io.pandasio.PandasData` objects
  rather than pandas objects(`DataFrame`_ or `Series`_) themselves.

.. _math: https://docs.python.org/3/library/math.html
.. _numpy: https://numpy.org/
.. _pandas: https://pandas.pydata.org/
.. _DataFrame: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html
.. _Series: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.html
