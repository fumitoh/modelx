# Copyright (c) 2017-2019 Fumito Hamamura <fumito.ham@gmail.com>

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

from textwrap import dedent
import warnings
from collections import namedtuple
from collections.abc import Mapping, Callable, Sized, Sequence
from itertools import combinations

from modelx.core.base import Impl, Derivable, Interface, BoundFunction
from modelx.core.node import OBJ, KEY, get_node, tuplize_key
from modelx.core.formula import Formula, NullFormula, NULL_FORMULA
from modelx.core.util import is_valid_name
from modelx.core.errors import NoneReturnedError, RewindStackError


def convert_args(args, kwargs):
    """If args and kwargs contains Cells, Convert them to their values."""

    found = False
    for arg in args:
        if isinstance(arg, Cells):
            found = True
            break

    if found:
        args = tuple(
            arg.value if isinstance(arg, Cells) else arg for arg in args
        )

    if kwargs is not None:
        for key, arg in kwargs.items():
            if isinstance(arg, Cells):
                kwargs[key] = arg.value

    return args, kwargs


class CellsMaker:
    def __init__(self, *, space, name):
        self.space = space  # SpaceImpl
        self.name = name

    def __call__(self, func):
        return self.space.new_cells(formula=func, name=self.name).interface


ArgsValuePair = namedtuple("ArgsValuePair", ["args", "value"])


class Cells(Interface, Mapping, Callable):
    """Data container with a formula to calculate its own values.

    Cells are created by ``new_cells`` method or its variant methods of
    the containing space, or by function definitions with ``defcells``
    decorator.
    """

    __slots__ = ()

    def __contains__(self, key):
        return self._impl.has_cell(tuplize_key(self, key))

    def __getitem__(self, key):
        return self._impl.get_value(tuplize_key(self, key))

    def __call__(self, *args, **kwargs):
        return self._impl.get_value(args, kwargs)

    def match(self, *args, **kwargs):
        """Returns the best matching args and their value.

        If the cells returns None for the given arguments,
        continue to get a value by passing arguments
        masking the given arguments with Nones.
        The search of non-None value starts from the given arguments
        to the all None arguments in the lexicographical order.
        The masked arguments that returns non-None value
        first is returned with the value.
        """
        return self._impl.find_match(args, kwargs)

    def __len__(self):
        return len(self._impl.data)

    def __setitem__(self, key, value):
        """Set value of a particular cell"""
        self._impl.set_value(tuplize_key(self, key), value)

    def __iter__(self):
        def inner():  # For single parameter
            for key in self._impl.data.keys():
                yield key[0]

        if len(self._impl.formula.parameters) == 1:
            return inner()
        else:
            return iter(self._impl.data)

    def copy(self, space=None, name=None):
        """Make a copy of itself and return it."""
        return Cells(space=space, name=name, formula=self.formula)

    def __hash__(self):
        return hash(id(self))

    def clear(self, *args, **kwargs):
        """Clear all the values."""
        return self._impl.clear_value(*args, **kwargs)

    # ----------------------------------------------------------------------
    # Coercion to single value

    def __bool__(self):
        """True if self != 0. Called for bool(self)."""
        return self._impl.single_value != 0

    def __add__(self, other):
        """self + other"""
        return self._impl.single_value + other

    def __radd__(self, other):
        """other + self"""
        return self.__add__(other)

    def __neg__(self):
        """-self"""
        return -self._impl.single_value

    def __pos__(self):
        """+self"""
        return +self._impl.single_value

    def __sub__(self, other):
        """self - other"""
        return self + -other

    def __rsub__(self, other):
        """other - self"""
        return -self + other

    def __mul__(self, other):
        """self * other"""
        return self._impl.single_value * other

    def __rmul__(self, other):
        """other * self"""
        return self.__mul__(other)

    def __truediv__(self, other):
        """self / other: Should promote to float when necessary."""
        return self._impl.single_value / other

    def __rtruediv__(self, other):
        """other / self"""
        return other / self._impl.single_value

    def __pow__(self, exponent):
        """self ** exponent
        should promote to float or complex when necessary.
        """
        return self._impl.single_value ** exponent

    def __rpow__(self, base):
        """base ** self"""
        return base ** self._impl.single_value

    def __abs__(self):
        """Returns the Real distance from 0. Called for abs(self)."""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # Comparison operations

    def __eq__(self, other):
        """self == other"""
        if self._impl.is_scalar():
            return self._impl.single_value == other
        elif isinstance(other, Cells):
            return self is other
        else:
            raise TypeError

    def __lt__(self, other):
        """self < other"""
        return self._impl.single_value < other

    def __le__(self, other):
        """self <= other"""
        return self.__eq__(other) or self.__lt__(other)

    def __gt__(self, other):
        """self > other"""
        return self._impl.single_value > other

    def __ge__(self, other):
        """self >= other"""
        return self.__eq__(other) or self.__gt__(other)

    # ----------------------------------------------------------------------
    # Conversion to Pandas objects

    def to_series(self, *args):
        """Convert the cells itself into a Pandas Series and return it."""
        return self._impl.to_series(args)

    @property
    def series(self):
        """Alias of ``to_series()``."""
        return self._impl.to_series(())

    def to_frame(self, *args):
        """Convert the cells itself into a Pandas DataFrame and return it.

        if no `args` are passed, the returned DataFrame contains as many
        values as the cells have.

        if A sequence of arguments to the cells is passed as `args`,
        the returned DataFrame contains values only for the specified `args`.

        Args:
            args: A sequence or iterable of arguments to the cells.

        Returns:
            a DataFrame with a column named after the cells,
            with indexes named after the parameters of the cells.
        """

        return self._impl.to_frame(args)

    @property
    def frame(self):
        """Alias of ``to_frame()``."""
        return self._impl.to_frame(())

    # ----------------------------------------------------------------------
    # Properties

    @property
    def formula(self):
        """Property to get, set, delete formula."""
        return self._impl.formula

    @formula.setter
    def formula(self, formula):
        self._impl.set_formula(formula)

    @formula.deleter
    def formula(self):
        self._impl.clear_formula()

    @property
    def parameters(self):
        """A tuple of parameter strings."""
        return self._impl.formula.parameters

    def set_formula(self, func):
        """Set formula from a function.
        Deprecated since version 0.0.5. Use formula property instead.
        """
        self._impl.set_formula(func)

    def clear_formula(self):
        """Clear the formula.
        Deprecated since version 0.0.5. Use formula property instead.
        """
        self._impl.clear_formula()

    @property
    def value(self):
        """Get, set, delete the scalar value.
        The cells must be a scalar cells.
        """
        return self._impl.single_value

    @value.setter
    def value(self, value):
        self._impl.set_value((), value)

    @value.deleter
    def value(self):
        self._impl.clear_value()

    # ----------------------------------------------------------------------
    # Dependency
    def node(self, *args, **kwargs):
        """Return a :class:`CellNode` object for the given arguments."""
        return CellNode(get_node(self._impl, *convert_args(args, kwargs)))

    def preds(self, *args, **kwargs):
        """Return a list of predecessors of a cell.

        This method returns a list of CellNode objects, whose elements are
        predecessors of (i.e. referenced in the formula
        of) the cell specified by the given arguments.
        """
        return self._impl.predecessors(args, kwargs)

    def succs(self, *args, **kwargs):
        """Return a list of successors of a cell.

        This method returns a list of CellNode objects, whose elements are
        successors of (i.e. referencing in their formulas)
        the cell specified by the given arguments.
        """
        return self._impl.successors(args, kwargs)

    # ----------------------------------------------------------------------
    # Override base class methods

    @property
    def _baseattrs(self):
        """A dict of members expressed in literals"""

        result = super()._baseattrs
        result["params"] = ", ".join(self.parameters)
        return result

    @property
    def _is_derived(self):
        return self._impl.is_derived

    @property
    def _is_defined(self):
        return not self._impl.is_derived


