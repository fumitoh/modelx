Installation
============

.. note::

    This page explains how to install and configure
    modelx and related packages manually, and is intended for
    advanced Python users or Linux/Mac users.

    For Windows users,
    it is recommended to use the latest custom WinPython with modelx,
    which is available `here <https://lifelib.io/download.html>`_.
    You can start using modelx just by unzipping the downloaded file,
    and no need to follow the steps on this page.

Python version
--------------

modelx requires Python 3.6 or newer.
However, Python 3.6 reached its `end of life <https://devguide.python.org/devcycle/#end-of-life-branches>`_
so if you're still using Python 3.6, you should upgrade it.
The newer the version of Python is, the faster it performs.


Package dependency
------------------
The packages listed below are either required by modelx,
or can be used with modelx to develop models more efficiently.

* NetworkX (>=2.0) (required)
* asttokens (required)
* pandas (optional)
* OpenPyXL (optional)
* Spyder (>=4.0.0) (optional)

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
To use modelx with `Spyder <https://www.spyder-ide.org/>`_,
a popular open-source Python IDE,
A plugin for modelx is available.
``spyder-modelx`` is a separate package to add custom IPython consoles
and Modelx explorer, a widget that shows the current model in a tree view.
The supported Spyder version is 4.0.0 or newer.
For how to install the plugin, see :ref:`here <install-spyder-plugin>`.

Installing modelx
-----------------

.. note::

   For `lifelib`_ users, when installing `lifelib`_ using
   ``pip`` or ``conda``, modelx is automatically installed due to its dependency, so
   no need to install modelx separately.

.. _lifelib: http://lifelib.io
.. _Anaconda: https://www.anaconda.com/

Just like other Python packages, you can install ``modelx`` by
running ``pip`` command from a terminal on Linux, or from a command prompt on
Windows. If your Python environment is `Anaconda`_, use the ``conda`` command in stead of ``pip``,
as explained below.

To install the current version of ``modelx`` with ``pip``::

    $ pip install modelx

To upgrade to a newer version using the ``--upgrade`` flag::

    $ pip install --upgrade modelx

To make ``modelx`` available only to you but others,
install it into your user directory using the ``--user`` flag::

    $ pip install --user modelx

To uninstall ``modelx``::

    $ pip uninstall modelx

If you prefer to install ``modelx`` from files placed locally on your machine
instead of directly fetching from the Web,
you can manually download ``modelx`` files from
`GitHub <https://github.com/fumitoh/modelx/releases>`_  or
`PyPI <http://pypi.python.org/pypi/modelx>`_.
Unpack the downloaded files and run the following command
at the top of the source directory::

    $ pip install .

To install the latest development version instead of the released version,
clone the `modelx repository`_  from github,
and install them from the cloned repos in `editable mode`_.

.. _modelx repository: https://github.com/fumitoh/modelx
.. _editable mode: https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs

Anaconda environment
^^^^^^^^^^^^^^^^^^^^
`Anaconda`_ is a Python distribution for scientific computing that has
its own package management command named ``conda``.
If your Python environment is based on the Anaconda distribution, do not use ``pip``
to install and update ``modelx``. In stead, use the ``conda`` command.

To install the current version of ``modelx``::

    $ conda install -c conda-forge modelx

To upgrade modelx::

    $ conda update modelx

To uninstall modelx::

    $ conda remove modelx

Spyder integration
------------------

`Spyder`_ is a popular open-source Python IDE, and
a Spyder plugin for modelx is available. For more about the Spyder plugin
for modelx, see the :doc:`spyder` page


Configuring Spyder
^^^^^^^^^^^^^^^^^^

**Disable User Module Reloader**

When you use modelx with Spyder, sometimes you may want to re-run the
same file in the editor window multiple times in the same IPython session.
You don't want to reload modelx because reloading modelx module creates
multiple instances of modelx systems within the same Python process,
causing models created before and after a reload to reside in different
modelx systems. To avoid that, you need to change *User Module Rloader (UMR)*
setting.

From the Spyder menu, select *Tools->Preferences* to bring up Preferences window.
Choose *Python interpreter* in the left pane, and you'll find an area titled
*User Module Reloader (UMR)* on the bottom right side of the Preferences window.
Leave *Enable UMR* option checked,
click *Set UMR excluded(not reloaded) modules* and then UMR dialog box pops up
as the figure blow.
Enter "modelx" in the dialog box. This prevents
Spyder from reloading the modelx module every time you re-run the same script
from *Run* menu, while allowing other modules to be reloaded.

Note that you need to restart Spyder to bring the change into effect.

.. figure:: /images/spyder/PreferencesUMR.png

   User Module Reloader setting


**Import modelx at IPython startup**

When you use modelx in IPython, you need to import modelx first.
Doing so every time you open a new IPython session is tedious,
so there's a way to import modelx at each IPython session's startup.
From the Spyder menu, select *Tools->Preferences* to bring up Preferences window.
Choose *IPython console* in the left pane, and select
*Startup* tab from the tabs on the right.
Enter ``import modelx as mx`` in the box titled *Lines:* in the *Run code* area,
and click *Okay*. Next time you open a new IPython session,
modelx is imported as ``mx`` in the IPython's global namespace.

.. figure:: /images/spyder/PreferencesStartup.png

   IPython startup setting


.. _install-spyder-plugin:

Installing Spyder plugin for modelx
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The plugin is available as separate Python packages named ``spyder-modelx`` and ``spymx-kernels``.

The supported version of Spyder is 4.0.0 or newer. The plugin does not
work with Spyder 3.x.

``spyder-modelx`` package is available on PyPI, and can be installed using ``pip`` command.
If you're using `Anaconda`_ distribution, do not use ``pip`` but use ``conda`` instead::

    > pip install spyder-modelx

With Anaconda::

    > conda install -c conda-forge spyder-modelx

``spymx-kernels`` is installed automatically because ``spyder-modelx`` depends on ``spymx-kernels``.

If Spyder is running while the plugin gets installed, close Spyder once
and restart it to bring the plugin into effect.

.. _updating-packages:

Updating packages
-----------------

To update modelx to the latest version, use ``-U`` option with ``pip install``,
or ``conda update`` with `Anaconda`_::

    $ pip install -U modelx

On Anaconda::

    $ conda update modelx


