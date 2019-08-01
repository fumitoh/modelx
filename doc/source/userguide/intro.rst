Design Overview
===============



modelx and OOP
--------------

The design of modelx is heavily influenced by the object-oriented
programming (OOP) paradigm.
Space in modelx imitates class and instance in OOP,
and Cells in modelx imitates method in OOP.
Composition and inheritance are also brought in from OOP.

.. note::

    Be aware that some OOP terminologies are redefined in this guide
    and have different meanings from those in OOP contexts.


modelx and Python
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