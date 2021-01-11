
===============================
modelx v0.12.0 (11 Jan 2021)
===============================


This release introduces the following enhancement.

Enhancements
============

.. rubric:: New interface for pandas DataFrame and Series

.. py:currentmodule:: modelx

pandas DataFrame and Series objects referenced in Models and Spaces
can now be written to and read from Excel or CSV text files.

New methods, :meth:`Model.new_pandas<core.model.Model.new_pandas>` and
:meth:`UserSpace.new_pandas<core.space.UserSpace.new_pandas>` are introduced.

By calling either method, the user can create a
:class:`~io.pandasio.PandasData` object that associates
a DataFrame/Series with a file path and file type ("excel" or "csv"),
and assigns the :class:`~io.pandasio.PandasData` object to a Reference.

For example, the script below creates a sample DataFrame ``df``::

    >>> import pandas as pd

    >>> import numpy as np

    >>> index = pd.date_range("20210101", periods=3)

    >>> df = pd.DataFrame(np.random.randn(3, 3), index=index, columns=list("XYZ"))

    >>> df
                       X         Y         Z
    2021-01-01  0.184497  0.140037 -1.599499
    2021-01-02 -1.029170  0.588080  0.081129
    2021-01-03  0.028450 -0.490102  0.025208

The code below creates a :class:`~io.pandasio.PandasData` object containing
the DataFrame created above,
and assigns it to a Reference named ``x`` in ``Model1.Space1``::

    >>> import modelx as mx

    >>> space = mx.new_space()      # Creates Model1.Space1

    >>> space.new_pandas("x", "Space1/df.xlsx", data=df, filetype="excel")

    >>> space.x
    <modelx.io.pandasio.PandasData at 0x15efa565548>

To get the DataFrame, call the :class:`~io.pandasio.PandasData` object
or access its :attr:`~io.pandasio.PandasData.value` property::

    >>> space.x()     # or space.value
                       X         Y         Z
    2021-01-01  0.184497  0.140037 -1.599499
    2021-01-02 -1.029170  0.588080  0.081129
    2021-01-03  0.028450 -0.490102  0.025208

When the model is saved, the DataFrame is written to an Excel file
named `df.xlsx` placed under the `Space1` folder in `model`.

    >>> model.write("model")    # `model` is the parent of `space`

When the model is read back by :func:`modelx.read_model` function,
the DataFrame is read from the file::

    >>> model2 = mx.read_model("model", name="Model2")

    >>> model2.Space1.x()
                       X         Y         Z
    2021-01-01  0.184497  0.140037 -1.599499
    2021-01-02 -1.029170  0.588080  0.081129
    2021-01-03  0.028450 -0.490102  0.025208



