modelx
======
*Use Python like a spreadsheet!*

.. image:: https://github.com/fumitoh/modelx/actions/workflows/python-package.yml/badge.svg
    :target: https://github.com/fumitoh/modelx/actions/workflows/python-package.yml

.. image:: https://img.shields.io/pypi/pyversions/modelx
    :target: https://pypi.org/project/modelx/

.. image:: https://img.shields.io/pypi/v/modelx
    :target: https://pypi.org/project/modelx/

.. image:: https://img.shields.io/pypi/l/modelx
    :target: https://github.com/fumitoh/modelx/blob/master/LICENSE.LESSER.txt


.. Overview Begin

What is modelx?
---------------
**modelx** is a numerical computing tool that enables you to use
Python like a spreadsheet and build object-oriented models
by defining formulas. modelx is best suited for building models
in such fields as actuarial science, quantitative finance and risk management.

Feature highlights
------------------
**modelx** enables you to interactively
develop, run and debug complex models in smart ways.
modelx allows you to:

- Define cached formulas by writing Python functions
- Quickly build object-oriented models, utilizing inheritance and composition
- Quickly parameterize a set of formulas and get results for different parameters
- Trace formula dependency
- Import and use any Python modules, such as `Numpy`_, `pandas`_, `SciPy`_, `scikit-learn`_, etc..
- See formula traceback upon error and inspect local variables
- Save models to text files and version-control with `Git`_
- Save data such as pandas DataFrames in Excel or CSV files within models
- Auto-document saved models by Python documentation generators, such as `Sphinx`_
- Use Spyder with the Spyder plugin for modelx (spyder-modelx) to interface with modelx

.. _Numpy: https://numpy.org/
.. _pandas: https://pandas.pydata.org/
.. _SciPy: https://scipy.org/
.. _scikit-learn: https://scikit-learn.org/
.. _Git: https://git-scm.com/
.. _Sphinx: https://www.sphinx-doc.org


modelx sites
-------------

========================== ===============================================
Home page                  https://modelx.io
Blog                       https://modelx.io/allposts
Documentation site         https://docs.modelx.io
Development                https://github.com/fumitoh/modelx
Discussion Forum           https://github.com/fumitoh/modelx/discussions
modelx on PyPI             https://pypi.org/project/modelx/
========================== ===============================================


Who is modelx for?
------------------
**modelx** is designed to be domain agnostic, 
so it's useful for anyone in any field.
Especially, modelx is suited for modeling in such fields such as:

- Quantitative finance
- Risk management
- Actuarial science

**lifelib** (https://lifelib.io) is a library of actuarial and
financial models that are built on top of modelx.

How modelx works
----------------
**modelx** exposes its API functions and classes such as Model, Space and Cells to
its users, and the users build their models from those classes, by defining
calculation formulas in the form of Python functions and associating those
calculations with Cells objects.

Below is a very simple working example in which following operations are
demonstrated:

- a new model is created,
- and in the model, a new space is created,
- and in the space, a new cells is created , which is associated with the
  Fibonacci series.

.. code-block:: python

    from modelx import *

    model, space = new_model(), new_space()

    @defcells
    def fibo(n):
        if n == 0 or n == 1:
            return n
        else:
            return fibo(n - 1) + fibo(n - 2)

To get a Fibonacci number for, say 10, you can do::

    >>> fibo(10)
    55
    >>> fibo.series
    n
    0      0
    1      1
    2      1
    3      2
    4      3
    5      5
    6      8
    7     13
    8     21
    9     34
    10    55
    Name: fibo, dtype: int64


Refer to **lifelib** (https://lifelib.io) fo more complex examples.


License
-------
Copyright 2017-2022, Fumito Hamamura

modelx is free software; you can redistribute it and/or
modify it under the terms of
`GNU Lesser General Public License v3 (LGPLv3)
<https://github.com/fumitoh/modelx/blob/master/LICENSE.LESSER.txt>`_.

Contributions, productive comments, requests and feedback from the community
are always welcome. Information on modelx development is found at Github
https://github.com/fumitoh/modelx


.. Overview End


Requirements
------------
* Python 3.6+
* NetwrkX 2.0+
* asttokens
* Pandas
* OpenPyXL
