import sys
import importlib
from collections import Sequence
from textwrap import dedent
from types import (MappingProxyType,
                   FunctionType,
                   ModuleType)

from modelx.core.base import (ObjectPointer,
                              get_impls,
                              get_interfaces,
                              Impl,
                              Interface,
                              LazyEvalDict,
                              LazyEvalChainMap)
from modelx.core.formula import Formula, create_closure
from modelx.core.cells import (Cells,
                               CellsMaker,
                               CellsImpl)
from modelx.core.util import AutoNamer, is_valid_name, get_module


class SpacePointer(ObjectPointer):
    """Combination of space and arguments to locate its subspace."""

    def __init__(self, space, args, kwargs=None):

        ObjectPointer.__init__(self, space, args, kwargs)
        self.space = self.obj_

    def eval_formula(self):

        func = self.space.factory.func
        codeobj = func.__code__
        name = self.space.name
        namespace = self.space.namespace

        closure = func.__closure__  # None normally.
        if closure is not None:     # pytest fails without this.
            closure = create_closure(self.space.interface)

        altfunc = FunctionType(codeobj, namespace,
                               name=name, closure=closure)

        return altfunc(**self.arguments)


class SpaceFactory(Formula):
    def __init__(self, func):
        Formula.__init__(self, func)


class SpaceContainerImpl(Impl):
    """Base class of Model and Space that contain spaces.

    A space in
    """
    state_attrs = ['_spaces',
                   'param_spaces',
                   'spacenamer',
                   'factory'] + Impl.state_attrs

    def __init__(self, system, if_class, factory):

        Impl.__init__(self, if_class)

        self.system = system
        self.param_spaces = {}
        self.spacenamer = AutoNamer('Space')

        if factory is None:
            self.factory = None
        else:
            self.factory = SpaceFactory(factory)

        self._spaces = {}

    def __getstate__(self):

        state = {key: value for key, value in self.__dict__.items()
                 if key in self.state_attrs}

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def restore_state(self, system):
        """Called after unpickling to restore some attributes manually."""

        self.system = system

        for space in self._spaces.values():
            space.restore_state(system)

    @property
    def spaces(self):
        return self._spaces

    def has_space(self, name):

        if name in self.spaces:
            return True
        else:
            return False

    def create_space(self, *, name=None, bases=None, factory=None,
                     arguments=None):
        """Create a child space.

        Args:
            name (str): Name of the space. If omitted, the space is
                created automatically.
            bases: If specified, the new space becomes a derived space of
                the `base` space.
            factory: Function whose parameters used to set space parameters.
            arguments: ordered dict of space parameter names to their values.
            base_self: True if subspaces inherit self by default.

        """
        if name is None:
            name = self.spacenamer.get_next(self.spaces)

        if self.has_space(name):
            raise ValueError("Name already assigned.")

        if not is_valid_name(name):
            raise ValueError("Invalid name '%s'." % name)

        space = SpaceImpl(parent=self, name=name, bases=bases,
                          factory=factory, arguments=arguments)

        self.spaces[name] = space

        return space

    def create_space_from_module(self, module_, name=None, recursive=False):

        module_ = get_module(module_)

        if name is None:
            name = module_.__name__.split('.')[-1]  # xxx.yyy.zzz -> zzz

        space = self.create_space(name=name)
        space.create_cells_from_module(module_)

        if recursive and hasattr(module_, '_spaces'):
            for name in module_._spaces:
                submodule = module_.__name__ + '.' + name
                space.create_space_from_module(module_=submodule,
                                               recursive=True)

        return space

    def create_space_from_excel(self, book, range_, sheet=None,
                                name=None,
                                names_row=None, param_cols=None,
                                space_param_order=None,
                                cells_param_order=None,
                                transpose=False,
                                names_col=None, param_rows=None):

        import modelx.io.excel as xl

        param_order = space_param_order + cells_param_order

        cellstable = xl.CellsTable(book, range_, sheet,
                                   names_row, param_cols,
                                   param_order,
                                   transpose,
                                   names_col, param_rows)

        space_params = cellstable.param_names[:len(space_param_order)]
        cells_params = cellstable.param_names[len(space_param_order):]

        if space_params:
            space_sig = "=None, ".join(space_params) + "=None"
        else:
            space_sig = ""

        if cells_params:
            cells_sig = "=None, ".join(cells_params) + "=None"
        else:
            cells_sig = ""

        param_func = "def _param_func(" + space_sig + "): pass"
        blank_func = "def _blank_func(" + cells_sig + "): pass"

        space = self.create_space(name=name, factory=param_func)

        for cellsdata in cellstable.items():
            for args, value in cellsdata.items():
                space_args = args[:len(space_params)]
                cells_args = args[len(space_params):]

                subspace = space.get_space(space_args)

                if cellsdata.name in subspace.cells:
                    cells = subspace.cells[cellsdata.name]
                else:
                    cells = subspace.create_cells(name=cellsdata.name,
                                                  func=blank_func)
                cells.set_value(cells_args, value)

        return space



    def get_space(self, args, kwargs=None):

        ptr = SpacePointer(self, args, kwargs)

        if ptr.argvalues in self.param_spaces:
            return self.param_spaces[ptr.argvalues]

        else:
            last_self = self.system.self
            self.system.self = self

            try:
                space_args = ptr.eval_formula()

            finally:
                self.system.self = last_self

            if space_args is None:
                space_args = {}
            else:
                space_args = get_impls(space_args)

            space_args['arguments'] = ptr.arguments
            space = self.create_space(**space_args)
            self.param_spaces[ptr.argvalues] = space
            return space

    def set_factory(self, factory):
        if self.factory is None:
            self.factory = SpaceFactory(factory)
        else:
            raise ValueError("Factory already assigned.")


