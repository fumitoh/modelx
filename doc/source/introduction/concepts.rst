========
Concepts
========


Model
=====
Models are to modelx what workbooks are to a spreadsheet application.
Model is a unit of work.
Models contain spaces.

Space
=====
Spaces are to modelx what worksheets are to a spreadsheet application.
A space contains cells, and/or other spaces.

A space can resides in another space or directly in its containing model.

A space contained in another space is called subspace or child space
of the containing space.

Space objects contain cells. All cells are contained in one and
only one space.

Subspace
--------
A subspace of another space is a space contained in the other space.


Space inheritance
-----------------
You can create a derived space from a base space.
A derived space inherits cells, child spaces and names.

Space factory
-------------
Spaces can have factory functions to generate its

Space as a namespace
--------------------
Spaces serve as namespaces to the formulas of the contained cells.


Cells
=====
Cells objects are contained in spaces.
Each cells object is contained in one and only one space.


