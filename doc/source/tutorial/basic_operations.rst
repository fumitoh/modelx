Basic Operations
===================

Up to the previous section, we've learned how to build and run models
using Spyder IDE, by going through some basic examples.
In this section, you will learn
how to perform modelx's basic operations from the Python interpreter,
such as creating Models, Spaces, Cells and References
and evaluating Formulas.

Code snippets in this section are assumed to be executed interactively
from IPython console,
but the snippets can also be written in Python scripts and
can be run as Python programs.

This tutorial supplements modelx reference,
which is build from docstrings of the API functions and classes.
The reference should cover the details of each API element,
which may not be fully explained in this tutorial.

.. contents:: Contents
   :local:

Importing modelx
----------------

To start using modelx, import the modelx module by the ``import`` statement.
By convention, import the module as an abbreviated name, ``mx``::

    >>> import modelx as mx

By doing so, modelx API functions becomes accessible through ``mx``.
The entire list of modelx API functions can be found in
the :doc:`/reference/functions` section in the *Reference Guide*.
All the sample scripts in this tutorial assume that the modelx module
is imported as ``mx``:


.. note::

    You could alternatively import all the API functions directly into
    ``__main__`` module by ``import modelx as *``,
    But this is not a good practice when you write in Python in general.
    If you want to import an API function directly,
    it is advisable to import it individually, for example,
    ``from modelx import defcells``


Basic Model operations
-----------------------

As introduced :ref:`previously <overview-of-core-modelx-objects>`,
Models are the top level objects that contain other types of modelx
objects in hierarchical tree structures.
Models are to modelx what workbooks are to a spreadsheet program.
Models can be saved to files and loaded back again.


Creating Models
^^^^^^^^^^^^^^^^

When *modelx* is imported into a Python session for the first time,
no Model exists in the session.

To create a new Model with a name, call :py:func:`~modelx.new_model`.
:py:func:`~modelx.new_model` returns a new Model with
the name passed to its ``name`` parameter.
For example, the statement below creates a Model named *MyModel*
and assigns it to a global variable ``model``.

    >>> model = mx.new_model(name="MyModel")

If no name is passed to the function,
the returned model is named automatically by modelx, such as ``Model1``.


Retrieving Models
^^^^^^^^^^^^^^^^^^

What happens if you accidentally delete ``model``,
the variable bound to *MyModel*?
*MyModel* itself is not deleted, and you can get it back by
accessing ``mx``, the modelx module.

From Python 3.7 onwards, Models can be obtained as attributes of
the *modelx* modules by their names. Continuing from the previous example,
the Model *MyModel* is available as::

    >>> mx.MyModel
    <Model MyModel>


The :attr:`~modelx.models` attirubte of the *modelx* module returns
a :obj:`dict` containing all the existing models associated with their names::

   >>> mx.models
   {'Model1': <Model Model1>}

With Python 3.6, use :func:`~modelx.get_models` function instead of instead of
:attr:`~modelx.models`::

   >>> mx.get_models()
   {'Model1': <Model Model1>}


.. _the-current-model:

The current Model
^^^^^^^^^^^^^^^^^

When a Model is created, read or restored, the Model is held
as the *current* Model. modelx having the current model is somewhat
analogous to how a spreadsheet program has the *active* workbook.


The :py:func:`~modelx.cur_model` function
returns the current model when no argument is passed::

    >>> mx.cur_model()
    <Model Model1>

If a Model or its name is passed to :py:func:`~modelx.cur_model`,
then the current Model is changed to the Model.


Deleting Models
^^^^^^^^^^^^^^^

To delete a model, call the :py:meth:`~modelx.core.model.Model.close` method
of the Model.


Saving and reading Models
^^^^^^^^^^^^^^^^^^^^^^^^^

Models can be saved into files in a directory tree by the
:py:func:`~modelx.write_model` function. Let ``model`` be
a Model object. The code below saves the Model to the specified path::

    >>> mx.write_model(model, r"C:\Users\path\to\model")

The path can also be expressed relative to the current directory.
The *model* directory contains a ``__init__.py`` file and
a tree of sub directories
that correspond to UserSpaces in ``model``.
In each sub-directory, there is a ``__init__.py`` file.
The ``__init__.py`` file is a pseudo-script written in Python.
The Formulas of Cells contained in the UserSpace
are written in ``__init__.py`` as Python functions,
as well as other information, such as the Formula of the UserSpace if any,
and the metadata of contained References.
Although ``__init__.py`` is not meant to be interpreted by Python directly,
it's a semantically correct Python script,
which makes it possible to import the sub-directory as if it's a
Python package. This allows Sphinx, Python's documentation generator
to auto-generate a model document from the docstrings in the ``__init__.py``
files.

The :py:meth:`~modelx.core.model.Model.write` method performs
the same as the :py:func:`~modelx.write_model` function on itself.

