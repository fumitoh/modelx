Evaluating Formulas
====================

Unlike a program written in a programming language,
a *modelx* Model does not have a single entry point, such as the *main* function
in *C*. And modelx also differs from Excel, in a sence that
modelx does not populate its Model with calculated values upon
opening the Model. modelx evaluates a Formula when its value
is requested by the user directly or indirectly through Formulas
depending on the Fromula's value.

The ``Fibo`` Cells in the sample below is taken from the earlier section::

    >>> Fibo.formula
    def Fibo(n):
        if n > 1:
            return Fibo(n-1) + Fibo(n-2)
        else:
            return n

Initially, ``Fibo`` does not have any values. You can check
``Fibo``'s values by converting it to :obj:`dict`::

    >>> dict(Fibo)
    {}

When you request the value of ``Fibo`` for ``n=5``,
the values of ``Fibo`` for ``n=0`` through ``n=4`` are also calculated::

    >>> Fibo(5)
    5

    >>> dict(Fibo)
    {1: 1, 0: 0, 2: 1, 3: 2, 4: 3, 5: 5}



Namespaces for Formulas
--------------------------

Most Formulas need to reference values of other Cells
and References to calculte their own values.
Unlike Python functions,
the name binding for modelx Formulas is independent from
Python modules.
Each Space has its own namespace associated with itself,
and the names in the Formulas of child Cells in the Space
are bound in the namespace associated with the Space.
The names defined in the associated namespace are
the names of the child objects of the Space, such as
child Cells, Spaces and References. In addition to
the child objects' names, global References,
special names and built-in names are defined in the associated
namespace.
The global References are the References defined at the containing Model level,
as attributes of the Model.
The special names are defiend by modelx,
and the names start with "_".
Currently there is only one special name, ``_space``,
which refers to the Space itself.
The list below summarizes
the kind of names defined in the namespace associated with a UserSpace.

    * The child Cells, Spaces and References
    * The global References defined in the Model
    * The special names (``_space``)
    * The Python built-in names

The sample code below is taken from
the mortgage loan example we have seen earlier.
The ``Balance`` global variable
refers to a Cells object ``Balance``, but the name of the variable
does not need to be the same as the Cells' name::

    >>> Balance.formula
    def Balance(t):

        if t > 0:
            return Balance(t-1) * (1+Rate) - Payment()
        else:
            return Principal

    >>> Balance(30)
    1.2096279533579946e-10


If ``Balance`` was a Python function, then the names in
the ``Balance`` definition, such as ``Balance``, ``Rate``,
``Payment``, ``Principal`` would refer to global variables
defined in the module that the function was defined in.
However, as explained above, the Formula of ``Balance`` is evaluated
in the namespace associated with its parent Space ``Fixed``.
The ``Fixed`` Space has child Cells, such as ``Payment`` and
``Balance``. It also has child References, such as
``Principal`` and ``Rate``. So, the names in the ``Balance`` definition
refer to those child Cells and Referneces of the ``Fixed`` Space.
To get all the names defined in the ``Fixed`` name space,
use the Python built-in function :obj:`dict`.
The code below assumes that the ``Fixed`` variable refers to the ``Fixed`` Space::

    >>> dir(Fixed)
    ['Balance',
     'Payment',
     'Principal',
     'Rate',
     'Term',
     '__builtins__',
     '_self',
     '_space']

(Note: ``_self`` in the list above is deprecated and should not be used.)

Analyzing Formula dependency
------------------------------

<<TODO>>




