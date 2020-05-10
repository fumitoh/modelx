Mortgage Example
================

For the second example, we are going to model a fixed-rate mortgage loan,
one of the basic types of amortized mortgage loans.
In a fixed-rate mortgage, the borrower repays the same amount
periodically for a certain term, such as 20 years or 30 years.
To learn more about mortgage loans, Wikipedia has
`a great article <https://en.wikipedia.org/wiki/Mortgage_loan>`_
detailing various types of mortgage loans.

For this exercise, we assume the payments are made annually.
We model the annual payment amount using a well-known formula,
for a given principal, interest rate and term.
We also model the outstanding loan balance at each year throughout
the payment term.

.. contents:: Contents
   :local:


Create Model and Space
----------------------
We start by creating a new *MxConsole* for this exercise.
Right-click on the tab of the existing *MxConsole* or the default Console,
and select *New MxConsole*.

.. figure:: /images/tutorial/Mortgage/OpenNewMxConsole2.png
   :align: center

   MxConsole Tab Context Menu

A new *MxConsole* tab opens and after a few
second, a new IPython session becomes ready to read your input
in the *MxConsole*.

In the previous example, before creating a Cells,
you did not explicitly create
the parent Space or the Model for the Cells,
but modelx automatically created them for you when the Cells was created.
This time, we start by creating a Model and a Space explicitly,
and name them ``Mortgage`` and ``Fixed``.

Right-click in the blank *MxExplorer*, and select *New Model*.
Enter ``Mortgage`` in the *Model Name* box in the dialog box.
As you type ``Mortgage``, the *Import As* box is also filled with ``Mortgage``.
This makes the Model accessible in the IPython
in the *MxConsole* as a variable named ``Morgage``. Click *OK*.

.. figure:: /images/tutorial/Mortgage/NewModelDialogMortgage.png
   :align: center

   New Model Dialog Box

Now you see *Current Model - Mortgage* is shown in the *Model* box
at the top right corner of the *MxExplorer*.

.. figure:: /images/tutorial/Mortgage/ModelSelectorMortgage.png
   :align: center

   Model Selector

Next we are going to create a new Space named ``Fixed`` in ``Mortgage``,
which stands for fixed-rate mortgage.

Right-click in the blank *MxExplorer*, and select *New Space*.
In the dialog box, you can see that *Mortgage* is selected
in the *Parent* box. As there is no Space,
only the Model can be the parent of the Space to be created.

Enter *Fixed* in the *Space Name* box. The *Import As* box
should be filled with *Fixed* automatically.

The *Base Spaces* box is for inheriting other Spaces.
We don't cover the *Inheritance* concept in this exercise,
so leave it blank here and click *OK*.


.. figure:: /images/tutorial/Mortgage/NewSpaceDialogFixed.png
   :align: center

   New Space Dialog Box

Now you should have the *Fixed* Space item in the *MxExplorer*.

.. figure:: /images/tutorial/Mortgage/MxExplorerFixed.png
   :align: center

   MxExplorer


Create Cells
------------

The annual payment for a fixed-rate mortgage can be calculated by
a well-known formula and can be expressed as follows:

.. math::

    Payment = Principal\cdot\frac{Rate(1+Rate)^{Term}}{(1+Rate)^{Term}-1}

where :math:`Principal` is the principal amount borrowed,
:math:`Rate` is the fixed annual interest rate on the outstanding loan balance
and :math:`Term` is the length of the loan period in years.

This formula can be expressed in a Python function as follows::

    def Payment():
        return Principal * Rate * (1+Rate)**Term / ((1+Rate)**Term - 1)

In Python ``**`` in math expressions is the power operator, so
the expressions ``(1+Rate)**Term`` above calculate
``(1+Rate)`` to the power ``Term``.

Let's create a Cells named ``Payment`` and define its formula by
the function above.
This time, let's create it following steps different from the first exercise:
We create ``Payment`` as an empty Cells,
and assign the formula after it's created.

