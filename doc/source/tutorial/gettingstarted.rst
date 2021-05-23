Getting Started
---------------

Before diving into sample exercises,
first we learn how to interface with modelx, then
set up a Python environment for modelx, and
learn about core modelx objects.

.. contents:: Contents
   :local:

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


Setting up Python and modelx
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setting up a Python environment for modelx is pretty straight-forward.
Download the WinPython distribution customized for modelx from
`here <https://lifelib.io/download.html>`_.

This tutorial assumes you're using the latest modelx and spyde-modelx,
so if you have downloaded the distribution before,
make sure you update modelx and spyder-modelx to the latest versions
by following the instruction :ref:`here<updating-packages>`,
or download the latest distribution from the site above.

Unzip the downloaded zip file. You can unzip it from the Windows default
context menu by right-clicking on the file and select *Extract All...*,
or instead you can use your favorite third party tool for unzipping.

.. figure:: /images/tutorial/GettingStarted/ExtractAllContextMenu.png
   :align: center

   Windows context menu for extracting zip file

In this tutorial, we use *Spyder* as a graphical user interface to modelx.
The downloaded WinPython comes with Spyder and Spyder plugin for modelx
pre-installed and pre-configured,
so no need to install them separately.

Within the unzipped folder, find *Spyder.exe* and start Spyder by
double-clicking it.

.. figure:: /images/tutorial/GettingStarted/StartSpyder.png
   :align: center

   Spyder.exe in unzipped folder

The Spyder window shows up. You may have modelx widgets showing already
upon startup, but if you don't, bring them up by going to *View* menu
in the menu bar and select *Pane* and then select
three modelx items (*MxExplorer*, *MxDataView*, *MxAnalyzer*)
at the bottom.

.. figure:: /images/tutorial/GettingStarted/ViewMenuMxWidgets.png
   :align: center

   modelx Widgets in View menu

Now you should be able to see the 3 widgets. You can move them around
and change their locations by unlocking panes.
To unlock panes, go to *View* menu and uncheck *Lock panes and toolbars* item.

.. figure:: /images/tutorial/GettingStarted/ViewMenuUnlockPane.png
   :align: center

   Lock and Unlock Panes

The last widget to prepare for modelx is *MxConsole*,
an IPython console that communicates with the modelx widgets.
modelx works fine in Spyder's default IPython consoles,
but the default consoles do not communicate with the modelx widgets,
so you want to use *MxConsoles* instead.
You should have IPython console pane and a tab named *Console 1/A*.
Right-click on the tab, and from the context menu,
select *New MxConsole*.

.. figure:: /images/tutorial/GettingStarted/OpenNewMxConsole.png
   :align: center

   Console Tab Context Menu

A new tab named *MxConsole 2/A* is created,
and after a few seconds, an IPython session starts in the *MxConsole*
and waits for your input.

.. figure:: /images/tutorial/GettingStarted/BlankMxConsole.png
   :align: center

   MxConsole

.. _overview-of-core-modelx-objects:

Overview of core modelx objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

modelx is designed to let the users build models consisting
of a few types of objects.
*Model*, *Space*, *Cells* and *References*
are the most important types of objects.
Before getting started with the first example,
you want to have an idea on what these types of objects are.

Model, Space and Cells are to modelx
what workbook, worksheet and cells are to a spreadsheet program respectively,
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


Models are the top level objects that contain all the other types
of modelx objects. Models can be saved to files and loaded back again.

Directly under Models, there are Spaces. Spaces serve as containers,
separating contents in Models into components.
Spaces contain Cells objects and other Spaces, allowing tree
structures of objects to form within Models.

Spaces also serve as the namespaces for the formulas associated to
the Spaces themselves or to the Cells contained in them.
References are names bound to arbitrary objects.
References defined in a Model (for example *Ref1* in the
diagram above) can be referenced from any Formulas
in the Model. References defined in a Space can be referenced from
the Formulas in the Space.
For example, ``Cells1.formula`` (and ``Space1.formula`` if any) can
refer to ``Ref2``.


Cells are objects that can have formulas and hold values, just like
spreadsheet cells can have formulas and values.
Cells values are either calculated
by their formulas or assigned as input by the user.
We will learn how to define Cells formulas through the examples soon.