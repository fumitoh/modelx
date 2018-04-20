Installation
============

.. note::

   For `lifelib`_ users, when installing `lifelib`_ using
   ``pip``, modelx is automatically installed due to its dependency, so
   no need to install modelx separately.

.. _lifelib: http://lifelib.io

Python version
--------------
modelx requires Python 3.4 or newer. modelx does not work with Python 3 older
than version 3.4 or any version of Python 2.


Package dependency
------------------
modelx depends of the following packages.

* NetworkX
* Pandas
* OpenPyXL

networkx
^^^^^^^^
`NetworkX <http://networkx.github.io/>`_ is a required package that modelx
depends on.

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

Installing modelx
-----------------
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
