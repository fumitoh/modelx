.. currentmodule:: modelx

.. _release-v0.0.25:

================================
modelx v0.0.25 (19 October 2019)
================================

This release introduces a feature to trace the call stack of formula calculations
in response to user's feature request.
The tracing is useful when the user wants to get the information on
the execution of cells formulas, such as
how much time each formula takes from start to finish, or
what formulas are called in what order to identify performance bottlenecks.


Enhancements
============

* The API functions blow are introduce for the stack tracing feature (`GH13`_).

    * :func:`~start_stacktrace`
    * :func:`~stop_stacktrace`
    * :func:`~get_stacktrace`
    * :func:`~clear_stacktrace`

.. _GH13: https://github.com/fumitoh/modelx/issues/13

Bug Fixes
=========

* Error when writing models containing non-ascii strings as refs.