To save a Model in a single zip file, use :py:func:`~modelx.zip_model`
or :py:meth:`~modelx.core.model.Model.zip` instead. The contents of
the zip file is the same as the contents in the directory tree saved
by :py:func:`~modelx.write_model` or :py:meth:`~modelx.core.model.Model.write`.

These functions and methods save input values of Cells,
but do not save calculated values.
They also do not save :class:`~modelx.core.space.DynamicSpace` objects,
except for those that
have input values.
To save Models with calculated values and DinamicSpaces,
use the :py:func:`~modelx.core.model.Model.backup` method.


Use :py:func:`~modelx.read_model`
to read a saved Model, whether it's saved as a zip file or a directory tree::

    >>> model = mx.read_model(r"C:\Users\path\to\model")

If a model with the same name already exsits, the existing model's name is
suffixed with ``_BAKn`` where ``n`` is an integer.


Backup and restore
^^^^^^^^^^^^^^^^^^

There is another way to save Models. The :meth:`~modelx.core.model.Model.backup`
method writes the Model to a binary file.
Unlike :py:func:`~modelx.write_model`,
the :meth:`~modelx.core.model.Model.backup` method also saves
calculated values and DinamicSpaces.

The :py:func:`~modelx.restore_model` is used
to restore a Model backed up by the method.

Backing up a Model is faster than writing or zipping the Model.
However, the backed-up Model is a binary file and not human-readable.
It may not be restored by a different version of modelx.
It also may not be restored on
Python environments other than the one that the Model is backed up on,
so it is advisable to back up Models only for saving them temporarily.


Basic Space operations
-----------------------

*Spaces* are modelx objects that serve as containers, separating
contents in a Model into components.
A Space can be created directly in a Model or can be nested in another Space,
forming a tree of Spaces. Spaces are a lot like folders (or what
Linux users would call directories), because both are
for organizing their contents in tree structures.

Another important role of a Space is to provide a namespace for
the Formulas in it. We'll get to this point later in more details.

There are a few types of Spaces. The type of Space that the user can
create explicitly is :class:`~modelx.core.space.UserSpace`.

Creating a UserSpace
^^^^^^^^^^^^^^^^^^^^^

To create a :class:`~modelx.core.space.UserSpace` in a Model, the
:py:meth:`Model.new_space <modelx.core.model.Model.new_space>` method
is used. The code below creates a new UserSpace named 'MySpace',
and assigns it to a global variable, ``space``::

    >>> space = model.new_space('MySpace')

``model`` is called the *parent* of *MySpace*.
Any Space has one and only one parent.
A UserSpace can also be created in another UserSpace.
To do so, call the :meth:`~modelx.core.space.UserSpace.new_space` method
of the other UserSpace.
In this case, the parent of the UserSpace is the other UserSpace.
For example, the code below creates a UserSpace
named 'SubSpace' in *MySpace* just created by the code above::

    >>> subspace = space.new_space('SubSpace')

If you don't pass any name to the method, then
modelx gives the new UserSpace a name, such as 'Space1'.

There is also a function, :py:func:`~modelx.new_space`.
This function creates a new UserSpace
in :ref:`the current Model<the-current-model>`.
If there is no current Model, then modelx creates one
and assigns it to the current Model.


Retrieving UserSpaces
^^^^^^^^^^^^^^^^^^^^^

UserSpaces can be obtained by their names as if they are attributes
of their parents.

To get all the spaces in a model mapped to their names,
you can check ``spaces`` property of the model::

   >>> model.spaces
   mappingproxy({'Space1': <Space Space1 in Model1>})

The returned MappingProxy objects acts like an immutable dictionary, so you can
get *Space1* by ``model.spaces['Space1']``. You can see the returned space is
the same object as what is referred as ``space``::

   >>> space is model.spaces['Space1']
   True

To get one space, its name is available as an attribute of the containing model::

   >>> model.Space1
   <Space Space1 in Model1>


The current Space
^^^^^^^^^^^^^^^^^^

When you create a new UserSpace, it's held as the *current* Space by modelx,
and when next time you create a Cells by :func:`~modelx.defcells` decorator
without specifying its parent, the new Cells is created in the current Space.

You can get the current Space of the current Model by calling
:py:func:`~modelx.cur_space` without arguments.


Deleting UserSpaces
^^^^^^^^^^^^^^^^^^^

UserSpaces can be deleted by the **del** statement, like this way::

    >>> del model.Space1

or this way::

    >>> del model.spaces["Space1"]

Either statement works the same.

Basic Cells operations
-----------------------

Cells objects are for defining calculations and storing values.
Cells are to modelx what cells are to a spreadsheet.
However, as the name "Cells" indicates, a Cells object
may have multiple values for the associated *Formula*.
The Formula of a Cells is defined by an underlying Python function.
If the Formula does not have parameters,
the Cells can only have one value at most.
If the Formula has parameters, the Cells can have multiple values
associated with arguments passed to the Formula.