class SpaceContainer(Interface):

    def create_space(self, name=None, bases=None, factory=None):
        """Create a space in the model.

        Args:
            name (str): Name of the space. If omitted, the space is
                created automatically.
            bases: If specified, the new space becomes a derived space of
                the `base` space.
            factory: Function whose parameters used to set space parameters.

        """
        space = self._impl.model.currentspace \
            = self._impl.create_space(name=name, bases=get_impls(bases),
                                      factory=factory)

        return space.interface

    def create_space_from_module(self, module_, name=None, recursive=False):

        space = self._impl.model.currentspace \
            = self._impl.create_space_from_module(module_, name=name,
                                                  recursive=recursive)

        return get_interfaces(space)

    def create_space_from_excel(self, book, range_, sheet=None,
                                name=None,
                                names_row=None, param_cols=None,
                                space_param_order=None,
                                cells_param_order=None,
                                transpose=False,
                                names_col=None, param_rows=None):

        space = self._impl.create_space_from_excel(
            book, range_, sheet, name,
            names_row, param_cols,
            space_param_order,
            cells_param_order,
            transpose,
            names_col, param_rows)

        return get_interfaces(space)

    @property
    def spaces(self):
        return MappingProxyType(get_interfaces(self._impl.spaces))

class InheritedMembers(LazyEvalDict):

    def __init__(self, space, data={}, observers=[], attr=''):

        LazyEvalDict.__init__(self, data, observers)
        self.space = space
        self.base_data = {}

        self.attr = attr

        if attr == 'cells':
            self._update_data = self._update_data_cells
        elif attr == 'spaces':
            self._update_data = self._update_data_spaces
        elif attr == 'names':
            self._update_data = self._update_data_names
        else:
            raise ValueError

        self.update_data()

    def _update_base(self, attr):

        self.base_data.clear()
        bases = list(reversed(self.space.mro))

        for base, base_next in zip(bases, bases[1:]):

            self.base_data.update(getattr(base, attr))
            keys = self.base_data.keys() - base_next.self_members.keys()

            for name in self.base_data:
                if name not in keys:
                    del self.base_data[name]

    def __repr__(self):
        return '<' + self.space.name + ':' + 'inherited_' + self.attr + '>'

    def _update_data_cells(self):

        self._update_base('self_cells')
        keys = self.data.keys() - self.base_data.keys()

        for key in keys:
            del self.data[key]

        for key, base_cell in self.base_data.items():

            if key in self.data:
                if self.data[key].formula is base_cell.formula:
                    return
                else:
                    del self.data[key]

            cell = CellsImpl(space=self.space, name=base_cell.name,
                             func=base_cell.formula)

            self.data[key] = cell

    def _update_data_spaces(self):

        self._update_base('self_spaces')
        self.data.clear()

        for base_space in self.base_data.values():

            space = SpaceImpl(parent=self.space, name=base_space.name,
                              bases=base_space.bases,
                              factory=base_space.factory)

            self.data[space.name] = space

    def _update_data_names(self):
        self._update_base('self_names')
        self.data.clear()
        self.data.update(self.base_data)


