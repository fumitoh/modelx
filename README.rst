modelx
======
*Use Python like a spreadsheet!*

.. image:: https://github.com/fumitoh/modelx/actions/workflows/python-package.yml/badge.svg
    :target: https://github.com/fumitoh/modelx/actions/workflows/python-package.yml

.. image:: https://img.shields.io/pypi/pyversions/modelx
    :target: https://pypi.org/project/modelx/

.. image:: https://img.shields.io/pypi/v/modelx
    :target: https://pypi.org/project/modelx/

.. image:: https://img.shields.io/pypi/l/modelx
    :target: https://github.com/fumitoh/modelx/blob/master/LICENSE.LESSER.txt


.. Overview Begin

What is modelx?
---------------
**modelx** is a numerical computing tool that enables you to
use Python like a spreadsheet by quickly defining cached functions.
modelx is best suited for implementing mathematical models expressed
in a large system of recursive formulas,
in such fields as actuarial science, quantitative finance and risk management.

See also the `GitHub Copilot instructions for modelx <https://github.com/fumitoh/modelx/blob/main/.github/copilot-instructions.md>`_.

Feature highlights
------------------
**modelx** enables you to interactively
develop, run and debug complex models in smart ways.
modelx allows you to:

- Define cached functions as *Cells* objects by writing Python functions
- Quickly build object-oriented models, utilizing prototype-based inheritance and composition
- Quickly parameterize a set of formulas and get results for different parameters
- Trace formula dependency
- Import and use any Python modules, such as `Numpy`_, `pandas`_, `SciPy`_, `scikit-learn`_, etc..
- See formula traceback upon error and inspect local variables
- Save models to text files and version-control with `Git`_
- Save data such as pandas DataFrames in Excel or CSV files within models
- Auto-document saved models by Python documentation generators, such as `Sphinx`_
- Use Spyder with a plugin for modelx (`spyder-modelx`_) to interface with modelx through GUI
- Export models as Python modules independent of modelx
- Translate exported models to Cython optimized code and compile them for performance improvement using Cython through `modelx-cython`_ 

.. _Numpy: https://numpy.org/
.. _pandas: https://pandas.pydata.org/
.. _SciPy: https://scipy.org/
.. _scikit-learn: https://scikit-learn.org/
.. _Git: https://git-scm.com/
.. _Sphinx: https://www.sphinx-doc.org
.. _spyder-modelx: https://github.com/fumitoh/spyder-modelx
.. _modelx-cython: https://github.com/fumitoh/modelx-cython


modelx sites
-------------

========================== ===============================================
Home page                  https://modelx.io
Blog                       https://modelx.io/allposts
Documentation site         https://docs.modelx.io
Development                https://github.com/fumitoh/modelx
Discussion Forum           https://github.com/fumitoh/modelx/discussions
modelx on PyPI             https://pypi.org/project/modelx/
========================== ===============================================


Who is modelx for?
------------------
**modelx** is designed to be domain agnostic, 
so it's useful for anyone in any field.
Especially, modelx is suited for modeling in such fields such as:

- Quantitative finance
- Risk management
- Actuarial science

**lifelib** (https://lifelib.io) is a library of actuarial and
financial models that are built on top of modelx.

How modelx works
----------------

Below is an example showing how to build a simple model using modelx.
The model performs a Monte Carlo simulation to generate 10,000
stochastic paths of a stock price that follow a geometric Brownian motion
and to price an European call option on the stock.

.. code-block:: python

    import modelx as mx
    import numpy as np

    model = mx.new_model()                  # Create a new Model named "Model1"
    space = model.new_space("MonteCarlo")   # Create a UserSpace named "MonteCralo"

    # Define names in MonteCarlo
    space.np = np
    space.M = 10000     # Number of scenarios
    space.T = 3         # Time to maturity in years
    space.N = 36        # Number of time steps
    space.S0 = 100      # S(0): Stock price at t=0
    space.r = 0.05      # Risk Free Rate
    space.sigma = 0.2   # Volatility
    space.K = 110       # Option Strike


    # Define Cells objects in MonteCarlo from function definitions
    @mx.defcells
    def std_norm_rand():
        gen = np.random.default_rng(1234)
        return gen.standard_normal(size=(N, M))


    @mx.defcells
    def stock(i):
        """Stock price at time t_i"""
        dt = T/N; t = dt * i
        if i == 0:
            return np.full(shape=M, fill_value=S0)
        else:
            epsilon = std_norm_rand()[i-1]
            return stock(i-1) * np.exp((r - 0.5 * sigma**2) * dt + sigma * epsilon * dt**0.5)


    @mx.defcells
    def call_opt():
        """Call option price by Monte Carlo"""
        return np.average(np.maximum(stock(N) - K, 0)) * np.exp(-r*T)

Running the model from IPython is as simple as calling a function:

.. code-block:: pycon

    >>> stock(space.N)      # Stock price at i=N i.e. t=T
    array([ 78.58406132,  59.01504804, 115.148291  , ..., 155.39335662,
            74.7907511 , 137.82730703])

    >>> call_opt()
    16.26919556999345

Changing a parameter is as simple as assigning a value to a name:

.. code-block:: pycon

    >>> space.K = 100   # Cache is cleared by this assignment

    >>> call_opt()    # New option price for the updated strike
    20.96156962064

You can even dynamically create multiple copies of *MonteCarlo*
with different combinations of ``r`` and ``sigma``,
by parameterizing *MonteCarlo* with ``r`` and ``sigma``:

.. code-block:: pycon

    >>> space.parameters = ("r", "sigma")   # Parameterize MonteCarlo with r and sigma

    >>> space[0.03, 0.15].call_opt()  # Dynamically create a copy of MonteCarlo with r=3% and sigma=15%
    14.812014828333284

    >>> space[0.06, 0.4].call_opt()   # Dynamically create another copy with r=6% and sigma=40%
    33.90481014639403


License
-------
Copyright 2017-2024, Fumito Hamamura

modelx is free software; you can redistribute it and/or
modify it under the terms of
`GNU Lesser General Public License v3 (LGPLv3)
<https://github.com/fumitoh/modelx/blob/master/LICENSE.LESSER.txt>`_.

Contributions, productive comments, requests and feedback from the community
are always welcome. Information on modelx development is found at Github
https://github.com/fumitoh/modelx


.. Overview End


Requirements
------------
* Python 3.7+
* NetwrkX 2.0+
* asttokens
* LibCST
* Pandas
* OpenPyXL