class CellsImpl(Derivable, Impl):
    """
    Data container optionally with a formula to set its own values.

    **Creation**

    **Deletion**

    * Values dependent on the cell are deleted clear_all()
    * Values dependent on the derived cells of the cells are deleted
    * Derived cells are deleted _del_derived
    * The cells is deleted _del_self

    **Changing formula**
    clear_all
    _set_formula
    _clear_all_derived
    _set_formula_derived

    **Changing allow_none**

    **Setting Values**
    clear()
    _set

    **Getting Values**

    **Deleting Values**
    clear(params)
    clear_all
    _clear_all_derived()

    Args:
        space: Space to contain the cell.
        name: Cell's name.
        func: Python function or Formula
        data: array-like, dict, pandas.DataSeries or scalar values.
    """

    if_class = Cells

    state_attrs = [
        "_model",
        "space",
        "formula",
        "name",
        "data",
        "_namespace_impl",
        "altfunc",
    ] + Derivable.state_attrs + Impl.state_attrs

    assert len(state_attrs) == len(set(state_attrs))

    def __init__(
        self, *, space, name=None, formula=None, data=None, base=None
    ):
        Impl.__init__(self, system=space.system)
        Derivable.__init__(self)

        self._model = space.model
        self.space = self.parent = space

        if base:
            self.name = base.name
        elif is_valid_name(name):
            self.name = name
        elif formula:
            name = Formula(formula).name
            if is_valid_name(name):
                self.name = name
            else:
                self.name = space.cellsnamer.get_next(space.namespace)
        else:
            self.name = space.cellsnamer.get_next(space.namespace)

        if base:
            self.formula = base.formula
        elif formula is None:
            self.formula = NullFormula(NULL_FORMULA, name=self.name)
        elif isinstance(formula, Formula):
            self.formula = formula.__class__(formula, name=self.name)
        else:
            self.formula = Formula(formula, name=self.name)

        self.data = {}
        if data is None:
            data = {}
        self.data.update(data)

        self._namespace_impl = self.space._namespace_impl
        self.altfunc = BoundFunction(self)

    # ----------------------------------------------------------------------
    # Serialization by pickle

    def __getstate__(self):
        state = {
            key: value
            for key, value in self.__dict__.items()
            if key in self.state_attrs
        }

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    # ----------------------------------------------------------------------
    # Properties

    @property
    def model(self):
        return self._model

    # ----------------------------------------------------------------------
    # repr methods

    def repr_self(self, add_params=True):
        if add_params:
            return "%s(%s)" % (self.name, ", ".join(self.formula.parameters))
        else:
            return self.name

    def repr_parent(self):
        return self.space.repr_parent() + "." + self.space.repr_self()

    def has_cell(self, key):
        return key in self.data

    def is_scalar(self):  # TODO: Move to HasFormula
        return len(self.formula.parameters) == 0

    @property
    def single_value(self):
        if self.is_scalar():
            return self.get_value(())
        else:
            raise ValueError("%s not a scalar" % self.name)

    def inherit(self, **kwargs):

        if "clear_value" in kwargs:
            clear_value = kwargs["clear_value"]
        else:
            clear_value = True

        if self.bases:
            if clear_value:
                self._model.clear_obj(self)
            self.formula = self.bases[0].formula
            self.altfunc.set_update()

    @property
    def module(self):
        return self.formula.module

    @property
    def self_bases(self):
        return []

    @staticmethod
    def _get_members(other):
        return other.cells

    # ----------------------------------------------------------------------
    # Formula operations

    def reload(self, module=None):
        oldsrc = self.formula.source
        newsrc = self.formula._reload(module).source
        if oldsrc != newsrc:
            self._model.clear_obj(self)

    def clear_formula(self):

        if self.is_derived:
            self.is_derived = False

        self.set_formula(NULL_FORMULA)

    def set_formula(self, func):

        if self.parent.is_dynamic():
            raise ValueError("cannot set formula in dynamic space")

        if self.is_derived:
            self.is_derived = False

        self._model.clear_obj(self)
        if isinstance(func, Formula):
            klass = func.__class__
        else:
            klass = Formula
        self.formula = klass(func, name=self.name)
        self.altfunc.set_update()
        self._model.spacegraph.update_subspaces_upward(
            self.parent, from_parent=False, event="cells_set_formula"
        )

    # ----------------------------------------------------------------------
    # Value operations

    def on_eval_formula(self, key):

        value = self.altfunc.get_updated().altfunc(*key)

        if self.has_cell(key):
            # Assignment took place inside the cell.
            if value is not None:
                raise ValueError("Duplicate assignment for %s" % key)
            else:
                value = self.data[key]
                del self.data[key]
                value = self._store_value(key, value, False)
        else:
            value = self._store_value(key, value, False)

        return value

    def get_value(self, args, kwargs=None):

        node = get_node(self, *convert_args(args, kwargs))
        key = node[KEY]

        if self.has_cell(key):
            value = self.data[key]
        else:
            value = self.system.execution.eval_cell(node)

        graph = self._model.cellgraph
        if self.system.callstack:
            graph.add_path([node, self.system.callstack.last()])
        else:
            graph.add_node(node)

        return value

    def find_match(self, args, kwargs):

        node = get_node(self, *convert_args(args, kwargs))
        key = node[KEY]
        keylen = len(key)

        if not self.get_property("allow_none"):
            # raise ValueError('Cells %s cannot return None' % self.name)
            tracemsg = self.system.callstack.tracemessage()
            raise NoneReturnedError(node, tracemsg)

        for match_len in range(keylen, -1, -1):
            for idxs in combinations(range(keylen), match_len):
                masked = [None] * keylen
                for idx in idxs:
                    masked[idx] = key[idx]
                value = self.get_value(masked)
                if value is not None:
                    return ArgsValuePair(tuple(masked), value)

        return ArgsValuePair(None, None)

    def set_value(self, args, value):

        node = get_node(self, *convert_args(args, {}))
        key = node[KEY]

        if self.system.callstack:
            if node == self.system.callstack.last():
                self._store_value(key, value, False)
            else:
                raise KeyError("Assignment in cells other than %s" % key)
        else:
            self._store_value(key, value, True)
            self._model.cellgraph.add_node(node)

    def _store_value(self, key, value, overwrite=False):

        if isinstance(value, Cells):
            if value._impl.is_scalar():
                value = value._impl.single_value

        if not self.has_cell(key) or overwrite:

            if overwrite:
                self.clear_value(*key)

            if value is not None:
                self.data[key] = value
            elif self.get_property("allow_none"):
                self.data[key] = value
            else:
                tracemsg = self.system.callstack.tracemessage()
                raise NoneReturnedError(get_node(self, key, None), tracemsg)

        else:
            raise ValueError("Value already exists for %s" % key)

        return value

    def clear_value(self, *args, **kwargs):
        if args == () and kwargs == {} and not self.is_scalar():
            self.clear_all_values()
        else:
            node = get_node(self, *convert_args(args, kwargs))
            if self.has_cell(node[KEY]):
                self._model.clear_descendants(node)

    def clear_all_values(self):
        for args in list(self.data):
            self.clear_value(*args)

    # ----------------------------------------------------------------------
    # Pandas I/O

    def tuplize_arg_sequence(self, argseq):

        if len(argseq) == 1:
            if isinstance(argseq[0], Sequence) and len(argseq[0]) == 0:
                pass  # Empty sequence
            else:
                argseq = argseq[0]

        for arg in argseq:
            self.get_value(tuplize_key(self, arg, remove_extra=True))

        return tuple(tuplize_key(self, arg) for arg in argseq)

    def to_series(self, args):

        from modelx.io.pandas import cells_to_series

        args = self.tuplize_arg_sequence(args)
        return cells_to_series(self, args)

    def to_frame(self, args):
        from modelx.io.pandas import cells_to_dataframe

        args = self.tuplize_arg_sequence(args)
        return cells_to_dataframe(self, args)

    # ----------------------------------------------------------------------
    # Dependency

    def predecessors(self, args, kwargs):
        node = get_node(self, *convert_args(args, kwargs))
        preds = self._model.cellgraph.predecessors(node)
        return [CellNode(n) for n in preds]

    def successors(self, args, kwargs):
        node = get_node(self, *convert_args(args, kwargs))
        succs = self._model.cellgraph.successors(node)
        return [CellNode(n) for n in succs]


