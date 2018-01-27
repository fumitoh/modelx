# Copyright (c) 2017 Fumito Hamamura <fumito.ham@gmail.com>

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

from types import FunctionType
from textwrap import dedent
from collections import Sequence, namedtuple
from collections.abc import (
    Container,
    Callable,
    Sized)
from itertools import combinations

from modelx.core.base import (
    ObjectArgs,
    Impl,
    Interface)
from modelx.core.formula import (
    Formula,
    create_closure,
    NULL_FORMULA)
from modelx.core.util import is_valid_name
from modelx.core.errors import NoneReturnedError


def cells_to_argvals(args, kwargs):

    if isinstance(args, Sequence):

        result = []
        for arg in args:
            if isinstance(arg, Cells):
                if arg._impl.is_scalar():
                    result.append(arg._impl.single_value)
                else:
                    raise ValueError('Cells cannot be an argument')
            else:
                result.append(arg)

        args = result

    elif isinstance(args, Cells):
        args = args._impl.single_value

    if kwargs is not None:
        for key, arg in kwargs.items():
            if isinstance(arg, Cells):
                if arg._impl.is_scalar():
                    kwargs[key] = arg._impl.single_value
                else:
                    raise ValueError('Cells cannot be an argument')

    return args, kwargs


class CellArgs(ObjectArgs):

    state_attrs = ['cells'] + ObjectArgs.state_attrs

    def __init__(self, cells, args, kwargs=None):

        args, kwargs = cells_to_argvals(args, kwargs)
        ObjectArgs.__init__(self, cells, args, kwargs)
        self.cells = self.obj_

    def eval_formula(self):

        func = self.cells.formula.func
        codeobj = func.__code__
        name = self.cells.name   # func.__name__
        namespace = self.cells.space.namespace

        closure = func.__closure__  # None normally.
        if closure is not None:     # pytest fails without this.
            closure = create_closure(self.cells.interface)

        altfunc = FunctionType(codeobj, namespace,
                               name=name, closure=closure)

        return altfunc(**self.arguments)


class CellsMaker:

    def __init__(self, *, space, name):
        self.space = space  # SpaceImpl
        self.name = name

    def __call__(self, func):
        return self.space.new_cells(func=func, name=self.name).interface

ArgsValuePair = namedtuple('ArgsValuePair', ['args', 'value'])

