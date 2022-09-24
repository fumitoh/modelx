==================================
modelx v0.21.0 (24 September 2022)
==================================

This release introduces the following enhancements to
make it easier to inspect formula errors.


To update modelx, run the following command::

    >>> pip install modelx --upgrade

If you're using Anaconda, use the ``conda`` command instead::

    >>> conda update modelx

If you're using the Spyder plugin for modelx, the
:doc:`spymx-kernels<spymx_kernels_relnotes>` pakcage is also updated,
so update it as well by either::

    >>> pip install smymx-kernels --upgrade

or on Anaconda,

    >>> conda update spymx-kernels


Enhancements
============

.. py:currentmodule:: modelx

Update on :func:`get_traceback` and introduction of :func:`trace_locals`
-------------------------------------------------------------------------

When a formula throws an error, the traceback of the formula execution
is available by :func:`get_traceback`.
:func:`get_traceback` is now enhanced to also report
the local variables referenced by the fomulas in the traceback list.
In addition, :func:`trace_locals`, a convenience fuction
is introduced to quickly view the local variables referenced
by the erronerous formula or its callers::


    >>> import modelx as mx

    >>> @mx.defcells
    ... def foo(x):
    ... a = 1
    ... return bar(x) + a

    >>> @mx.defcells
    ... def bar(y):
    ...     b = 2
    ...     return 2 * y / 0  # raises ZeroDivisionError

    >>> foo(1)
    modelx.core.errors.FormulaError: Error raised during formula execution
    ZeroDivisionError: division by zero
    Formula traceback:
    0: Model1.Space1.foo(x=1), line 3
    1: Model1.Space1.bar(y=1), line 3
    Formula source:
    def bar(y):
        b = 2
        return 2 * y / 0 #  raise ZeroDivizion

    >>> mx.get_traceback()
    [(Model1.Space1.foo(x=1), 3, {'x': 1, 'a': 1}),
     (Model1.Space1.bar(y=1), 3, {'y': 1, 'b': 2})]

    >>> mx.trace_locals()
    {'y': 1, 'b': 2}

    >>> mx.trace_locals(-2)
    {'x': 1, 'a': 1}