Right-click on the MxExplorer, and select *New Cells* from the dialog box.
Then enter ``Payment`` in the *Cells Name* box.
As is always the case, leave the *Import As* check box checked to import
``Payment`` into IPython in the *MxConsole*. Click *OK*

.. figure:: /images/tutorial/Mortgage/NewCellsDialogPayment.png
   :align: center

   New Cells Dialog Box

You can see the *Payment* Cells created under the *Fixed* Space
in *MxExplorer*. Select the *Payment* Cells, right-click and
select *Show Properties* item. The properties of the *Payment* Cells
are shown in the Properties tab on the right side of the *MxExplorer*.

The expression ``lambda: None`` is set to the *Formula* property as
the default formula. Enter the ``Payment`` function above in the *Formula*
pane.

.. figure:: /images/tutorial/Mortgage/MxExplorerFixedPayment.png
   :align: center

   MxExplorer

The other item to calculate is the outstanding loan balance.
Let :math:`Balance(t)` be the loan balance at time :math:`t`.
:math:`Balance(t)` can be expressed as the following recursive formula:

.. math::

    &Balance(t)=Balance(t-1)\cdot(1+Rate)-Payment\qquad&(0<t\leq{Term})\\
    &Balance(0)=Principal\qquad&(t=0)

The :math:`Balance(Term)` should be 0 if :math:`Payment` is calculated
correctly by the previous formula.

As a Python function, the formula above can be expressed as follows::

    def Balance(t):

        if t > 0:
            return Balance(t-1) * (1+Rate) - Payment
        else:
            return Principle

You may have noticed that the code above has a typo ``Principle``,
but let's leave it as is to observe an error caused by the typo later.

Right-click on the MxExplorer, and select *New Cells* from the dialog box.
Then enter ``Balance`` in the *Cells Name* box.
Leave the *Import As* check box checked to import
``Balance`` into IPython in the *MxConsole*. Click *OK*

.. figure:: /images/tutorial/Mortgage/NewCellsDialogBalance.png
   :align: center

   New Cells Dialog Box

In the same way as you did for ``Payment``, Open show the properties
of ``Balance`` and put the function above in the *Formula* Pane.

.. figure:: /images/tutorial/Mortgage/MxExplorerFixedBalanceWrongFormula.png
   :align: center

   MxExplorer


Understand Error
----------------

The ``Payment`` Formula
refers to names such as ``Principal``, ``Rate`` and ``Term``.
We haven't define those names yet, so calculating ``Payment`` should
raise an error. Type ``Fixed.Payement()`` in the *MxConsole* and
you should get the following error message:

.. code-block:: none

    FormulaError: Error raised during formula execution
    NameError: name 'Principal' is not defined

    Formula traceback:
    0: Mortgage.FixedRate.Payment(), line 3

    Formula source:
    def Payment():

        return Principal * Rate * (1+Rate)**Term / ((1+Rate)**Term - 1)


The error message consists of 3 blocks of text. The first block
shows the type and message of the original error.
The original error in this case is ``NameError``, as
the name ``Principal`` is not defined.

The second block is Formula traceback.
It shows the stack of Formula calls, as pairs of Cells and arguments,
with the Formula you called on top, and the Formula call
that raises the error at the bottom.
In the case above, since the error is raised in the first Formula call,
it only shows one Formula call, ``Payment()``.

The last block shows the Formula that raised the error.


Create References
-----------------

The ``Payment`` Formula refers to the names ``Principal``, ``Rate``
and ``Term`` so we need to define those names.
Let's assume the principal is $100,000, the interest rate is 3% and
the payment term is 30 years.

You would think defining those names in the *MxConsole*
as follows would work::

    >>> Principal = 100000

    >>> Rate = 0.03

    >>> Term = 30

