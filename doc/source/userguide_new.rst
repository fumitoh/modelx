Tutorial
========

This tutorial aims to show how to use modelx by going through some examples.

This tutorial supplements modelx reference,
which is build from docstrings of the API functions and classes.
The reference should cover the details of each API element,
which may not be fully explained in this tutorial.

Overview
--------

Interfacing with modelx
^^^^^^^^^^^^^^^^^^^^^^^

modelx is a Python package, and Python interpreter

Interactive mode
IPython console
Importing modelx
Spyder plugin for modelx
Model structure


modelx is a Python package, and you use it by writing a Python script
and importing it, as you would normally do with any other Python package.

modelx is best suited for building complex numerical models composed of
many formulas referencing each other, so when you start from scratch,
the typical workflow would be to first write code for building a model,
and then evaluate the model.

As we are going to see, it takes more than one line of code to build a model,
so it's convenient to use a Python shell that allows you edit and execute
a chunk of code at once for building a model, then get into an interative mode
for letting you examine the model one expression or statement at a time.

IDLE, the Tk/Tcl based simple Python GUI shell that comes with CPython
lets you do that. You can open an editor window, and when the part of
building a model is done, you can press F5 to save and run the script
in a Python shell window where you are prompted to enter Python code to
evaluate the model. Jupyter Notebook and many other popular Python shell
environments have similar capability.

Building a Model
----------------

Creating a Model
Creating a Space
Creating a Cells
Creating a Reference

Accessing Objects
-----------------

Getting Models
The Current Model
Attribute access
Getting Spaces
The Current Space
Getting Cells

Accessing values
----------------

Getting Values
Setting Values
Clearing Values


More on Cells
-------------
Scalar Cells

Understanding Spaces
--------------------
Space Components
Space as a Namespace
Space Trees

Understanding Inheritance
-------------------------

Overriding Base Members
Multiple Inheritance
Inheriting a Space Tree

Parameterizing Spaces
---------------------

Importing/Exporting Data
------------------------

Importing Excel files
Exporting to Pandas objects