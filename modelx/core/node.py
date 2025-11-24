# Copyright (c) 2017-2025 Fumito Hamamura <fumito.ham@gmail.com>

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

from modelx.core.execution.trace import OBJ, KEY, get_node, TraceObject, ParentTraceObject


class BaseNode:
    """Base class for all Node classes

    .. seealso::

        :class:`ItemNode`, :class:`~modelx.core.reference.ReferenceNode`

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

    @property
    def _baseattrs(self):
        """A dict of members expressed in literals"""

        result = {
            "type": type(self).__name__,
            "obj": self.obj._baseattrs,
            "args": self.args,
            "value": self.value if self.has_value() else None,
            "predslen": len(self.preds),
            "succslen": len(self.succs),
            "repr_parent": self.obj._impl.repr_parent(),
            "repr": self.obj._get_repr(),
        }

        return result

    def _get_attrdict(self, extattrs=None, recursive=True):

        result = {
            "type": type(self).__name__,
            "obj": self.obj._get_attrdict(extattrs, recursive),
            "args": self.args,
            "value": self.value if self.has_value() else None,
            "predslen": len(self.preds),
            "succslen": len(self.succs),
            "precedentslen": len(self.precedents),
            "repr_parent": self.obj._impl.repr_parent(),
            "repr": self.obj._get_repr(),
        }
        return result

    def __repr__(self):
        raise NotImplementedError


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

    def __repr__(self):

        name = self.obj._get_repr(fullname=True, add_params=False)
        params = self.obj._impl.formula.parameters

        arglist = ", ".join(
            "%s=%s" % (param, repr(arg)) for param, arg in
            zip(params, self.args)
        )

        if self.has_value():
            valrepr = repr(self.value)
            if "\n" in valrepr:
                valrepr = "\n" + valrepr
            return name + "(" + arglist + ")" + "=" + valrepr
        else:
            return name + "(" + arglist + ")"


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

    def __repr__(self):

        name = self.obj._get_repr(fullname=True, add_params=False)

        if not hasattr(self.obj, "formula"):    # for Reference
            params = None
        elif self.obj.formula is None:      # for Space
            params = None
        else:
            params = ", ".join(self.obj.parameters)

        if self.has_value():
            valrepr = repr(self.value)
            if "\n" in valrepr:
                valrepr = "\n" + valrepr
            if params is None:
                return name + "=" + valrepr
            else:
                return name + "(" + params + ")" + "=" + valrepr
        else:
            if params is None:
                return name
            else:
                return name + "(" + params + ")"


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

    def predecessors(self, args, kwargs):
        node = get_node(self, args, kwargs)
        preds = self.model.tracegraph.predecessors(node)
        return [ObjectNode(n) if len(n) < 2 else ItemNode(n) for n in preds]

    def successors(self, args, kwargs):
        node = get_node(self, args, kwargs)
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


class ParentNodeFactoryImpl(BaseNodeFactoryImpl, ParentTraceObject):
    pass