class CellNode:
    """A combination of a cells, its args and its value."""

    def __init__(self, node):
        self._impl = node

    @property
    def cells(self):
        """Return the Cells object"""
        return self._impl[OBJ].interface

    @property
    def args(self):
        """Return a tuple of the cells' arguments."""
        return self._impl[KEY]

    @property
    def has_value(self):
        """Return ``True`` if the cell has a value."""
        return self._impl[OBJ].has_cell(self._impl[KEY])

    @property
    def value(self):
        """Return the value of the cells."""
        if self.has_value:
            return self._impl[OBJ].get_value(self._impl[KEY])
        else:
            raise ValueError("Value not found")

    @property
    def preds(self):
        """A list of nodes that this node refers to."""
        return self.cells.preds(*self.args)

    @property
    def succs(self):
        """A list of nodes that refer to this  node."""
        return self.cells.succs(*self.args)

    @property
    def _baseattrs(self):
        """A dict of members expressed in literals"""

        result = {
            "type": type(self).__name__,
            "obj": self.cells._baseattrs,
            "args": self.args,
            "value": self.value if self.has_value else None,
            "predslen": len(self.preds),
            "succslen": len(self.succs),
            "repr_parent": self.cells._impl.repr_parent(),
            "repr": self.cells._get_repr(),
        }

        return result

    def __repr__(self):

        name = self.cells._get_repr(fullname=True, add_params=False)
        params = self.cells._impl.formula.parameters

        arglist = ", ".join(
            "%s=%s" % (param, arg) for param, arg in zip(params, self.args)
        )

        if self.has_value:
            return name + "(" + arglist + ")" + "=" + str(self.value)
        else:
            return name + "(" + arglist + ")"


def shareable_parameters(cells):
    """Return parameter names if the parameters are shareable among cells.

    Parameters are shareable among multiple cells when all the cells
    have the parameters in the same order if they ever have any.

    For example, if cells are foo(), bar(x), baz(x, y), then
    ('x', 'y') are shareable parameters amounts them, as 'x' and 'y'
    appear in the same order in the parameter list if they ever appear.

    Args:
        cells: An iterator yielding cells.

    Returns:
        None if parameters are not share,
        tuple of shareable parameter names,
        () if cells are all scalars.
    """
    result = []
    for c in cells.values():
        params = c.formula.parameters

        for i in range(min(len(result), len(params))):
            if params[i] != result[i]:
                return None

        for i in range(len(result), len(params)):
            result.append(params[i])

    return result
