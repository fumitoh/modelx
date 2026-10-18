# Copyright (c) 2017-2026 Fumito Hamamura <fumito.ham@gmail.com>

# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation version 3.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.

from modelx.core.execution.trace import (
    OBJ, KEY, get_node, get_node_repr, TraceObject
)


class BaseNode:
    """Base class for all Node classes

    See Also:
        * :class:`ItemNode`: Node representing a cells evaluation
        * :class:`~modelx.core.reference.ReferenceNode`: Node representing a reference

    .. versionadded:: 0.15.0

    """

    __slots__ = ("_impl",)

    def __init__(self, node):
        self._impl = node

    def __eq__(self, other):
        return (self._impl[OBJ] is other._impl[OBJ] and
                self._impl[KEY] == other._impl[KEY])

    def __hash__(self):
        return hash((self._impl[OBJ], self._impl[KEY]))

    @property
    def obj(self):
        """Return the Cells object"""
        return self._impl[OBJ].interface

    @property
    def args(self):
        """Return a tuple of the cells' arguments."""
        return self._impl[KEY]

    def has_value(self):
        """Return :obj:`True` if the cell has a value."""
        return self._impl[OBJ].has_node(self._impl[KEY])

    @property
    def value(self):
        """Return the value of the cells."""
        if self.has_value():
            return self._impl[OBJ].get_value_from_key(self._impl[KEY])
        else:
            raise ValueError("Value not found")

    @property
    def preds(self):
        """A list of nodes that this node refers to."""
        return self.obj.preds(*self.args)

    @property
    def succs(self):
        """A list of nodes that refer to this  node."""
        return self.obj.succs(*self.args)

    # preds, succs and precedents of an ItemNode with no stored value raise
    # ValueError ("... has no cached value for the given arguments", or
    # "... is not cached" for a Cells whose is_cached is False), so before
    # 0.34 both dicts below raised it. They give None there, as 'value'
    # does. An ObjectNode, a ReferenceNode included, has no arguments
    # (args is None) and empty lists, so it keeps giving 0.

    @property
    def _baseattrs(self):
        """The older form of :meth:`_get_attrdict`, kept for existing tools.

        Returns:
            dict: The keys of :meth:`_get_attrdict` except ``'valid'``
            and ``'precedentslen'``, with ``'obj'`` from the object's
            ``_baseattrs``.

        .. versionchanged:: 0.34.0
            An :class:`ItemNode` with no stored value gives :obj:`None`
            for ``'predslen'`` and ``'succslen'``, where it raised
            :obj:`ValueError`.
        """
        has_value = self.has_value()
        has_lists = has_value or self.args is None
        result = {
            "type": type(self).__name__,
            "obj": self.obj._baseattrs,
            "args": self.args,
            "value": self.value if has_value else None,
            "predslen": len(self.preds) if has_lists else None,
            "succslen": len(self.succs) if has_lists else None,
            "repr_parent": self.obj._impl.repr_parent(),
            "repr": self.obj._get_repr(),
        }

        return result

    def _get_attrdict(self, extattrs=None, recursive=True):
        """A dict that describes the node.

        ``extattrs`` and ``recursive`` are passed to the node's object,
        so the names in ``extattrs`` are added to ``'obj'``.

        Returns:
            dict: ``'type'``, the class name of the node;
            ``'obj'``, the dict of the node's object;
            ``'args'``, the arguments, or :obj:`None` for a
            :class:`~modelx.core.reference.ReferenceNode`;
            ``'value'``, the value, or :obj:`None` when there is none;
            ``'valid'``, the :func:`id` of the value, or :obj:`None`;
            ``'predslen'``, ``'succslen'`` and ``'precedentslen'``,
            the lengths of :attr:`preds`, :attr:`succs` and
            ``precedents``, or :obj:`None` for an :class:`ItemNode`
            with no stored value;
            and ``'repr_parent'`` and ``'repr'``, display strings of
            the parent of the node's object and of the object. An
            ItemSpace in them shows its arguments, as in
            ``'Model1.Proj[1][5]'``.

        .. versionchanged:: 0.34.0
            An :class:`ItemNode` with no stored value gives :obj:`None`
            for ``'predslen'``, ``'succslen'`` and ``'precedentslen'``,
            where it raised :obj:`ValueError`.
            For an object in an ItemSpace of an ItemSpace,
            ``'repr_parent'`` and ``'repr'`` name the parent item by its
            arguments, as in ``'Model1.Proj[1][5]'``, where they gave
            its ``__SpaceN`` name, as in ``'Model1.__Space1[5]'``.
        """
        has_value = self.has_value()
        has_lists = has_value or self.args is None
        result = {
            "type": type(self).__name__,
            "obj": self.obj._get_attrdict(extattrs, recursive),
            "args": self.args,
            "value": self.value if has_value else None,
            "valid": id(self.value) if has_value else None,
            "predslen": len(self.preds) if has_lists else None,
            "succslen": len(self.succs) if has_lists else None,
            "precedentslen": len(self.precedents) if has_lists else None,
            "repr_parent": self.obj._impl.repr_parent(),
            "repr": self.obj._get_repr(),
        }
        return result

    def _get_repr(self, fullname=True, add_value=False):
        """The display string of the node.

        It is the display name of the node's object, as
        ``obj._get_repr(fullname, add_params=False)`` gives it, followed
        by the node's arguments by parameter name, each formatted by
        :func:`repr`, as in ``'BasicTerm_S.Projection[2].claims(t=3)'``.
        An ItemSpace in it shows its arguments, as in
        ``'Model1.Proj[1][5].bar()'``. A
        :class:`~modelx.core.reference.ReferenceNode` has no arguments,
        and gives the display name of its Reference, as in
        ``'Model1.Proj[1].i'``.

        With ``add_value=True``, a node that has a value is followed by
        ``'='`` and the :func:`repr` of the value, with a line break
        before a value whose :func:`repr` spans lines. That is the
        :func:`repr` of the node.

        Args:
            fullname(:obj:`bool`, optional): Start with the name of
                the Model. Defaults to :obj:`True`.
            add_value(:obj:`bool`, optional): Add the value, if the
                node has one. Defaults to :obj:`False`.

        Returns:
            str: The display string, such as
            ``'BasicTerm_S.Projection[2].claims(t=3)'``.

        .. versionadded:: 0.34.0
        """
        obj = self.obj  # a new proxy on each read for a ReferenceNode
        result = obj._get_repr(fullname=fullname, add_params=False)
        args = self.args

        if args is not None:    # ItemNode
            params = obj._impl.formula.parameters
            result += "(" + ", ".join(
                "%s=%s" % (param, repr(arg)) for param, arg in
                zip(params, args)
            ) + ")"
        elif not hasattr(obj, "formula"):   # ReferenceNode, or a Model's
            pass
        elif obj.formula is not None:   # a Cells', or a Space's with one
            result += "(" + ", ".join(obj.parameters) + ")"

        if add_value and self.has_value():
            valrepr = repr(self.value)
            if "\n" in valrepr:
                valrepr = "\n" + valrepr
            result += "=" + valrepr

        return result

    def __repr__(self):
        return self._get_repr(fullname=True, add_value=True)


