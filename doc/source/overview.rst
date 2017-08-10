..  -*- coding: utf-8 -*-

Overview
========
*Unleash your spreadsheet models!*

What is modelx?
---------------
modelx is a Python package for performing complex calculations by creating models
composed of structured data and formulas. You can think of it as a multidimensional
version of spreadsheet, but it’s so much more!

How modelx works
----------------
modelx eposes its API functions and classes such as Model, Space and Cells to its users,
and the users build their models from those classes, by defining calculation formulas
in the form of Python functions and associating those calculations with Cells objects.

Below is a very simple working example in which:

- a new model is created,
- and in the model, a new space is created,
- and in the space, a new cells is created , which is associated with the Fibonacci series.

.. literalinclude:: example_overview.py
   :lines: 1-4                 

To get a Fibonacci number for, say 10, you can do::
  
  >> fibo(10)
  55
  
To start using modlex, import it and create a model and then a space in the model like this:

           
``create_model()`` is a modelx API function which returns a newly created model. You can
specify the name of the model by passing it as an argumet to the function. If no name
is given as the argument, the returned model is named automatically by modelx.

You can create a space in a model by calling ``create_space()`` method on the model.
The name of the space can be specified by passing it to the method as an argument,
otherwise the space gets its name by modelx.

If you're on an interactive python shell, you can 

::
   
   >> fibo
   name: fibo
   space: MySpace
   number of cells: 0

How to end literal block                    
           
Feature highlights
------------------

- Creation of Formulas from Python function definitions
- Dynamic scope in Formulas
- Cells as a callable and dictionary-like container
- Namespacing by Space objects
- Inheritance of Space

Who is modelx for?
------------------

modelx is designed to be domain agnostic. The modelx creator is an actuary, so he meant it to be used by  actuaries, but potential audience for modelx can be anyone who needs to develop complex models that are too much for spreadsheets.

Goals
-----

NetworkX is a Python language software package for the creation,
manipulation, and study of the structure, dynamics, and function of complex networks.

With NetworkX you can load and store networks in standard and nonstandard data formats, generate many types of random and classic networks, analyze network structure,  build network models, design new network algorithms, draw networks, and much more.


Who uses NetworkX?
------------------

The potential audience for NetworkX includes mathematicians,
physicists, biologists, computer scientists, and social scientists. Good
reviews of the state-of-the-art in the science of
complex networks are presented in Albert and Barabási [BA02]_, Newman
[Newman03]_, and Dorogovtsev and Mendes [DM03]_. See also the classic
texts [Bollobas01]_, [Diestel97]_ and [West01]_ for graph theoretic
results and terminology. For basic graph algorithms, we recommend the
texts of Sedgewick, e.g. [Sedgewick01]_ and [Sedgewick02]_ and the
survey of Brandes and Erlebach [BE05]_.

Goals
-----
NetworkX is intended to provide

-  tools for the study of the structure and
   dynamics of social, biological, and infrastructure networks,

-  a standard programming interface and graph implementation that is suitable
   for many applications,

-  a rapid development environment for collaborative, multidisciplinary
   projects,

-  an interface to existing numerical algorithms and code written in C,
   C++, and FORTRAN,

-  the ability to painlessly slurp in large nonstandard data sets.


The Python programming language
-------------------------------

Python is a powerful programming language that allows simple and flexible representations of networks, and  clear and concise expressions of network algorithms (and other algorithms too).  Python has a vibrant and growing ecosystem of packages that NetworkX uses to provide more features such as numerical linear algebra and drawing.  In addition
Python is also an excellent "glue" language for putting together pieces of software from other languages which allows reuse of legacy code and engineering of high-performance algorithms [Langtangen04]_.

Equally important, Python is free, well-supported, and a joy to use.

In order to make the most out of NetworkX you will want to know how to write basic programs in Python.
Among the many guides to Python, we recommend the documentation at
http://www.python.org and the text by Alex Martelli [Martelli03]_.

Free software
-------------

NetworkX is free software; you can redistribute it and/or
modify it under the terms of the :doc:`BSD License </reference/legal>`.
We welcome contributions from the community.  Information on
NetworkX development is found at the NetworkX Developer Zone at Github
https://github.com/networkx/networkx


History
-------


NetworkX was born in May 2002. The original version was designed and written by Aric Hagberg, Dan Schult, and Pieter Swart in 2002 and 2003.
The first public release was in April 2005.

Many people have contributed to the success of NetworkX. Some of the contributors are listed in the :doc:`credits. </reference/credits>`



What Next
^^^^^^^^^
.. todo::

   Update links below.


   
 - :doc:`A Brief Tour </tutorial/tutorial>`

 - :doc:`Installing </install>`

 - :doc:`Reference </reference/index>`

 - :doc:`Examples </examples/index>`