class NameSpaceDict(LazyEvalDict):

    def __init__(self, space, data=None, observers=None):

        if data is None:
            data = {}

        if observers is None:
            observers = []

        LazyEvalDict.__init__(self, data, observers)
        self.space = space

    def _update_data(self):
        self.space._namespace_impl.update_data()
        self.data.clear()
        self.data.update(get_interfaces(self.space.cells))
        self.data.update(get_interfaces(self.space.spaces))
        self.data.update(self.space.names)

    def __repr__(self):
        return '<' + self.space.name + ':namespace>'


class SelfMembers(LazyEvalDict):

    def __init__(self, space, attr, data=None, observers=None):

        if data is None:
            data = {}

        if observers is None:
            observers = []

        LazyEvalDict.__init__(self, data, observers)
        self.space = space
        self.attr = attr

    def __repr__(self):
        return "<" + self.space.name + "." + self.attr + ">"


class SpaceImpl(SpaceContainerImpl):
    """The implementation of Space class.

    The rationales for splitting implementation from its interface are twofold,
    one is to hide from users attributes used only within the package,
    and the other is to free referring objects from getting affected by
    special methods that are meant for changing the behaviour of operations
    for users.

    namespace

        cells
            inherited_cells
            self_cells

        spaces
            dynamic_spaces
            static_spaces
                inherited_spaces
                self_spaces

        names
            inherited_names
            self_names
            builtin_names

        arguments
        cells_parameters (Not yet implemented)

    inherited_members (ChainMap)
        inherited_cells
        inherited_spaces
        inherited_names

    self_members
        self_cells
        self_spaces
        self_names

        # Operations
        remove_inherited
        revert_inherited

    Args:
        parent: SpaceImpl or ModelImpl to contain this.
        name: Name of the space.
        params: Callable or str or sequence.
        bases: SpaceImpl or a list of SpaceImpl.
        
    Attributes:
        space (Space): The Space associated with this implementation.
        parent: the space or model containing this space.
        name:   name of this space.
        signature: Function signature for child spaces. None if not specified.
        
        cells (dict):  Dict to contained cells
        _self_cells (dict): cells defined in this space.
        base_cells (dict): cells in base spaces to inherit in this space.
        _inherited_cells (dict): cells inherited from base cells.
        _self_names
        _inherited_names
        
        cellsnamer (AutoNamer): AutoNamer to auto-name unnamed child cells.
        
        mro (list): MRO of base spaces.
                
        _namespace (dict)
    """

    def __init__(self, parent, name, bases, factory, arguments=None):

        SpaceContainerImpl.__init__(self, parent.system, if_class=Space,
                                    factory=factory)

        self.name = name
        self.parent = parent
        self.cellsnamer = AutoNamer('Cells')

        if arguments is None:
            self._arguments = LazyEvalDict()
        else:
            self._arguments = LazyEvalDict(arguments)

        # Set up direct base spaces and mro
        if bases is None:
            bases = []
        elif isinstance(bases, SpaceImpl):
            bases = [bases]
        elif isinstance(bases, Sequence) \
                and all(isinstance(base, SpaceImpl) for base in bases):
            bases = list(bases)
        else:
            raise TypeError('bases must be space(s).')

        self._direct_bases = bases
        self._mro = []
        self._update_mro()
        self._init_members()

    def _init_members(self):

        self._inherited_cells = InheritedMembers(self, attr='cells')
        self._inherited_spaces = InheritedMembers(self, attr='spaces')
        self._inherited_names = InheritedMembers(self, attr='names')

        inherited = [self._inherited_cells,
                     self._inherited_spaces,
                     self._inherited_names]

        base_self_members = [base._self_members for base in self.mro[1:]]
        self._observed_bases = LazyEvalChainMap(base_self_members,
                                                observers=inherited)

        self._self_cells = SelfMembers(self, 'cells')
        self._self_spaces = SelfMembers(self, 'spaces')
        self._self_names = SelfMembers(self, 'names')
        self._dynamic_spaces = LazyEvalDict()

        self_members = [self._self_cells,
                        self._self_spaces,
                        self._self_names,
                        self._dynamic_spaces]

        self._self_members = LazyEvalChainMap(self_members, inherited)
        self._self_members._repr = '<' + self.name + '.self_members>'

        self._cells = LazyEvalChainMap([self._self_cells,
                                        self._inherited_cells])
        self._cells._repr = '<' + self.name + '.cells>'

        self._static_spaces = LazyEvalChainMap([self._self_spaces,
                                                self._inherited_spaces])

        self._static_spaces._repr = '<' + self.name + '.static_spaces>'

        self._spaces = LazyEvalChainMap([self._static_spaces,
                                         self._dynamic_spaces])

        self._spaces._repr = '<' + self.name + '.spaces>'

        self._builtin_names = LazyEvalDict(
            data={
                  'get_self': self.get_self_interface})

        self._names = LazyEvalChainMap([self._builtin_names,
                                        self._arguments,
                                        self._self_names,
                                        self._inherited_names])

        self._names._repr = '<' + self.name + '.names>'
        self._namespace_impl = LazyEvalChainMap([self._cells,
                                                 self._spaces,
                                                 self._names])

        self._namespace_impl._repr = '<' + self.name + '.namespace_impl>'
        self._namespace = NameSpaceDict(self)
        self._namespace_impl.append_observer(self._namespace)
        self._namespace_cache = dict(self._namespace)

    # ----------------------------------------------------------------------
    # Serialization by pickle

    state_attrs = [
        '_mro',
        '_names',
        '_namespace_cache',
        '_namespace_impl',
        '_arguments',
        '_namespace',
        '_dynamic_spaces',
        '_builtin_names',
        '_inherited_spaces',
        '_inherited_names',
        '_direct_bases',
        '_static_spaces',
        '_self_spaces',
        '_self_members',
        '_cells',
        '_self_cells',
        '_inherited_cells',
        '_observed_bases',
        '_self_names',
        'interface',
        'cellsnamer',
        'name',
        'parent'] + SpaceContainerImpl.state_attrs

    def __getstate__(self):
        state = {key: value for key, value in self.__dict__.items()
                 if key in self.state_attrs}

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def restore_state(self, system):
        """Called after unpickling to restore some attributes manually."""

        self.system = system

        for space in self._spaces.values():
            space.restore_state(system)

        for cells in self._cells.values():
            cells.restore_state(system)

    def __repr__(self):
        return '<SpaceImpl: ' + self.name + '>'

    def get_self_interface(self):
        return self.interface

    def get_object(self, name):
        """Retrieve an object by a dotted name relative to the space."""

        parts = name.split('.')
        child = parts.pop(0)

        if parts:
            return self.spaces[child].get_object('.'.join(parts))
        else:
            return self._namespace_impl[child]

    def debug_print(self):

        format_ = dedent("""\
        namespace(%s) := %r
        namespace_impl(%s) := %r

            cells := %r
                inherited_cells := %r
                self_cells := %r.

            spaces := %r
                dynamic_spaces := %r
                static_spaces := %r
                    inherited_spaces := %r
                    self_spaces := %r
    
            names := %r
                inherited_names := %r
                self_names := %r
                builtin_names""")

        print(format_ % (
            self._namespace.needs_update, self._namespace.data,
            self._namespace_impl.needs_update, dict(self._namespace_impl),
            dict(self._cells),
            dict(self._inherited_cells),
            dict(self._self_cells),
            dict(self._spaces),
            dict(self._dynamic_spaces),
            dict(self._static_spaces),
            self._inherited_spaces.data,
            self._self_spaces.data,
            dict(self._names),
            self._inherited_names.data,
            self._self_names.data))

    @property
    def repr_(self):

        format_ = dedent("""\
        name: %s
        cells: %s
        spaces: %s
        names: %s
        """)

        return format_ % (
            self.name,
            list(self.cells.keys()),
            list(self.spaces.keys()),
            list(self.names.keys())
        )

    # ----------------------------------------------------------------------
    # Components and namespace

    @property
    def self_cells(self):
        return self._self_cells.update_data()

    @property
    def self_spaces(self):
        return self._self_spaces.update_data()

    @property
    def self_names(self):
        return self._self_names.update_data()

    @property
    def self_members(self):
        return self._self_members.update_data()

    @property
    def cells(self):
        return self._cells.update_data()

    @property
    def spaces(self):
        return self._spaces.update_data()

    @property
    def names(self):
        return self._names.update_data()

    @property
    def namespace(self):
        if self._namespace.needs_update:
            self._namespace_cache = dict(self._namespace.update_data())

        return self._namespace_cache

    # ----------------------------------------------------------------------
    # Inheritance

    @property
    def bases(self):
        return self._direct_bases

    @property
    def mro(self):
        return self._mro

    def _update_mro(self):
        """Calculate the Method Resolution Order of bases using the C3 algorithm.

        Code modified from 
        http://code.activestate.com/recipes/577748-calculate-the-mro-of-a-class/

        Args:
            bases: sequence of direct base spaces.

        """
        seqs = [base.mro.copy() for base
                in self._direct_bases] + [self._direct_bases]
        res = []

        while True:
            non_empty = list(filter(None, seqs))

            if not non_empty:
                # Nothing left to process, we're done.
                self._mro = [self] + res
                return

            for seq in non_empty:  # Find merge candidates among seq heads.
                candidate = seq[0]
                not_head = [s for s in non_empty if candidate in s[1:]]
                if not_head:
                    # Reject the candidate.
                    candidate = None
                else:
                    break

            if not candidate:
                raise TypeError(
                    "inconsistent hierarchy, no C3 MRO is possible")

            res.append(candidate)

            for seq in non_empty:
                # Remove candidate.
                if seq[0] == candidate:
                    del seq[0]

    # ----------------------------------------------------------------------

    @property
    def model(self):
        return self.parent.model

    def set_cells(self, name, cells):
        self._self_cells[name] = cells
        self._self_cells.set_update(skip_self=True)

    def set_space(self, name, space):
        pass

    def set_name(self, name, value):

        if not is_valid_name(name):
            raise ValueError

        if name in self.namespace:
            if name in self.names:
                self.names[name] = value
                self.names.set_update(skip_self=False)

            elif name in self.cells:
                if self.cells[name].has_single_value():
                    self.cells[name].set_value((), value)

            else:
                raise ValueError

        else:
            self._self_names[name] = value
            self._self_names.set_update(skip_self=True)

    def remove_cells(self, name):

        if name in self._self_cells:
            self._self_cells[name].parent = None
            del self._self_cells[name]

        for base in self._direct_bases:
            if name in base.cells:
                base_cells = base.cells[name]
                self._inherited_cells[name] = \
                    self.create_cells(name=name, func=base_cells.formula)
            break

    def remove_inherited(self, name):

        if name in self.namespace:

            if name in self._inherited_cells:
                self._inherited_cells[name].parent = None
                del self._inherited_cells[name]

            elif name in self._inherited_spaces:
                self._inherited_spaces[name].parent = None
                del self._inherited_spaces[name]

            elif name in self._inherited_names:
                del self._inherited_names[name]

            else:
                raise RuntimeError("Name already assigned.")

            return True

        else:
            return False

    def revert_inherited(self, name):

        if name in self.base_namespace:
            pass

    def has_bases(self):
        if len(self._mro) > 1:
            return True
        else:
            return False

    def create_cells(self, name=None, func=None):
        cells = CellsImpl(space=self, name=name, func=func)
        self.set_cells(cells.name, cells)
        return cells

    def create_cells_from_module(self, module_):
        # Outside formulas only

        module_ = get_module(module_)
        newcells = {}

        for name in dir(module_):
            func = getattr(module_, name)
            if isinstance(func, FunctionType):
                # Choose only the functions defined in the module.
                if func.__module__ == module_.__name__:
                    newcells[name] = \
                        self.create_cells(name, func)

        return newcells

    def create_cells_from_excel(self, book, range_, sheet=None,
                                names_row=None, param_cols=None,
                                param_order=None,
                                transpose=False,
                                names_col=None, param_rows=None):
        """Create multiple cells from an Excel range.

        Args:
            book (str): Path to an Excel file.
            range_ (str): Range expression, such as "A1", "$G4:$K10",
                or named range "NamedRange1".
            sheet (str): Sheet name (case ignored).
            names_row: Cells names in a sequence, or an integer number, or
              a string expression indicating row (or column depending on
              ```orientation```) to read cells names from.
            param_cols: a sequence of them
                indicating parameter columns (or rows depending on ```
                orientation```)
            param_order: a sequence of integers representing
                the order of params and extra_params.
            transpose: in which direction 'vertical' or 'horizontal'
            names_col: a string or a list of names of the extra params.
            param_rows: integer or string expression, or a sequence of them
                indicating row (or column) to be interpreted as parameters.
        """
        import modelx.io.excel as xl

        cellstable = xl.CellsTable(book, range_, sheet,
                                   names_row, param_cols, param_order,
                                   transpose, names_col, param_rows)

        if cellstable.param_names:
            sig = "=None, ".join(cellstable.param_names) + "=None"
        else:
            sig = ""

        blank_func = "def _blank_func(" + sig + "): pass"

        for cellsdata in cellstable.items():
            cells = self.create_cells(name=cellsdata.name, func=blank_func)
            for args, value in cellsdata.items():
                cells.set_value(args, value)

    @property
    def signature(self):
        return self.factory.signature

    def get_fullname(self, omit_model=False):

        fullname = self.name
        parent = self.parent
        while True:
            fullname = parent.name + '.' + fullname
            if hasattr(parent, 'parent'):
                parent = parent.parent
            else:
                if omit_model:
                    separated = fullname.split('.')
                    separated.pop(0)
                    fullname = '.'.join(separated)

                return fullname

    def to_dataframe(self):

        from modelx.io.pandas import space_to_dataframe

        return space_to_dataframe(self)