class ItemNode(BaseNode):
    """Node class to represent elements of Cells and Spaces

    This class
    is for representing *elements* of :class:`~modelx.core.cells.Cells` objects
    and Space objects such as :class:`~modelx.core.space.UserSpace`.
    An *element* of a :class:`~modelx.core.cells.Cells` object is identified
    by arguments to the :class:`~modelx.core.cells.Cells`.
    If the :class:`~modelx.core.cells.Cells` has a value for the arguments,
    whether it's calculated or input, the :meth:`has_value`
    returns :obj:`True` and :attr:`value` returns the value.
    Similarly to the :class:`~modelx.core.cells.Cells` element,
    an element of a Space is identified by arguments to the Space.
    Since a call to the Space returns an :class:`~modelx.core.space.ItemSpace`,
    the value of the Space's element is the :class:`~space.ItemSpace` object
    if it ever exists.

    .. seealso::

        :class:`BaseNode`, :class:`~modelx.core.reference.ReferenceNode`

    .. versionchanged:: 0.15.0
        Renamed to ItemNode from Element.

    """

    __slots__ = ()

    @property
    def precedents(self):
        """Return the precedents

        .. seealso::

            :meth:`Cells.precedents<modelx.core.cells.Cells.precedents>`,
            :meth:`Space.precedents<modelx.core.space.UserSpace.precedents>`

        """
        return self.obj.precedents(*self.args)


class ObjectNode(BaseNode):
    __slots__ = ()

    def __eq__(self, other):
        return self._impl[OBJ] is other._impl[OBJ]

    def __hash__(self):
        return hash(self._impl[OBJ])

    @property
    def obj(self):
        """Return the ReferenceProxy object"""
        return self._impl[OBJ].interface

    @property
    def args(self):
        """Return a tuple of the cells' arguments."""
        return None

    def has_value(self):
        return False

    @property
    def value(self):
        return None

    @property
    def preds(self):
        """A list of nodes that this node refers to."""
        return []

    @property
    def succs(self):
        """A list of nodes that refer to this  node."""
        return []

    @property
    def precedents(self):
        return []

    # @property
    # def dependents(self):
    #     pass