Creating Cells and defining their Formulas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are a few ways to create a cells object and defiene the formula
associated with the cells. The quickest way is to define
a python function with :func:`~modelx.defcells` decorator.

.. code-block:: python

    model, space = mx.new_model(), mx.new_space()

    @mx.defcells
    def fibo(n):
        if n == 0 or n == 1:
            return n
        else:
            return fibo(n - 1) + fibo(n - 2)


By :func:`~modelx.defcells` decorator, the name ``fibo`` in this scope points
to the Cells object that has just been created from the formula definition.

By this definition, the cells is created in the current Space in the current
Model.
As explained earlier,
modelx keeps the last operated model as the current Model, and
the last operated Space for each model as the current space.
:py:func:`~modelx.cur_model` API function returns
the current model,
and :py:meth:`~modelx.core.model.Model.cur_space` method of a model holds
its current space.

To specify the space to create a cells in, you can pass the space object as
an argument to the :func:`~modelx.defcells` decorator. Below is the same as
the definition above, but explicitly specifies in what space to define
the cell::

   @mx.defcells(space)
   def fibo(n):
       if n == 0 or n == 1:
           return n
       else:
           return fibo(n - 1) + fibo(n - 2)

There are other ways to create cells by :func:`~modelx.defcells`.
Refer to the :py:func:`~modelx.defcells` section in the reference manual
for the details.

Another way to create a cells is to use Space's
:py:meth:`~modelx.core.space.UserSpace.new_cells` method.
The method creates a new cells that has a Formula defined by
the function passed to its ``formula`` paramter::

   >>> def fibo2(n):
           return fibo2(n-1) + fibo2(n-2) if n > 0 else n

   >>> space.new_cells(formula=fibo2)

The ``formula`` parameter can either be a function object, or a string
of function definition.


Getting Cells
^^^^^^^^^^^^^^

Similar to spaces in a model contained in the ``spaces`` property of the model,
cells in a space are associated with their names and
contained in the ``cells`` property of the model::

   >>> fibo is space.cells['fibo']
   True

As you can get a space in a model by attribute access with ``.``,
you can get a cells in a space by accessing the space attribute
of the cells name with ``.``::

   >>> space.fibo
   <Cells fibo(n) in Model1.Space1>

   >>> fibo is space.fibo
   True


Getting Values
^^^^^^^^^^^^^^^

The cells ``fibo`` does not have values yet right after it is created.
To get cells' value for a
certain argument, simply call ``fibo`` with the paratmer in parenthesis or
in squre brackets::

   >>> fibo[10]
   55
   >>> fibo(10)
   55

Its values are calculated automatically by the associated formula,
when the cells values are requested.
Note that values are calculated not only for the specified argument,
but also for the arguments that recursively referenced by the formula
in order to get the value for the specified argument.
To see for what arguments values are calculated, export ``fibo`` to a Pandas
Series object. (You need to have Pandas installed, of course.)::

   >>> fibo[10]
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

Since ``fibo[10]`` refers to ``fibo[9]`` and ``fibo[8]``,
``fibo[9]`` refers to ``fibo[8]`` and ``fibo[7]``, and
the recursive reference goes on until it stops and ``fibo[1]`` and ``fibo[0]``,
values of ``fibo`` for argument ``0`` to ``10`` are
calculated by just calling ``fibo[10]``.

.. note::

   It is important to understand in what namespace cells formulas
   are executed. Unlike Python functions, the global namespace
   of a cells formula has nothing to do with where in the source files
   the formula is defined. The names in the formula are resolved
   in the namespace associated with the cells' parent space.
   In that namespace, available names are cells contained in the space,
   spaces contained in the space (i.e. the subspaces of the space)
   and "references" accessible in the space.


Clearing Values
^^^^^^^^^^^^^^^^

To clear cells values, you can use ``clear()`` method. Below shows
what happens when the value of ``fibo`` at n = 5 is cleared::

  >>> fibo.clear(5)
  >>> fibo.series
  n
  0    0
  1    1
  2    1
  3    2
  4    3
  Name: fibo, dtype: int64

As you can see, not only at n = 5, but also for n = 6 to 10
values of ``fibo`` are cleared. This is because the calculations of
``fibo[6]`` to ``fibo[10]`` depend on the value of ``fibo[5]``.
Dependent values are cleared all together with the specified value.

To clear all values, simply call ``clear()`` witthout arguments::

  >>> fibo.clear()
  >>> fibo.series
  Series([], Name: fibo, dtype: float64)

Setting Values
^^^^^^^^^^^^^^^

Other than letting the formula calculate cells values, you can
input cells values manually by the set item (``[] =``) operation.
If the cells already has a value at the specified parameter value,
then the values of dependent cells are cleared first, then the
specified value is assigned::

  >>> fibo[10]
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

  >>> fibo[5] = 0
  >>> fibo.series
  n
  0    0
  1    1
  2    1
  3    2
  4    3
  5    0
  Name: fibo, dtype: int64

