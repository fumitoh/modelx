Installation
============

.. note::

   For `lifelib`_ users, when installing `lifelib`_ using
   ``pip``, modelx is automatically installed due to its dependency, so
   no need to install modelx separately.

.. _lifelib: http://lifelib.io

Python version
--------------
modelx requires Python 3.6 or newer. modelx does not work with Python 3 older
than version 3.6 or any version of Python 2.


Package dependency
------------------
The packages listed below are either required by modelx,
or can be used with modelx to develop models more efficiently.

* NetworkX (>=2.0)
* Pandas
* OpenPyXL
* Spyder (>=3.2.5)

networkx
^^^^^^^^
`NetworkX <http://networkx.github.io/>`_ is a required package that modelx
depends on. Version 2.0 or newer is required.

Pandas
^^^^^^
Although you can install modelx without Pandas,
it is highly recommended that you have Pandas installed, together with
other packages Pandas depends on, such as NumPy,
so that you can export Spaces and Cells to Pandas DataFrame and Series.

Openpyxl
^^^^^^^^
OpenPyXL is a package that supports reading from and writing to Excel files.
Openpyxl is also not required, but it is desirable to hav it installed
to enable modelx to interface with Excel files.

Spyder
^^^^^^
If you use modelx with `Spyder <https://www.spyder-ide.org/>`_,
a plugin for modelx is available.
``spyder-modelx`` is a separate package to add custom IPython consoles
and Modelx explorer, a widget that shows the current model in a tree view.
The supported Spyder version is 3.2.5 or newer.
For how to install the plugin, see :ref:`here <install-spyder-plugin>`.

Installing modelx
-----------------

.. note::

   If you install :ref:`Spyder plugin for modelx <install-spyder-plugin>`
   as explained below,
   no need to install modelx separately as modelx is installed
   together with the plugin, so skip to the
   :ref:`Plugin installation <install-spyder-plugin>` section.

Just like other Python packages, you can install ``modelx`` by
running ``pip`` command from a terminal on Linux, or from a command prompt on
Windows.

To install the current version of ``modelx`` with ``pip``::

    $ pip install modelx

To upgrade to a newer version using the ``--upgrade`` flag::

    $ pip install --upgrade modelx

To make ``modelx`` available only to you but others,
install it into your user directory using the ``--user`` flag::

    $ pip install --user modelx

If you prefer to install ``modelx`` from files placed locally on your machine
instead of directly fetching from the Web,
you can manually download ``modelx`` files from
`GitHub <https://github.com/fumitoh/modelx/releases>`_  or
`PyPI <http://pypi.python.org/pypi/modelx>`_.

Unpack the downloaded files and run the following command
at the top of the source directory::

    $ pip install .


.. _install-spyder-plugin:

Installing Spyder plugin for modelx
-----------------------------------

`Spyder <https://www.spyder-ide.org/>`_ is a popular Python IDE,
and it's bundled in with `Anaconda <https://www.anaconda.com/>`_ by default.
``spyder-modelx`` is a Spyder plugin to add custom IPyhton consoles
and Modelx explorer, a widget that shows
the current model in a tree view.

To install the plugin, run the following command in the command prompt::

    $ pip install spyder-modelx


To check the plugin, start Spyder, and go to *View->Panes* menu, and
check *Mx explorer*.

.. figure:: images/SpyderMainMenuForModelx.png

Then the Modelx explorer tab appears in the upper right pane.

.. figure:: images/MxExplorer.png

Right-click ont the IPython console tab in the lower right pane, then click
*Open a modelx console* menu.

.. figure:: images/IPythonConsoleMenu.png

A modelx console named *Mx Console* starts. The modelx console works
exactly the same as a regular IPython console,
except that the modelx explorer shows the components of the current model
in the IPython session of this console. To test the behaviour,
create a new model and space in the modelx console like this::

    >>> import modelx as mx

    >>> model, space = mx.new_model(), mx.new_space()

    >>> cells = space.new_cells()

The modelx explorer shows the component tree of the created space.

.. figure:: images/MxExplorerTreeSample.png