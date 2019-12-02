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
* asttokens
* Pandas
* OpenPyXL
* Spyder (>=3.2.5)

networkx
^^^^^^^^
`NetworkX <http://networkx.github.io/>`_ is a required package that modelx
depends on. Version 2.0 or newer is required.

asttokens
^^^^^^^^^
`asttokens <https://asttokens.readthedocs.io/en/latest/>`_
is a required package that modelx depends on.

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


Spyder integration
------------------

`Spyder`_ is a popular open-source Python IDE, and
a Spyder plugin for modelx is avaialble. To install and use the plugin,
see the :doc:`spyder` page