class CellsImpl(Impl):
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

    **Changing can_have_none**

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

    def __init__(self, *, space, name=None, func=None, data=None):

        Impl.__init__(self, Cells)

        self.system = space.system
        self.model = space.model
        self.space = self.parent = space
        if func is None:
            self.formula = NULL_FORMULA
        else:
            self.formula = Formula(func)

        if is_valid_name(name):
            self.name = name
        elif is_valid_name(self.formula.name):
            self.name = self.formula.name
        else:
            self.name = space.cellsnamer.get_next(space.namespace)

        self.data = {}
        if data is None:
            data = {}
        self.data.update(data)

    # ----------------------------------------------------------------------
    # Serialization by pickle

    state_attrs = ['model',
                   'space',
                   'formula',
                   'name',
                   'data'] + Impl.state_attrs

    def __getstate__(self):
        state = {key: value for key, value in self.__dict__.items()
                 if key in self.state_attrs}

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def restore_state(self, system):
        """Called after unpickling to restore some attributes manually."""
        self.system = system

    # ----------------------------------------------------------------------
    # Properties

    def __repr__(self):
        return '<CellsImpl: %s>' % self.name

    def get_fullname(self, omit_model=False):
        return self.space.get_fullname(omit_model) + '.' + self.name

    @property
    def fullname(self):
        return self.space.fullname + '.' + self.name

    @property
    def _repr_self(self):
        return "%s(%s)" % (self.name, ', '.join(self.parameters.keys()))

    @property
    def _repr_parent(self):
        return self.space._repr_parent + '.' + self.space._repr_self

    @property
    def signature(self):
        return self.formula.signature

    @property
    def parameters(self):
        return self.signature.parameters

    @property
    def repr_(self):

        format_ = dedent("""\
        name: %s
        space: %s
        number of cells: %s""")

        return format_ % (self.name,
                          self.space.name,
                          len(self.data))

    def has_cell(self, args):
        return args in self.data

    def is_scalar(self):
        return len(self.parameters) == 0

    @property
    def single_value(self):
        if self.is_scalar():
            return self.get_value(())
        else:
            raise ValueError("%s not a scalar" % self.name)

    @property
    def is_derived(self):
        return self.name in self.space.derived_cells

    # ----------------------------------------------------------------------
    # Formula operations

    def clear_formula(self):
        self.set_formula(NULL_FORMULA)

    def set_formula(self, func):
        if not self.is_derived:
            formula = Formula(func)
            self.model.clear_obj(self)
            self.formula = formula
            self.space.self_cells_set_update()
        else:
            raise NotImplementedError('Cannot change derived cells formula')

    # ----------------------------------------------------------------------
    # Value operations

    def get_value(self, args, kwargs=None):

        ptr = CellArgs(self, args, kwargs)
        args = ptr.argvalues

        if self.has_cell(args):
            value = self.data[args]

        else:
            self.system.callstack.append(ptr)
            try:
                value = ptr.eval_formula()

                if self.has_cell(args):
                    # Assignment took place inside the cell.
                    if value is not None:
                        raise ValueError("Duplicate assignment for %s"
                                         % args)
                    else:
                        value = self.data[args]
                        del self.data[args]
                        value = self._store_value(ptr, value, False)
                else:
                    value = self._store_value(ptr, value, False)

            finally:
                self.system.callstack.pop()

        graph = self.model.cellgraph
        if not self.system.callstack.is_empty():
            graph.add_path([ptr, self.system.callstack.last()])
        else:
            graph.add_node(ptr)

        return value

    def find_match(self, args, kwargs):

        ptr = CellArgs(self, args, kwargs)
        args = ptr.argvalues
        args_len = len(args)

        if not self.get_property('can_have_none'):
            # raise ValueError('Cells %s cannot return None' % self.name)
            tracemsg = self.system.callstack.tracemessage()
            raise NoneReturnedError(ptr, tracemsg)

        for match_len in range(args_len, -1, -1):
            for idxs in combinations(range(args_len), match_len):
                masked = [None] * args_len
                for idx in idxs:
                    masked[idx] = args[idx]
                value = self.get_value(masked)
                if value is not None:
                    return ArgsValuePair(tuple(masked), value)

        return ArgsValuePair(None, None)

    def set_value(self, key, value):

        ptr = CellArgs(self, key)

        if self.system.callstack.is_empty():
            self._store_value(ptr, value, True)
            self.model.cellgraph.add_node(ptr)
        else:
            if ptr == self.system.callstack.last():
                self._store_value(ptr, value, False)
            else:
                raise KeyError("Assignment in cells other than %s" %
                               ptr.argvalues)

    def _store_value(self, ptr, value, overwrite=False):

        key = ptr.argvalues

        if isinstance(value, Cells):
            if value._impl.is_scalar():
                value = value._impl.single_value

        if not ptr.cells.has_cell(key) or overwrite:

            if overwrite:
                self.clear_value(*key)

            if value is not None:
                self.data[key] = value
            elif self.get_property('can_have_none'):
                self.data[key] = value
            else:
                tracemsg = self.system.callstack.tracemessage()
                raise NoneReturnedError(ptr, tracemsg)

        else:
            raise ValueError("Value already exists for %s" %
                             ptr.arguments)

        return value

    def clear_value(self, *args, **kwargs):
        if args == () and kwargs == {} and not self.is_scalar():
            self.clear_all_values()
        else:
            ptr = CellArgs(self, args, kwargs)
            if self.has_cell(ptr.argvalues):
                self.model.clear_descendants(ptr)

    def clear_all_values(self):
        for args in list(self.data):
            self.clear_value(*args)

    # ----------------------------------------------------------------------
    # Pandas I/O

    def to_series(self):
        from modelx.io.pandas import cells_to_series

        return cells_to_series(self)

    def to_frame(self):

        from modelx.io.pandas import cells_to_dataframe

        return cells_to_dataframe(self)

    # ----------------------------------------------------------------------
    # Dependency

    def predecessors(self, args, kwargs):
        node = CellArgs(self, args, kwargs)
        preds = self.model.cellgraph.predecessors(node)
        return [CellNode(n) for n in preds]

    def successors(self, args, kwargs):
        node = CellArgs(self, args, kwargs)
        succs = self.model.cellgraph.successors(node)
        return [CellNode(n) for n in succs]


