.. currentmodule:: modelx

.. _release-v0.6.1:

================================
modelx v0.6.1 (29 April 2020)
================================

This release is for a bug fix.

Bug Fixes
=========

* Bug in :func:`get_traceback` when formula in traceback
  contains lambda expressions, formula calls within comprehensions or
  nested functions (`GH31`_).

.. _GH31: https://github.com/fumitoh/modelx/issues/31


.. _release-v0.6.0:

================================
modelx v0.6.0 (27 April 2020)
================================

This release implements a new error mechanism for tracing errors raised in
formula execution. The error messages are also improved.

.. contents::
   :depth: 1
   :local:


Enhancements
============

**Formula error**

When an error is raised during formula execution,
the new default behaviour of modelx is to raise ``FormulaError``,
instead of raising the original exception.
The error message of the ``FormulaError``
shows the error message from the original exception, followed by
a traceback of modelx elements, and the source code of the formula
the exception is raised from. To retrieve the original exception, use
:func:`get_error` function.
This default behaviour can be altered by the user by passing :obj:`False`
to :func:`use_formula_error` function, in which case the original errors
are raised.
:func:`get_traceback` function returns the traceback information
as a list of tuples. Each tuple represents a call to a formula
stacked in the execution callstack when the error is raised.
The first element of the tuple is an element of a modelx object, which is
an element of a Cells in most cases. The second element of the tuple is
a line number in the formula, indicating where the call to the next formula
is or, in the case of the last formula, where the error happens.
The line number of the last formula can be 0 if the error happens
before or after the execution of the formula.

The last error information, which can be retrieved by
:func:`get_error` and :func:`get_traceback`,
is cleared at the next formula execution.

* :func:`get_error`, :func:`get_traceback` and :func:`use_formula_error`
  functions are added as explained above.

* :func:`get_recursion` is added to get the current recursion limit.


Backward Incompatible Changes
=============================

* Implicit conversion of a Cells with no parameters to its value
  upon assignment to a Cells is now removed.

Bug Fixes
=========

* Broken internal state due to failed formula execution.