class NodeFactory:

    _impl: TraceObject
    __slots__ = ()

    def node(self, *args, **kwargs):
        """Return a Node object for the given arguments."""
        return ItemNode(get_node(self._impl, args, kwargs))

    def preds(self, *args, **kwargs):
        """Return a list of predecessors of a cell.

        This method returns a list of ItemNode objects, whose elements are
        predecessors of (i.e. referenced in the formula
        of) the cell specified by the given arguments.
        """
        return self._impl.predecessors(args, kwargs)

    def succs(self, *args, **kwargs):
        """Return a list of successors of a cell.

        This method returns a list of ItemNode objects, whose elements are
        successors of (i.e. referencing in their formulas)
        the cell specified by the given arguments.
        """
        return self._impl.successors(args, kwargs)

    def precedents(self, *args, **kwargs):
        """Return a list of the precedents.

        This is a method of Cells and Space types,
        and returns a list of :class:`Node<modelx.core.node.BaseNode>`
        objects that are precedents of the object's node specified by
        the arguments passed to the method.

        The :meth:`preds` method is similar to this method, but
        :meth:`preds` only lists nodes of Cells and Spaces.
        This method also lists nodes of Reference values in addition to
        the nodes of Cells and Spaces returned by :meth:`preds`.

        .. code-block:: python

            import modelx as mx

            space = mx.new_space()
            space.new_space('Child')
            space.Child.new_space('GrandChild')

            space.x = 1
            space.Child.y = 2
            space.Child.GrandChild.z = 3

            @mx.defcells(space=space)
            def foo(t):
                return t

            @mx.defcells(space=space)
            def bar(t):
                return foo(t) + x + Child.y + Child.GrandChild.z


        The ``bar`` Cells depends on one Cells ``foo``, and 3 References,
        ``x``, ``Child.y``, and ``Child.GrandChild.z``.
        Below, ``bar.preds(3)`` returns a list containing ``foo(3)``,
        which is the only Cells element that ``bar(3)`` depends on::

            >>> bar(3)
            9

            >>> bar.preds(3)
            [Model1.Space1.foo(t=3)=3]

        The :meth:`precedents` method returns a list containing not only
        Cells elements,
        but also References that ``bar(3)``
        depends on when calculating its value::

            >>> bar.precedents(3)
            [Model1.Space1.foo(t=3)=3,
             Model1.Space1.x=1,
             Model1.Space1.Child.GrandChild.z=3,
             Model1.Space1.Child.y=2]

        References whose values are modelx objects, such as
        :class:`~modelx.core.cells.Cells` and
        :class:`Spaces <modelx.core.space.UserSpace>`,
        are not included in the lists
        returned by this method.

        .. seealso::

            :meth:`preds`, :meth:`succs`, :meth:`node`

        .. versionadded:: 0.15.0

        """
        return (self.preds(*args, **kwargs)
            + self._impl.get_valuerefs()
                + self._impl.get_attrpreds(args, kwargs))


class BaseNodeFactoryImpl:

    __slots__ = ()
    __mixin_slots = ()

    # ----------------------------------------------------------------------
    # Dependency

    def _check_cached(self, node):
        obj = node[OBJ]
        if not obj.is_cached:
            raise ValueError(
                "%s is not cached"
                % obj.get_repr(fullname=True, add_params=False)
            )
        if not obj.has_node(node[KEY]):
            raise ValueError(
                "%s has no cached value for the given arguments"
                % get_node_repr(node)
            )

    def predecessors(self, args, kwargs):
        node = get_node(self, args, kwargs)
        self._check_cached(node)
        preds = self.model.tracegraph.predecessors(node)
        return [ObjectNode(n) if len(n) < 2 else ItemNode(n) for n in preds]

    def successors(self, args, kwargs):
        node = get_node(self, args, kwargs)
        self._check_cached(node)
        succs = self.model.tracegraph.successors(node)
        return [ItemNode(n) for n in succs]

    def get_attrpreds(self, args, kwargs):
        node = get_node(self, args, kwargs)
        if node in self.model.refgraph:
            preds = self.model.refgraph.predecessors(node)
            return [ref.to_node() for ref in preds]
        else:
            return []

    def get_value_from_key(self, key):
        raise NotImplementedError

    def has_node(self, key):
        raise NotImplementedError

    def to_node(self):
        return ObjectNode(get_node(self, None, None))

    def set_value_from_key(self, key, value):
        pass

    def clear_value_at(self, key, clear_input=True):
        pass


class NodeFactoryImpl(BaseNodeFactoryImpl, TraceObject):
    pass

