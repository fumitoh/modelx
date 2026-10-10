Formula
=======

.. currentmodule:: modelx.core.formula

A *Formula* holds the definition of a :class:`~modelx.core.cells.Cells`,
of a Space's parameters, or of a :class:`~modelx.core.macro.Macro`:
the source text and the Python function made from it.
modelx creates Formula objects; you get them from these properties:

* :attr:`Cells.formula <modelx.core.cells.Cells.formula>`
* :attr:`UserSpace.formula <modelx.core.space.UserSpace.formula>`,
  and the ``formula`` of an :class:`~modelx.core.space.ItemSpace`
  or a :class:`~modelx.core.space.DynamicSpace`
* :attr:`Macro.formula <modelx.core.macro.Macro.formula>`

The representation of a Formula is its source, so a Formula prints as
the code that defines it::

    >>> import modelx as mx

    >>> space = mx.new_model("Model1").new_space("Space1")

    >>> @mx.defcells
    ... def foo(x, y=2):
    ...     """Docstring of foo"""
    ...     return x + y

    >>> foo.formula
    def foo(x, y=2):
        """Docstring of foo"""
        return x + y
    <BLANKLINE>

    >>> foo.formula.parameters
    ('x', 'y')

    >>> foo.formula.name
    'foo'

To change the formula of a Cells or a Space, assign a function,
a lambda expression or a string to its ``formula`` property,
as in ``foo.formula = "lambda x: x"``.
Treat a Formula object as read-only.


Formulas of Cells and Spaces
----------------------------

* :attr:`Cells.formula <modelx.core.cells.Cells.formula>` is never
  :obj:`None`.
  A Cells created without a formula, or whose formula was deleted by
  ``del cells.formula``, has a formula whose source is ``'lambda: None'``
  and whose :attr:`~Formula.parameters` is ``()``.

* The ``formula`` of a Space is :obj:`None` while the Space has no formula,
  and the Space's ``parameters`` is then :obj:`None` as well.
  A Space formula without parameters, such as ``lambda: None``,
  has ``()`` as its :attr:`~Formula.parameters`.

* A formula given as a function definition is renamed after its Cells
  (or Macro): assigning ``def bar(z): ...`` to the formula of the Cells
  ``foo`` gives the source ``def foo(z): ...``. The definition of a Space
  formula is renamed ``_formula``. A lambda expression keeps its text.

* Formula objects are shared. Unless the Space formula returns a
  ``'base'``, an :class:`~modelx.core.space.ItemSpace`
  has the same Formula object as the Space that it is an item of,
  and each Cells in the ItemSpace has the same Formula object as the Cells
  of that name in the Space.
  A Cells that a sub Space inherits from its base Space
  has the base Cells' Formula object until the sub Space defines its own::

    >>> sub = space.model.new_space("Sub", bases=space)

    >>> sub.foo.formula is foo.formula
    True

* Formula objects do not define equality: ``==`` is :obj:`True` only for
  the same object. Compare :attr:`~Formula.source` to compare definitions.


Formula class
-------------

.. class:: Formula

   The class of the objects that the ``formula`` properties return.
   The formula of a Space is an instance of a subclass of this class.

   .. attribute:: source
      :type: str

      The source text of the formula.
      It is a function definition, ending with a newline,
      or a lambda expression, such as ``'lambda x: x * 2'``.
      ``repr()`` and ``str()`` of the Formula return it.

      It is :obj:`None` when modelx could not retrieve the source code
      of the function the formula was made from.
      modelx then warns with a ``UserWarning``,
      "Cannot retrieve source code for function ...".

   .. attribute:: parameters
      :type: tuple of str

      The names of the parameters, in order, such as ``('x', 'y')``;
      ``()`` when the formula has none.
      :attr:`Cells.parameters <modelx.core.cells.Cells.parameters>`
      returns the same tuple, and so does a Space's ``parameters``
      when the Space has a formula.

   .. attribute:: name
      :type: str

      The name of :attr:`func`:

      * the name of the Cells, for the formula of a Cells,
        whether it is a definition or a lambda expression;
      * ``'_formula'``, for the formula of a Space;
      * the name of the Macro, for the formula of a Macro;
      * ``'<lambda>'``, for the formula of a Cells that has no formula
        (source ``'lambda: None'``).

      When :attr:`source` is :obj:`None`, it is the name of the original
      function.

   .. attribute:: signature
      :type: inspect.Signature

      The :class:`inspect.Signature` of :attr:`func`,
      with its defaults and annotations, such as ``(x: int, y=3)``.

   .. attribute:: func
      :type: function

      The Python function made from :attr:`source`.
      Its docstring is the docstring of the definition.

      modelx does not call this function to evaluate a Cells:
      it evaluates the formula with the names of the Space the Cells
      belongs to. Calling :attr:`func` yourself runs the code outside
      modelx: the names that the formula reads from its Space are not
      defined there, so it raises :obj:`NameError` if it reads any,
      and no value is stored in the Cells.

      When :attr:`source` is :obj:`None`, :attr:`func` is the original
      function the formula was made from, and calling it runs that
      function with its own global names.

   .. attribute:: module
      :type: str or None

      The name of the module in which the function was defined,
      such as ``'__main__'``,
      when the formula was made from a Python function object.
      :obj:`None` otherwise, for example for a formula given as a string,
      and for the formulas of a model read by :func:`~modelx.read_model`.

.. seealso::

   * :attr:`Cells.formula <modelx.core.cells.Cells.formula>` and
     :ref:`cells-formula-operations`
   * :attr:`UserSpace.formula <modelx.core.space.UserSpace.formula>`,
     :meth:`UserSpace.set_formula <modelx.core.space.UserSpace.set_formula>`
     and :meth:`UserSpace.del_formula <modelx.core.space.UserSpace.del_formula>`
