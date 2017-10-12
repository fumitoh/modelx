Tutorial
========
This tutorial aims to introduce core concepts and features of modelx, and
demonstrate how to use modelx by going through some examples.

This tutorial supplements the modelx reference,
which is build from docstrings of the API functions and classes,
and should cover the detailed description of each API element.

Typical workflow
----------------
modelx is a Python package, and you use it by writing a Python script
importing it, as you would normally do with any other Python package.

modelx is best suited for building a complex numerical models composed of
many formulas referencing each other, so when you start from scratch,
the typical workflow would be to first write code for building a model,
and then evaluate the model.

As we are going to see, it takes more than one line of code to build a model,
so it's convenient to use a Python shell that allows you edit and execute
a chunk of code at once for building a model, then get into an interative mode
for letting you examine the model one expression or statement at a time.

IDLE, the Tk/Tcl based simple Python GUI shell that comes with CPython
lets you do that. You can open an editor window, and when the part of
building a model is done, you can press F5 to save and run the script
in a Python shell window where you are prompted to enter Python code to
evaluate the model. Jupyter notebook and many other popular Python shell
environments have similar capability.

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

``new_model()`` is a modelx API function which returns a newly created
model. You can specify the name of the model by passing it as ``name`` argumet
to the function, like ``new_model(name='MyModel')``.
If no name is given as the argument,
the returned model is named automatically by modelx.
Confirm the model is created by ``get_models()`` function, which returns
a mapping of the names of all existing models to the model objects::

   >> get_models()
   {'Model1': <modelx.core.model.Model at 0x447f1b0>}

Creating Spaces
---------------

Now that you have created a brand new model, you can create a space in
the model by calling its ``new_space()`` method.

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
``get_model()`` API function returns
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
Models are to modelx what workbooks are to a spreadsheet program.
Among Model, Space and Cells, Model is the largest concept.
Models contain spaces.
Spaces can be directly contained in a model, but cells cannot.
Cells must be contained in a space.
You can save models to files, and later load them back into memory.

**Getting spaces**

**Global namespace**

Space
-----
Spaces are containers of cells and other spaces.
If a space contain other spaces, the contained spaces are called subspaces
of the containing space.

Spaces can be created in a model by calling the model's ``new_space``
method::

   model = new_model()
   space = model.new_space(name='TheSpace')

Spaces reside directly in models, but they can also reside in other spaces.
Subspaces can be created in a space in the same way as spaces are created
in a model, by calling the spaces's ``new_space`` method::

   subspace = space.new_space(name='TheSubspace')

**Getting spaces**

To get all the spaces that are directly contained in a parent, whether it's
a model or a space, ``spaces`` property

To obtain a space object from a Python script,


Namespace
---------
In addition to serving as containers, spaces have a very important
role of being the namespaces for the formulas of their contained cells.
Spaces have ``namespace`` attribute, which is a mapping of names to objects.

<Insert sample code here>

Formulas are created from Python's function definitions.
Python statements and expressions in functions
are evaluated in the lexical context,
so it matters to Python functions where in the source code they are defined.

However, when modelx create formula objects from Python function definitions,
modelx alters this lexical scoping with dynamic scoping.

When a formula is executed in modelx,
global names that appear in the formula code are resolved based on the
parent's namespace mapping object.

The namespace is composed of other mappings. cells, spaces and refs

Cells
-----
A Cells cannot reside in multiple Spaces at the same time.
A Cells can be moved from one Space to another.

References
----------
Often times you want access from cells formulas in a space to other objects
than cells in the same space.
References are names bound to arbitrary objects that are accessible from
within the same space.


As a cell container
-------------------

Static subspaces
----------------
As previously mentioned, spaces can be created in another space.
Spaces in another space are called subspaces of the containing space.

You can obtain a subspace as an attribute of the parent space,
or by accessing the parent space's ``spaces``
attribute::

  >> parent.a_subspace

  >> parent['a_subspace']




