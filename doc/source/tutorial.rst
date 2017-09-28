Tutorial
========

This tutorial introduces the basic concepts and features of the modelx
Python package by going through some simple examples.


Model, Space and Cells
----------------------
Before taking a look at the very first example, you might want to
have an idea on what Model, Space and Cells are, as those three types
of objects are central to modelx.

Model, Space and Cells are to modelx
what workbook, worksheet and cells are to a spreadsheet program respectively,
although there are differences.
The diagram below illustrates containment
relationship between those objects.

.. figure:: images/ObjectContainment.png

   Model, Space and Cells


A model is a unit of work. It can be saved to a file and loaded again.
A model contains spaces. In turn, spaces can contain cells and also other
spaces (subspaces). Spaces also serves as the namespace for contained
cells but we'll get to this later.

A Cells can have a formula that calculates the cells' values, just like
spreadsheet cells can have formulas. Cells values are either calculated
by the formula or assigned as an input. We will learn how to define
cells formulas through the examples soon.


First example
-------------
We'll start by talking a closer look at the simple example we saw
in the overview section.

.. literalinclude:: example_overview.py
   :lines: 1-13

To start using modelx, import the package by the import statement, as is the
case with any other package.

.. literalinclude:: example_overview.py
   :lines: 1

By doing so, you get to use modelx API functions in ``__main__`` module.
If you're not comfortable with importing modelx API functions directly into
the global namespace of ``__main__`` module, you can alternatively import
``modelx`` as an abbreviated name, such as ``mx``, for example::

    import modelx as mx

in which case you can use modelx API functions prepended with ``mx.``.
We'll assume importing ``*`` in this tutorial, but be reminded that this
is not a good practice when you write Python modules.

Creating Models
---------------

Then on the next line, we are creating a new Model object:

.. literalinclude:: example_overview.py
   :lines: 3

``create_model()`` is a modelx API function which returns a newly created
model. You can specify the name of the model by passing it as ``name`` argumet
to the function, like ``create_model(name='MyModel')``.
If no name is given as the argument,
the returned model is named automatically by modelx.
Confirm the model is created by ``get_models()`` function, which returns
a mapping of the names of all existing models to the model objects::

   >> get_models()
   {'Model1': <modelx.core.model.Model at 0x447f1b0>}

Creating Spaces
---------------

Now that you have created a brand new model, you can create a space in
the model by calling its ``create_space()`` method.

.. literalinclude:: example_overview.py
   :lines: 4

Just as with the models, the name of the space can be specified by
passing it to the method ``name`` argument, otherwise the space gets its
name by modelx.

Getting Spaces
--------------

To get all spaces in a model mapped to their names,
you can check ``spaces`` property of the model::

   >> model.spaces
   mappingproxy({'Space1': <modelx.core.space.Space at 0x4452790>})

The return MappingProxy objects acts like an immutable dictionary, so you can
get Space1 by ``model.spaces['Space1']``. You can see the returned space is
the same object as what is referred as ``space``::

   >> space is model.spaces['Space1']
   True


Creating Cells
--------------
There are a few ways to create a cells object and defiene the formula
associated with the cells. As seen in the example above,
one way is to define a python function with ``defcells`` decorator.

.. literalinclude:: example_overview.py
   :lines: 7-13

By this definition, the cells is created in the current space in the current
model. modelx keeps the last operated model as the current model, and
the last operated space for each model as the current space.
``get_currentmodel()`` API function returns
the current model, and ``currentspace`` property of a model holds
its current space.

To specify the space to create a cells in, you can pass the space object as
an argument to the ``defcells`` decorator. Below is the same as
the definition above, but explicitly specifies in what space to define
the cell::

   @defcells(space=space)
   def fibo(n):

       if n == 0 or n == 1:
           return n
       else:
           return fibo(n - 1) + fibo(n - 2)

Getting Cells
-------------
Similar to spaces in a model contained in the ``spaces`` property of the model,
cells in a space are associated with their names and
contained in the ``cells`` property of the model::

   >> fibo is space.cells['fibo']
   True

There is another way of accessing cells. You can just use `.` with cells names,
just like accessing the spaces's attribute::

   >> space.fibo
   <modelx.core.cells.Cells at 0x51ed090>
   >> fibo is space.fibo
   True


Getting Cells Values
--------------------
The cells ``fibo`` does not have values yet right after it is created.
To get cells' value for a
certain parameter, simply call ``fibo`` with the paratmer in parenthesis or
in squre brackets::

   >> fibo[10]
   55
   >> fibo(10)
   55

Its values are calculated automatically by the associated formula,
when the cells values are referenced.
Note that values are calculated not only for the specified parameter,
but also for the parameters that recursively referenced by the formula
in order to get the value for the specified parameter.
To see for what parameters values are calculated, export fibo to a Pandas
Series object. (You need to have Pandas installed, ofcourse.)::

   >> fibo[10]
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

Since ``fibo[10]`` refers to ``fibo[9]`` and ``fibo[8]``,
``fibo[9]`` refers to ``fibo[8]`` and ``fibo[7]``, and
the recursive reference goes on until it stops and ``fibo[1]`` and ``fibo[0]``.
by just calling ``fibo[10]``, values for the parameters from 0 to 10 are
calculated.

Model
-----
Container of spaces
Saving models

Space
-----
When you have many cells, you start to feel the need for a mechanism to better
manage variable names referred in your cells formulas.
At the same time, you may also want to refer to a set of cells,
so that you can apply a set of calculation to many homogenous data sets.

ModelX is designed to fulfill those needs as it has Space objects.
A Space is a container of Cells. It has its own name space.
Names referred to in Formulas associated with Cells that belong to
a Space are looked up in the Space’s name space.

Even up until now, you’re using Default Space implicitly,
as all cells defined with `@defcells` decorator belong to the Default Space.

A Cells cannot reside in multiple Spaces at the same time.
A Cells can be moved from one Space to another.

As a cells namespace
--------------------

As a cell container
-------------------

References
----------

Subspacing
----------

Dynamic subspaces
-----------------

When the parent space of dynamic spaces

When a space is derived from a base space that has dynamically created
sub-spaces, those dynamically created spaces themselves are not passed
on to the derived spaces. Instead, the sub-space constructor of the base
space is inherited, so sub-spaces of the derived space are created upon
calling (using () operator) or subscripting (using [] operator)
the derived space with arguments.

Dynamic spaces are not passed on to the derived spaces.

Inheritance
-----------

Importing from Excel
--------------------

