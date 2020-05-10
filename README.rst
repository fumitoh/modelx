modelx
======
*Use Python like a spreadsheet!*

.. image:: https://travis-ci.org/fumitoh/modelx.svg?branch=master
    :target: https://travis-ci.org/fumitoh/modelx

.. image:: https://img.shields.io/pypi/pyversions/modelx
    :target: https://pypi.org/project/modelx/

.. image:: https://img.shields.io/pypi/v/modelx
    :target: https://pypi.org/project/modelx/

.. image:: https://img.shields.io/pypi/l/modelx
    :target: https://github.com/fumitoh/modelx/blob/master/LICENSE.LESSER.txt


.. Overview Begin

What is modelx?
---------------
**modelx** is a Python package to build object-oriented models
containing formulas and values to carry out complex calculations.
You can think of it as a hierarchical and multidimensional extension
of spreadsheet, but there's so much more to it!

Feature highlights
------------------
**modelx** comes with features that enable users to interactively
develop, run and scrutinize complex models in smart ways:

- Only little Python knowledge required
- Model composed of a tree of Spaces containing Cells
- Cells containing formulas and data
- Dynamic name binding for evaluating formulas within a Space
- Space inheritance
- Dynamic parametrized spaces created interactively
- GUI as Spyder plugin (spyder-modelx)
- Cells graph to track cells interdependency
- Saving to / loading from files
- Conversion to Pandas objects
- Reading from Excel files

Who is modelx for?
------------------
**modelx** is designed to be domain agnostic.

The modelx was created by actuary, and its primary use is to develop
actuarial projection models. **lifelib** (https://lifelib.io) is a
library of actuarial models that are built on top of modelx.

However, modelx is intentionally designed to eliminate domain specific features
so that potential audience for modelx can be wider than actuaries,
whoever needs to develop
complex models of any sorts that are too much to deal with by spreadsheets.

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


Python and modelx
-----------------
Aside from modelx being a Python package and written entirely in Python,
modelx utilizes Python in that it lets users define formulas by writing
Python functions and converting it to modelx formulas.
However, there is a critical difference between how Python functions are
interpreted by Python and how modelx formulas are interpreted by modelx.

Python employs lexical scoping, i.e. the namespace in which function code is
executed is determined by textual context. The global namespace of a
function is the module that the function is defined in.
In contrast, the evaluation of modelx formulas is based on dynamic scoping.
Each Cells belongs to a space, and the space has associated namespace (a mapping
of names to objects). The formula associated with the cells is
evaluated in that namespace. So, what module a formula is defined (in the
form of a Python function) does not affect the result of formula evaluation.
It is what space the cells belongs to that affects the result.


License
-------
Copyright 2017-2020, Fumito Hamamura

modelx is free software; you can redistribute it and/or
modify it under the terms of
`GNU Lesser General Public License v3 (LGPLv3)
<https://github.com/fumitoh/modelx/blob/master/LICENSE.LESSER.txt>`_.

Contributions, productive comments, requests and feedback from the community
are always welcome. Information on modelx development is found at Github
https://github.com/fumitoh/modelx


Development State
-----------------

With the release of modelx version 0.1.0 in December 2019,
the author of modelx will try to consider maintaining
backward compatibility to a limited extent
in developing future releases of modelx.
Especially, he will try to make it possible to read
models written to files by one version's ``write_model``,
by ``read_model`` of the next version of modelx.
However, models saved by ``Model.save`` method may not be opened by
``open_model`` method.
Overall, modelx is still in its early alpha-release stage,
and its specifications may change without consideration
on backward compatibility.

.. warning::

   If you have embedded modelx in actuarial production processes,
   then it is encouraged to connect with the author
   `on linkedin <https://www.linkedin.com/in/fumito-hamamura>`_
   or `on github <https://github.com/fumitoh>`_ ,
   as modelx features you rely on might change or be removed in future releases
   without the author knowing those features are in use.

History
-------
modelx was originally conceived and written by Fumito Hamamura
and it was first released in October 2017.

.. Overview End


Requirements
------------
* Python 3.6+
* NetwrkX 2.0+
* asttokens
* Pandas
* OpenPyXL
