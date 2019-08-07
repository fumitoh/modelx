Space
=====


Space objects are

Any space is contained in exactly one parent.
The parent of a space can be a model or another space.
The parent of any static space is either a model or a static space.
The parent of any dynamic space is either a dynamic space or a static space.

Any dynamic space


Space members
--------------




Child spaces and space tree
---------------------------
As mentioned above, spaces can contain other spaces.
A space that contains other spaces is called the *parent* space of the other spaces, and the other spaces are called *child* spaces of the parent space.

By recursively creating child spaces in another space's child spaces, you can create a tree of spaces. A tree of spaces originating a space are called *descendant* spaces of the space. In turn *ascendant* spaces of a space are those that have the space as their descendant space.

Child spaces can not 'outlive' their parent space. In other words, a parent space owns its child spaces i.e. when the parent space is deleted, its child spaces, if there are any, are deleted too.

.. note::

   In OOP contexts, the terms 'parent' and 'child' are sometimes used interchangeably with 'base' and 'sub' respectively.
   The readers should be aware that here in this reference for modelx, we use the terms 'parent' and 'child' in
   composition contexts exclusively, and the terms 'sub' and 'base' exclusively in inheritance contexts.


Space as namespace
------------------



Child cells
------------------


Reference
------------------

Space Inheritance
------------------

Space formula
-------------

Static and Dynamic Space
------------------------

Index reference
---------------


API reference
-------------

.. toctree::

   ../reference/generated/modelx.core.space.UserSpace
   ../reference/generated/modelx.core.space.DynamicSpace