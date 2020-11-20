
===============================
modelx v0.11.0 (21 Nov 2020)
===============================


This release introduces the following enhancements and changes.

Enhancements
============

.. rubric:: Stack trace summary for performance checks

In order to diagnose performance bottlenecks, it is useful to
have a report which shows how much time each formula took during an execution.
:func:`~modelx.get_stacktrace` now has a ``summarize`` option, and
when the option is set to ``True``, :func:`~modelx.get_stacktrace`
returns a :obj:`dict` whose keys are the representation
strings of the called Cells, and whose values are dicts
containing the following statistics of the Cells::

    import time
    import pandas as pd
    import modelx as mx

    m = mx.new_model()

    m.time = time

    @mx.defcells
    def foo(x):
        time.sleep(0.1)     # Waits 0.1 second
        return foo(x-1) + 1 if x > 0 else bar()

    @mx.defcells
    def bar():
        time.sleep(0.2)     # Waits 0.2 second
        return 0

    mx.start_stacktrace(maxlen=None)

    foo(5)

    df = pd.DataFrame.from_dict(mx.get_stacktrace(summarize=True), orient="index")

    mx.stop_stacktrace()

The sample code above creates a DataFrame as ``df`` that shows how many times
``foo`` and ``bar`` Cells were called,
how much time they took to execute their formulas, and
the times that the execution entered into or left each of the formulas
for the first and last time.

====================== ======== ======================= ======================= =====================
Cells                     calls               duration     first_entry_at         last_exit_at
====================== ======== ======================= ======================= =====================
Model1.Space1.foo(x)         6   0.6097867488861084       1605873067.2099519      1605873068.0203028
Model1.Space1.bar()          1   0.20056414604187012      1605873067.8197386      1605873068.0203028
====================== ======== ======================= ======================= =====================


.. rubric:: Deleted objects are now replaced with null objects

When deleted objects are referenced either in or outside of models,
they are now replaced with *null objects*::

    import modelx as mx

    m = mx.new_model()
    A = m.new_space("A")
    B = m.new_space("B")

    B.C = A

    del m.A

In the sample model above, the Space ``A``  is a null object::

    >>> A
    <UserSpace null object>

    >>> B.C
    <UserSpace null object>

Accessing attributes of the null objects raises ``DeletedObjectError``.


Backward Incompatible Changes
=============================

* :func:`Cells._is_derived` and :func:`Cells._is_defined` are now
  methods instead of properties.

* `repr`_ of Spaces and Cells now based on their dotted names,
  such as ``<Cells Model1.B[3].foo(x)>``

.. _repr: https://docs.python.org/3/library/functions.html#repr


Bug Fixes
=========

* Fixed errors raised when reading models containing Pandas objects
  that were written by an older version of Pandas.

* Fixed errors raised when reading models containing pathlib.Path
  which were written on a different platform.