class CellNode:
    """A combination of a cells, its args and its value."""

    def __init__(self, cellargs):
        self._impl = cellargs

    @property
    def cells(self):
        """Return the Cells object"""
        return self._impl.cells.interface

    @property
    def args(self):
        """Return a tuple of the cells' arguments."""
        return self._impl.argvalues

    @property
    def has_value(self):
        """Return ``True`` if the cell has a value."""
        return self._impl.cells.has_cell(self._impl.argvalues)

    @property
    def value(self):
        """Return the value of the cells."""
        if self.has_value:
            return self._impl.cells.get_value(self._impl.argvalues)
        else:
            raise ValueError('Value not found')

    def __repr__(self):
        if self.has_value:
            return self._impl.__repr__() + '=' + str(self.value)
        else:
            return self._impl.__repr__()


class Cells(Interface, Container, Callable, Sized):
    """Data container with a formula to calculate its own values.

    Cells are created by ``new_cells`` method or its variant methods of
    the containing space, or by function definitions with ``defcells``
    decorator.
    """
    # __slots__ = ('_impl',)

    def __contains__(self, args):
        return self._impl.has_cell(args)

    def __getitem__(self, key):
        return self._impl.get_value(key)

    def __call__(self, *args, **kwargs):
        return self._impl.get_value(args, kwargs)

    def match(self, *args, **kwargs):
        """Returns the best matching args and their value.

        If the cells returns None for the given arguments,
        continue to get a value by passing arguments
        masking the given arguments with ``None``s.
        The search of non-None value starts from the given arguments
        to the all ``None`` arguments in the lexicographical order.
        The masked arguments that returns non-None value
        first is returned with the value.
        """
        return self._impl.find_match(args, kwargs)

    def __len__(self):
        return len(self._impl.data)

    def __setitem__(self, key, value):
        """Set value of a particular cell"""
        self._impl.set_value(key, value)

    def __iter__(self):

        def inner():
            keys = sorted(tuple(arg for arg in key)
                          for key in self._impl.data.keys())

            for args in keys:
                yield args

        return inner()

    def copy(self, space=None, name=None):
        """Make a copy of itself and return it."""
        return Cells(space=space, name=name, func=self.formula)

    def __hash__(self):
        return hash(id(self))

    def clear(self, *args, **kwargs):
        """Clear all the values."""
        return self._impl.clear_value(*args, **kwargs)

    # ----------------------------------------------------------------------
    # Coercion to single value

    def __bool__(self):
        """True if self != 0. Called for bool(self)."""
        return self.get_value() != 0

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

    def to_series(self):
        """Convert the cells itself into a Pandas Series and return it."""
        return self._impl.to_series()

    @property
    def series(self):
        """Alias of ``to_series()``."""
        return self._impl.to_series()

    def to_frame(self):
        """Convert the cells itself into a Pandas DataFrame and return it."""
        return self._impl.to_frame()

    @property
    def frame(self):
        """Alias of ``to_frame()``."""
        return self._impl.to_frame()

    # ----------------------------------------------------------------------
    # Properties

    @property
    def formula(self):
        """Property to get, set, delete formula."""
        return self._impl.formula.source

    @formula.setter
    def formula(self, formula):
        self._impl.set_formula(formula)

    @formula.deleter
    def formula(self):
        self._impl.clear_formula()

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