Space inheritance
-----------------
Space inheritance is a concept analogous to class inheritance
in object-oriented programming languages.
By making full use of space inheritance, you can minimize duplicated
formula definitions, keeping your model organized and transparent
and maintain model integrity.

Inheritance lets one space use(inherit) other spaces, as base spaces.
The inheriting space is called a derived space of the base spaces.
The cells in the base spaces are copied automatically in the derived space.
In the derived space, formulas of cells from base spaces can be overridden.
You can also add cells to the derived space, that do not exist in any
of the base spaces.

A space can have multiple base spaces. This is called multiple inheritance.
The base spaces can have their base spaces, and derived-base relationships
between spaces make up a directional graph of dependency.
In case of multiple inheritance, we need a way to order base spaces to
determine the priority of base spaces.modelx uses
C3 superclass linearization algorithm (a.k.a C3 Method Resolution Order or MRO)
for ordering the base spaces. Python uses the C3 MRO for obtaining the oder
of which method should be inherited.
https://www.python.org/download/releases/2.3/mro/

https://en.wikipedia.org/wiki/C3_linearization

**Inheritance Example**

Let's see how inheritance works by walking through an example of
pricing life insurance policies.
First, you create a very simple life model as a space and name it ``Life``.
You populate the space with cells that calculate the number of death
and remaining lives by age.

Then to price a term life policy, you derive a ``TermLife`` space from
the ``Life`` space, and add some cells to calculate death benefits
paid to the insured, and their present value.

Next, you want to model an endowment policy. Since the endowment policy
pays out a maturity benefit in addition to the death benefits covered by the
term life policy, you derive a ``Endowment`` space from ``TermLife``,
and make a residual change to the benefit cells.


**Creating a life model**

Below is a mathematical representation of the life model we'll
build as a ``Life`` space.

.. math::
   &l(x) = l(x - 1) - d(x - 1)\\
   &d(x) = l(x) * q


where, :math:`l(x)` denotes the number of lives at age x,
:math:`d(x)` denotes the number of death occurring between the age x
and age x + 1, :math:`q` denotes the annual mortality rate
(for simplicity, we'll assume a constant mortality rate of 0.003 for all ages
for the moment.)
One letter names like l, d, q would be too short for real world practices,
but we use them here as they often appear in classic actuarial textbooks.
Yet another simplification is, we set the starting age of x at 50, just
to get output shorter. As long as we use a constant mortality age,
it shouldn't affect the results whether the starting age is 0 or 50.
Below the modelx code for this life model::

   model = new_model()
   life = model.new_space(name='Life')

   @defcells
   def l(x):
       if x == 50:
           return 100000
       else:
           return l(x - 1) - d(x - 1)

   @defcells
   def d(x):
       return l(x) * q

   @defcells
   def q():
       return 0.003

Let's play around with this life model for a little bit.


Dynamic spaces
--------------
In many cases, you want to apply a set of calculations in a space,
or a tree of spaces, to differrent data sets.
You can achieve that by applying the space inheritance on dynamic spaces.

Dynamic spaces are parametrized spaces that are created on-the-fly when
requested through call(``()``) or subscript(``[]``) operation on their parents.

To define dynamic spaces in a parent, whether it's a model or a space,
You create the parent with a parameter function whose signature is
used to define space parameters. The paremter function should return,
if any, a mapping of parameter names to their arguments,
to be pass on to the ``new_space`` method, when the dynamic spaces
are created.

To see how this works, let's continue with the previous example.




Dynamic spaces of a base space are not passed on to the derived spaces.
When a space is derived from a base space that has dynamically created
subspaces, those dynamically created subspaces themselves are not passed
on to the derived spaces. Instead, the parameter function of the base
space is inherited, so subspaces of the derived space are created upon
call(using ``()``) or subscript (using ``[]``) operators
the derived space with arguments.

Reading Excel files
-------------------

Exporting to Pandas objects
---------------------------
