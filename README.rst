modelx
======
*Unleash your spreadsheet models!*

What is modelx?
---------------
modelx is a Python package for performing complex calculations by creating
models composed of structured data and formulas written in the form of Python
functions. You can think of it as a multidimensional
version of spreadsheet, but it’s so much more!

How modelx works
----------------
modelx exposes its API functions and classes such as Model, Space and Cells to
its users, and the users build their models from those classes, by defining
calculation formulas in the form of Python functions and associating those
calculations with Cells objects.

Below is a very simple working example in which:

- a new model is created,
- and in the model, a new space is created,
- and in the space, a new cells is created , which is associated with the
  Fibonacci series.

.. code-block:: python

    from modelx import *

    model = create_model()
    space = model.create_space()


    @defcells
    def fibo(n):

        if n == 0 or n == 1:
            return n
        else:
            return fibo(n - 1) + fibo(n - 2)

To get a Fibonacci number for, say 10, you can do::

    >> fibo(10)
    55
    >> fibo.series
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


Feature highlights
------------------
You may not see the whole point of usig modelx as the example above is
a simple one just to be meant for illustrating its fundamental mechanism,
modelx comes with features that enable users to build and manipulate
more complex models in smart ways:

- Cells containing formulas and data
- Dynamic scoping for evaluating formulas
- Cells graph to track cells interdependency
- Spaces to organize cells by related calculations
- Sub-spacing (having nested spaces within spaces)
- Space inheritance
- Dynamic parametrized spaces created automatically
- Saving to / loading from files
- Conversion to Pandas objects
- Reading from Excel files

Who is modelx for?
------------------
modelx is designed to be domain agnostic.
The modelx was created by an actuary to be used as a base tool to develop
actuarial projection models for light-weight tasks,
but it is intentionally designed to eliminate domain specific features
so that potential audience for modelx can be anyone who needs to develop
complex models of any sorts that are too much to deal with by spreadsheets.


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


Free software
-------------
modelx is free software; you can redistribute it and/or
modify it under the terms of
`GNU General Public License v3 (GPLv3)
<https://github.com/fumitoh/modelx/blob/master/LICENSE.txt>`_.

Contributions, productive comments, requests and feedback from the community
are always welcome. Information on modelx development is found at Github
https://github.com/fumitoh/modelx


History
-------
modelx was originally conceived and written by Fumito Hamamura
and it was first released in October 2017.


Requirements
------------
* Python 3.4+
* OpenPyXL
* Pandas