But actually it doesn't. This is because, by the commands above
you just define
those names in the IPython's global namespace.
However, the ``Payment`` Formula is evaluated in the namespace
associated with its parent Space, ``Fixed``.
In order for the ``Payment`` Formula to be able to refer to those names,
you need to define *References* in the ``Fixed`` Space as below::

    >>> Fixed.Principal = 100000

    >>> Fixed.Rate = 0.03

    >>> Fixed.Term = 30

You just created 3 *Reference* objects in the ``Fixed`` Space.
A *Reference* object
binds a name in its parent's namespace to an arbitrary object.

Now you see that the 3 items are created in the *MxExplorer*.
In the *Type* field, the types of *Principal* and  *Term* are *Ref/int*,
meaning that they are Reference objects, and the type of the associated values
is :obj:`int`.
In the same way, the type field of *Rate* shows *Ref/float*, which
means that it is a Reference object, and the type of its value
is :obj:`float`.

.. figure:: /images/tutorial/Mortgage/MxExplorerFixedReferences.png
   :align: center

   MxExplorer

Get Results
-----------

Now that you have defined all the References referenced by
the ``Payment``, calling the Formula should succeed::

    >>> Payment()
    5101.925932025255

To check the value is calculated correctly, we can make use
of `pmt`_ function from `numpy-financial`_ package::

    >>> import numpy_financial as npf

    >>> npf.pmt(0.03, 30, 100000)
    -5101.925932025255

You see that the absolute value of the returned value matches
the ``Payment`` value.

.. note::

    `pmt`_ function has been in `numpy`_ package, and it is still
    available in `numpy`_, but it is deprecated and moved to a separate
    package `numpy-financial`_.
    If you don't have `numpy-financial`_ installed,
    `pmt`_ function may be available in `numpy`_.

.. _pmt: https://numpy.org/numpy-financial/latest/pmt.html
.. _numpy: https://numpy.org/
.. _numpy-financial: https://numpy.org/numpy-financial/


Next try getting the loan balance at year 30:

    >>> Balance(30)

You should get the following error, as there is a typo in the formula.

.. code-block:: none

    FormulaError: Error raised during formula execution
    NameError: name 'Principle' is not defined

    Formula traceback:
    0: Mortgage.FixedRate.Balance(t=30), line 4
    ...
    28: Mortgage.FixedRate.Balance(t=2), line 4
    29: Mortgage.FixedRate.Balance(t=1), line 4
    30: Mortgage.FixedRate.Balance(t=0), line 6

    Formula source:
    def Balance(t):

        if t > 0:
            return Balance(t-1) * (1+Rate) - Payment()
        else:
            return Principle

The error message tells you that a ``NameError`` is raised
in ``Mortgage.FixedRate.Balance(t=0)`` at line 6,
because the name ``Principle`` is not found in the namespace in which
``Mortgage.FixedRate.Balance(t=0)`` is executed.

Correct the typo by going to *MxExplorer* and
changing ``Principle`` to ``Principal`` in the *Formula* pane.

.. figure:: /images/tutorial/Mortgage/MxExplorerBalance.png
   :align: center

   MxExplorer

Calculate the balance again::

    >> Balance(30)
    1.2096279533579946e-10

The result is the reciprocal of 1.2 to the 10th power, which is
effectively zero. It looks like the balance at each annual step
till the year 30 is calculated correctly. You can check
the values of the balance by ``dict(Balance)`` or ``Balance.frame``,
and also you can output a graph of the balance by::

    >>> Balance.frame.plot()

You should get a line graph of the balance in Spyder's *Plots* widget, and
see that the line smoothly decreases till the year 30 where the balance
becomes fully repaid.

.. figure:: /images/tutorial/Mortgage/BalanceGraph.png
   :align: center

   Mortgage Loan Balance


Recap
-----
Through this exercise, we learned:

* How to create a Model and Space explicitly,
* How to set the Formula of an existing Cells,
* The Formula of a Cells is evaluated in the parent's namespace,
* What are *References* and how to define them,
* How to interpret error messages and,
* How to output Cells values as a graph.