class Space(SpaceContainer):
    """Container for cells and other objects referred in formulas.

    Args:
        model: Model to contain the space.
        name (str): Name of the space. 
        params: Function with the signature to specify 
            space parameters. 
        bases: space or sequence of spaces.
    
    """
    # __slots__ = ('_impl',)

    @property
    def name(self):
        return self._impl.name

    # def __repr__(self):
    #     return self._impl.repr_

    # ----------------------------------------------------------------------
    # Manipulating cells

    def create_cells(self, name=None, func=None):
        # Outside formulas only
        return self._impl.create_cells(name, func).interface

    @property
    def cells(self):
        return MappingProxyType(get_interfaces(self._impl.cells))
        # return get_interfaces(self._impl.cells)

    def create_cells_from_module(self, module_):
        # Outside formulas only

        newcells = self._impl.create_cells_from_module(module_)
        return get_interfaces(newcells)

    def create_cells_from_excel(self, book, range_, sheet=None,
                                names_row=None, param_cols=None,
                                param_order=None,
                                transpose=False,
                                names_col=None, param_rows=None):
        """Create multiple cells from an Excel range.

        Args:
            book (str): Path to an Excel file.
            range_ (str): Range expression, such as "A1", "$G4:$K10",
                or named range "NamedRange1".
            sheet (str): Sheet name (case ignored).
            names_row: Cells names in a sequence, or an integer number, or
              a string expression indicating row (or column depending on
              ```orientation```) to read cells names from.
            param_cols: a sequence of them
                indicating parameter columns (or rows depending on ```
                orientation```)
            param_order: a sequence of integers representing
                the order of params and extra_params.
            transpose: in which direction 'vertical' or 'horizontal'
            names_col: a string or a list of names of the extra params.
            param_rows: integer or string expression, or a sequence of them
                indicating row (or column) to be interpreted as parameters.
        """
        return self._impl.create_cells_from_excel(
            book, range_, sheet, names_row, param_cols,
            param_order, transpose,
            names_col, param_rows)

    # ----------------------------------------------------------------------
    # Checking containing subspaces and cells

    def __contains__(self, item):
        """Check if item is in the space.

        item can be wither a cells or space.

        Args:
            item: a cells or space to check.

        Returns:
            True if item is a direct child of the space, False otherwise.
        """

        if isinstance(item, Cells):
            return item in self._cells.values()

        elif isinstance(item, Space):
            return item in self._subspaces.values()

    # ----------------------------------------------------------------------
    # Getting and setting attributes

    def __getattr__(self, name):
        return self._impl.namespace[name]

    def __setattr__(self, name, value):
        self._impl.set_name(name, value)

    # ----------------------------------------------------------------------
    # Manipulating subspaces

    def has_params(self):
        # Outside formulas only
        return bool(self.signature)

    def __getitem__(self, args):
        return self._impl.get_space(args).interface

    def __call__(self, *args, **kwargs):
        return self._impl.get_space(args, kwargs).interface

    def set_factory(self, factory):
        self._impl.set_factory(factory)

    # ----------------------------------------------------------------------
    # Conversion to Pandas objects

    def to_dataframe(self):
        return self._impl.to_dataframe()

    @property
    def frame(self):
        return self._impl.to_dataframe()


