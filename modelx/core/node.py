# Copyright (c) 2017-2021 Fumito Hamamura <fumito.ham@gmail.com>

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

from collections.abc import Sequence

OBJ = 0
KEY = 1

# class HasFormula:
#
#     self.data
#     self.formula
#
#     @property
#     def is_scalar(self):
#         return len(self.parameters) == 0
#
#     @property
#     def parameters(self):
#         return self.signature.paramters
#
#     @property
#     def signature(self):
#         return self.formula.signature
#


def node_has_key(node):
    return len(node) > 1


def key_to_node(obj, key):
    """Return node form object ane ky"""
    return (obj, key)


def get_node(obj, args, kwargs):
    """Create a node from arguments and return it"""

    if args is None and kwargs is None:
        return (obj,)

    if kwargs is None:
        kwargs = {}
    return obj, _bind_args(obj, args, kwargs)


def node_get_args(node):
    """Return an ordered mapping from params to args"""
    obj = node[OBJ]
    key = node[KEY]
    boundargs = obj.formula.signature.bind(*key)
    boundargs.apply_defaults()
    return boundargs.arguments


def tuplize_key(obj, key, remove_extra=False):
    """Args"""

    if key.__class__ is tuple:  # Not isinstance(key, tuple) for speed
        pass
    else:
        key = (key,)

    if not remove_extra:
        return key
    else:
        paramlen = len(obj.formula.parameters)
        arglen = len(key)
        if arglen:
            return key[: min(arglen, paramlen)]
        else:
            return key


def _bind_args(obj, args, kwargs):
    boundargs = obj.formula.signature.bind(*args, **kwargs)
    boundargs.apply_defaults()
    return tuple(boundargs.arguments.values())


def get_node_repr(node):

    obj = node[OBJ]
    key = node[KEY]

    name = obj.get_repr(fullname=True, add_params=False)
    params = obj.formula.parameters

    arglist = ", ".join(
        "%s=%s" % (param, arg) for param, arg in zip(params, key)
    )

    if key in obj.data:
        return name + "(" + arglist + ")" + "=" + str(obj.data[key])
    else:
        return name + "(" + arglist + ")"


class BaseElement:
    """A combination of a modelx object, its args and its value."""

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
        """Return ``True`` if the cell has a value."""
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


class Element(BaseElement):
    """Elements of Cells and Spaces"""
    __slots__ = ()

    @property
    def precedents(self):
        return (self.preds + self._impl[OBJ].get_valuerefs()
                + self._impl[OBJ].get_attrpreds(self.args, {}))

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


class ObjectElement(BaseElement):
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


class ElementFactory:

    __slots__ = ()

    def node(self, *args, **kwargs):
        """Return a :class:`Element` object for the given arguments."""
        return Element(get_node(self._impl, args, kwargs))

    def preds(self, *args, **kwargs):
        """Return a list of predecessors of a cell.

        This method returns a list of Element objects, whose elements are
        predecessors of (i.e. referenced in the formula
        of) the cell specified by the given arguments.
        """
        return self._impl.predecessors(args, kwargs)

    def succs(self, *args, **kwargs):
        """Return a list of successors of a cell.

        This method returns a list of Element objects, whose elements are
        successors of (i.e. referencing in their formulas)
        the cell specified by the given arguments.
        """
        return self._impl.successors(args, kwargs)

    def precedents(self, *args, **kwargs):
        return (self.preds(*args, **kwargs)
            + self._impl.get_valuerefs()
                + self._impl.get_attrpreds(args, kwargs))


class ElementFactoryImpl:

    __slots__ = ()

    # ----------------------------------------------------------------------
    # Dependency

    def predecessors(self, args, kwargs):
        node = get_node(self, args, kwargs)
        preds = self.model.tracegraph.predecessors(node)
        return [Element(n) for n in preds]

    def successors(self, args, kwargs):
        node = get_node(self, args, kwargs)
        succs = self.model.tracegraph.successors(node)
        return [Element(n) for n in succs]

    def get_attrpreds(self, args, kwargs):
        node = get_node(self, args, kwargs)
        if node in self.model.refgraph:
            preds = self.model.refgraph.predecessors(node)
            return [ref.to_element() for ref in preds]
        else:
            return []

    def get_value_from_key(self, key):
        raise NotImplementedError

    def has_node(self, key):
        raise NotImplementedError

    def to_element(self):
        return ObjectElement(get_node(self, None, None))
