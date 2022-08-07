Introduction to modelx
-----------------------

modelx is a Python package to build mathematical models
and carry out complex numerical computations.
modelx is best suited for models in such fields as actuarial science,
quantitative finance and risk management.
modelx lets you define the logic of a model by formulas like Excel.


.. _overview-of-core-modelx-objects:

Overview of core modelx objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

modelx lets you build models composed of a few types of objects.
*Model*, *Space*, *Cells* and *References*
are the most important types of objects.
In this section, these types of objects are briefly introduced
to let you have a basic idea on what these types of objects are,
before getting started with sample exercises.

Model, Space and Cells are to modelx
what Workbook, Worksheet and Range are to a Excel respectively,
although there are differences.
The diagram below illustrates containment
relationships between those objects.

.. blockdiag::
   :caption: Model, Space and Cells
   :align: center

   blockdiag {
     orientation = portrait
     default_node_color="#D5E8D4";
     default_linecolor="#628E47";
     node_width=70;
     Model1<- Space1[hstyle=composition];
     Model1<- Space2[hstyle=composition];
     Model1<- Ref1[hstyle=composition];
     Space1<- Cells1[hstyle=composition];
     Space1<- Space3[hstyle=composition];
     Space1<- Ref2[hstyle=composition];
   }


Models are the top level container objects.
Models can be saved to files and loaded back again.
You can have multiple models opened in one Python session at the same time.

Within a model, you can create Space objects. Spaces serve as containers,
separating contents in the model into components.
the spaces can contain Cells, Reference and other Space objects, allowing
a tree structure to form within the model.
The spaces also serve as the namespaces for the formulas associated to
the spaces themselves or to the Cells objects contained in them.

Cells are objects that can have formulas and hold values, just like
spreadsheet cells can have formulas and values.
Cells values are either calculated
by their formulas or assigned as input by the user.
We will later learn how to define cells' formulas through
some examples.

References are names bound to arbitrary objects.
References can be defined either in spaces or in models.
References defined in a space can be referenced from
the formulas of the cells defined in the space,
or the formula associated with the space.
For example, ``Cells1.formula`` (and ``Space1.formula`` if any) can
refer to ``Ref2``.
References defined in a model (for example *Ref1* in the
diagram above) can be referenced from formulas
defined anywhere in the model, unless other references
override the name binding defined by the reference in the model.


How to interface with modelx
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

modelx is a Python package, so to use modelx you can simply
write Python scripts and import it, as you would normally do with
any other Python package.
Likewise, you can also use it interactively from an IPython consoles,
or in Jupyter notebooks.
By convention, It is recommended to import the module as ``mx``::

    >>> import modelx as mx

Another way to interface with modelx is through Spyder plugin for modelx
on Spyder IDE. The plugin installs custom widgets and custom IPython consoles
that allow you to interface with modelx graphically.
Using the GUI greatly helps you to understand and interact with modelx models more
intuitively.
The sample exercises in this tutorial assumes you use Spyder with the plugin.

