
Concept Description
===================


**modelx** embodies software engineering concepts in Object-oriented programming (OOP) paradigm, such as composition and inheritance. However, modelx is not a programming language, rather it is a system of objects. So, some of the OOP terminologies are redefined for the purpose of describing modelx specifications below, although there is strong resemblance. In reading the specifications, readers should be aware that the meanings of the terms in modelx may differ from those in the context of OOP.

Core modelx Types
-----------------

Model, Space, and Cells are the core modelx types exposed to users for manipulation.
Models are the top level objects that contain spaces. Spaces can contain other spaces, so a tree of spaces originating a model can be formed in the model. See '`Space Composition`_' section for more details.

Spaces are intermediate objects that come between models and cells in the object composition hierarchy of modelx. Spaces can contain cells, other spaces and references.

A cells can have a formula that calculates the cells' values, just like
spreadsheet cells can have formulas. Cells values can be either calculated
by the formula or assigned as input.

Space Composition
-----------------

*Parent and Child spaces*

As mentioned above, spaces can contain other spaces. A space that contains other spaces is called the *parent* space of the other spaces, and the other spaces are called *child* spaces of the parent space.

By recursively creating child spaces in another space's child spaces, you can create a tree of spaces. A tree of spaces originating a space are called *descendant* spaces of the space. In turn *ascendant* spaces of a space are those that have the space as their descendant space.

Child spaces can not 'outlive' their parent space. In other words, a parent space owns its child spaces i.e. when the parent space is deleted, its child spaces, if there are any, are deleted too.

.. note::

   In OOP contexts, the terms 'parent' and 'child' are sometimes used interchangeably with 'base' and 'sub' respectively.
   The readers should be aware that here in this reference for modelx, we use the terms 'parent' and 'child' in
   composition contexts exclusively, and the terms 'sub' and 'base' exclusively in inheritance contexts.

Space Inheritance
-----------------

*Base and Sub spaces*

If a space inherits other spaces, the inherited spaces are called *base* spaces of the inheriting space, and the inheriting space is called a *sub* space of the inherited spaces. Multiple inheritance is allowed, i.e. a space can have more than
one base spaces.

Since a space that inherits base spaces can in turn be the base space of other spaces, you can create a directional graph of the inheritance relationship.
We use the term base spaces of a space to mean not just those spaces that are directly inherited by the space, but also those that are inherited indirectly, through chains of inheritance. In turn, if a space is a base space of another space, then the other space is a sub space of the space either directly or indirectly.

When a space inherits another space that has descendant spaces, descendant spaces are created in the sub space.
The descendant spaces in the sub space compose the same tree hierarchy as that in the base space.
Each descendant space in the sub space inherits the corresponding space in the space tree of the base space.

A space cannot inherit its descendant spaces.
Later in this document, the distinction between static and dynamic spaces is introduced.
Static spaces cannot be inherited by their descendant spaces, as that would form circular inheritance.
Dynamic spaces can be inherited by their descendant spaces.

.. note::

    The space inheritance concept explained above is analogous to that in OOP. However, the term 'derived' has a special meaning in modelx context. In OOP contexts, 'a class deriving another class' is synonymous with 'the other class inheriting the class'.


Defined and Derived spaces
--------------------------

If a space inherits another space, the child spaces, cells and refs of the base space are derived in the sub space. Furthermore, the descendant spaces and their members of the descendant spaces are derived. The derived spaces have the original corresponding spaces in the base space as their base spaces.

Every static space is either a defined space or a derived space.

Overriding members
------------------

Derived cells and refs are overridden when new cells and refs are defined with the same name as the derived cells and refs.

Derived spaces cannot be overridden, however, members of derived spaces can be added or overridden. When members of a derived space are added or overridden,
the derived space and its derived ascendant spaces become defined.

Spaces that are directly contained in a model, i.e. spaces that are not child spaces of any other spaces, are always defined spaces.


Static and Dynamic spaces
-------------------------

Every space is either a static space or a dynamic space.

Static spaces are those that are created explicitly by calling their parents' methods, or automatically by the space inheritance mechanism. Spaces that are directly contained in a model, i.e. spaces that are not child spaces of any other spaces, are always static spaces. Since they are always defined, they are always defined and static spaces.

Dynamic spaces, a.k.a parametrized spaces, are those that are created upon the first call or subscription operations on their parent spaces. Such parent spaces must have associated formulas that define parameters of the dynamic spaces and return arguments to be passed to the dynamic spaces for their initialization.

Dynamic spaces can have child spaces just like static spaces, either by calling their methods, or automatically by inheriting base spaces. A dynamic space and its descendants are collectively called a dynamic space tree.

A dynamic space can also have dynamic spaces in its dynamic space tree.

Spaces that are in dynamic space trees cannot be base spaces of other spaces.

Dynamic spaces are not inherited, i.e. if a static ascendant space of dynamic spaces are inherited,
no derived spaces in the sub space are created, that correspond to the dynamic spaces in the base space.
