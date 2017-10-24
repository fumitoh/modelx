# Copyright (c) 2017 Fumito Hamamura <fumito.ham@gmail.com>

# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.

from collections import Sequence
from textwrap import dedent
from types import (MappingProxyType,
                   FunctionType)

from modelx.core.base import (ObjectArgs,
                              get_impls,
                              get_interfaces,
                              Impl,
                              NullImpl,
                              Interface,
                              LazyEvalDict,
                              LazyEvalChainMap)
from modelx.core.formula import Formula, create_closure
from modelx.core.cells import Cells, CellsImpl
from modelx.core.util import AutoNamer, is_valid_name, get_module


class SpaceArgs(ObjectArgs):
    """Combination of space and arguments to locate its subspace."""

    def __init__(self, space, args, kwargs=None):

        ObjectArgs.__init__(self, space, args, kwargs)
        self.space = self.obj_

    def eval_formula(self):

        func = self.space.paramfunc.func
        codeobj = func.__code__
        name = self.space.name
        namespace = self.space.namespace

        closure = func.__closure__  # None normally.
        if closure is not None:     # pytest fails without this.
            closure = create_closure(self.space.interface)

        altfunc = FunctionType(codeobj, namespace,
                               name=name, closure=closure)

        return altfunc(**self.arguments)


class ParamFunc(Formula):
    def __init__(self, func):
        Formula.__init__(self, func)


class SpaceContainerImpl(Impl):
    """Base class of Model and Space to work as container of spaces.

    **Space Deletion**
    new_space(name)
    del_space(name)

    """

    state_attrs = ['_spaces',
                   'param_spaces',
                   'spacenamer',
                   'paramfunc'] + Impl.state_attrs

    def __init__(self, system, if_class, paramfunc):

        Impl.__init__(self, if_class)

        self.system = system
        self.param_spaces = {}
        self.spacenamer = AutoNamer('Space')

        if paramfunc is None:
            self.paramfunc = None
        else:
            self.paramfunc = ParamFunc(paramfunc)

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
        return name in self.spaces

    def new_space(self, *, name=None, bases=None, paramfunc=None,
                     arguments=None):
        """Create a child space.

        Args:
            name (str): Name of the space. If omitted, the space is
                created automatically.
            bases: If specified, the new space becomes a derived space of
                the `base` space.
            paramfunc: Function whose parameters used to set space parameters.
            arguments: ordered dict of space parameter names to their values.
            base_self: True if subspaces inherit self by default.

        """

        if name is None:
            name = self.spacenamer.get_next(self.namespace)

        if self.has_space(name):
            raise ValueError("Name already assigned.")

        if not is_valid_name(name):
            raise ValueError("Invalid name '%s'." % name)

        space = SpaceImpl(parent=self, name=name, bases=bases,
                          paramfunc=paramfunc, arguments=arguments)

        self._set_space(space)
        return space

    def _set_space(self, space):
        """To be overridden in subclasses."""
        raise NotImplementedError

    def del_space(self, name):
        raise NotImplementedError

    @property
    def namespace(self):
        raise NotImplementedError

    def new_space_from_module(self, module_, recursive=False, **params):

        module_ = get_module(module_)

        if 'name' not in params or params['name'] is None:
            # xxx.yyy.zzz -> zzz
            name = params['name'] = module_.__name__.split('.')[-1]
        else:
            name = params['name']

        space = self.new_space(**params)
        space.new_cells_from_module(module_)

        if recursive and hasattr(module_, '_spaces'):
            for name in module_._spaces:
                submodule = module_.__name__ + '.' + name
                space.new_space_from_module(module_=submodule, recursive=True)

        return space

    def new_space_from_excel(self, book, range_, sheet=None,
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

        space = self.new_space(name=name, paramfunc=param_func)

        for cellsdata in cellstable.items():
            for args, value in cellsdata.items():
                space_args = args[:len(space_params)]
                cells_args = args[len(space_params):]

                subspace = space.get_dyn_space(space_args)

                if cellsdata.name in subspace.cells:
                    cells = subspace.cells[cellsdata.name]
                else:
                    cells = subspace.new_cells(name=cellsdata.name,
                                                  func=blank_func)
                cells.set_value(cells_args, value)

        return space

    def get_dyn_space(self, args, kwargs=None):

        ptr = SpaceArgs(self, args, kwargs)

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
                if 'bases' in space_args:
                    space_args['bases'] = get_impls(space_args['bases'])

            space_args['arguments'] = ptr.arguments
            space = self.new_space(**space_args)
            self.param_spaces[ptr.argvalues] = space
            return space

    def set_paramfunc(self, paramfunc):
        if self.paramfunc is None:
            self.paramfunc = ParamFunc(paramfunc)
        else:
            raise ValueError("paramfunc already assigned.")


class SpaceContainer(Interface):
    """A common base class shared by Model and Space.

    A base class for implementing (sub)space containment.
    """
    def new_space(self, name=None, bases=None, paramfunc=None):
        """Create a (sub)space.

        Args:
            name (str, optional): Name of the space. Defaults to ``SpaceN``,
                where ``N`` is a number determined automatically.
            bases (optional): A space or a sequence of spaces to be the base
                space(s) of the created space.
            paramfunc (optional): Function to specify the parameters of
                dynamic (sub)spaces. The signature of this function is used
                for setting parameters for dynamic (sub)spaces.
                This function should return a mapping of keyword arguments
                to be passed to this method when the dynamic (sub)spaces
                are created.

        Returns:
            The new (sub)space.
        """
        space = self._impl.model.currentspace \
            = self._impl.new_space(name=name, bases=get_impls(bases),
                                      paramfunc=paramfunc)

        return space.interface

    def new_space_from_module(self, module_, recursive=False, **params):
        """Create a (sub)space from an module.

        Args:
            module_: a module object or name of the module object.
            recursive: Not yet implemented.
            **params: arguments to pass to ``new_space``

        Returns:
            The new (sub)space created from the module.
        """

        space = self._impl.model.currentspace \
            = self._impl.new_space_from_module(module_,
                                                  recursive=recursive,
                                                  **params)

        return get_interfaces(space)

    def new_space_from_excel(self, book, range_, sheet=None,
                                name=None,
                                names_row=None, param_cols=None,
                                space_param_order=None,
                                cells_param_order=None,
                                transpose=False,
                                names_col=None, param_rows=None):
        """Create a (sub)space from an Excel range.

        To use this method, ``openpyxl`` package must be installed.

        Args:
            book (str): Path to an Excel file.
            range_ (str): Range expression, such as "A1", "$G4:$K10",
                or named range "NamedRange1".
            sheet (str): Sheet name (case ignored).
            name (str, optional): Name of the space. Defaults to ``SpaceN``,
                where ``N`` is a number determined automatically.
            names_row (optional): an index number indicating
                what row contains the names of cells and parameters.
                Defaults to the top row (0).
            param_cols (optional): a sequence of index numbers
                indicating parameter columns.
                Defaults to only the leftmost column ([0]).
            names_col (optional): an index number, starting from 0,
                indicating what column contains additional parameters.
            param_rows (optional): a sequence of index numbers, starting from
                0, indicating rows of additional parameters, in case cells are
                defined in two dimensions.
            transpose (optional): Defaults to ``False``.
                If set to ``True``, "row(s)" and "col(s)" in the parameter
                names are interpreted inversely, i.e.
                all indexes passed to "row(s)" parameters are interpreted
                as column indexes,
                and all indexes passed to "col(s)" parameters as row indexes.
            space_param_order: a sequence to specify space parameters and
                their orders. The elements of the sequence denote the indexes
                of ``param_cols`` elements, and optionally the index of
                ``param_rows`` elements shifted by the length of
                ``param_cols``. The elements of this parameter and
                ``cell_param_order`` must not overlap.
            cell_param_order (optional): a sequence to reorder the parameters.
                The elements of the sequence denote the indexes of
                ``param_cols`` elements, and optionally the index of
                ``param_rows`` elements shifted by the length of
                ``param_cols``. The elements of this parameter and
                ``cell_space_order`` must not overlap.

        Returns:
            The new (sub)space created from the Excel range.
        """

        space = self._impl.new_space_from_excel(
            book, range_, sheet, name,
            names_row, param_cols,
            space_param_order,
            cells_param_order,
            transpose,
            names_col, param_rows)

        return get_interfaces(space)

    @property
    def spaces(self):
        """A mapping of the names of (sub)spaces to the Space objects"""
        return MappingProxyType(get_interfaces(self._impl.spaces))


class ImplMapMixin:
    """Mixin to LazyEvalChain to update interface with impl

    _update_interfaces needs to be manually called from _update_data.
    """
    def __init__(self):
        self._interfaces = {}
        self.interfaces = MappingProxyType(self._interfaces)

    def _update_interfaces(self):
        self._interfaces.clear()
        self._interfaces.update(get_interfaces(self))

    def __getstate__(self):
        state = {key: value for key, value in self.__dict__.items()}
        del state['interfaces']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.interfaces = MappingProxyType(self._interfaces)


class BaseMembers(LazyEvalDict):
    """Members of bases to be inherited to ``space``"""

    def __init__(self, derived):

        observer = [derived]
        LazyEvalDict.__init__(self, {}, observer)

        self.space = derived.space
        self.member = derived.member

        attr = 'self_' + self.member
        observe = []
        for base in self.space.mro[1:]:
            base._self_members.append_observer(self)

        self._repr = self.space.get_fullname(omit_model=True) + \
            '.BaseMembers(%s)' % self.member

        self.update_data()

    def _update_data(self):

        self.data.clear()
        bases = list(reversed(self.space.mro))

        for base, base_next in zip(bases, bases[1:]):

            attr = 'self_' + self.member
            self.data.update(getattr(base, attr))
            keys = self.data.keys() - base_next.self_members.keys()

            for name in list(self.data):
                if name not in keys:
                    del self.data[name]


class DerivedMembers(LazyEvalDict):

    def __init__(self, space, data=None, observers=None, member=''):

        if data is None:
            data = {}
        if observers is None:
            observers = []

        self.space = space
        self.member = member
        LazyEvalDict.__init__(self, data, observers)
        self._base_members = BaseMembers(self)
        self.update_data()

    @property
    def base_members(self):
        return self._base_members.update_data()


class DerivedCells(ImplMapMixin, DerivedMembers):

    def __init__(self, space, data=None, observers=None, member=''):
        ImplMapMixin.__init__(self)
        DerivedMembers.__init__(self, space, data, observers, member)

    def _update_data(self):
        keys = self.data.keys() - self.base_members.keys()
        for key in keys:
            del self.data[key]

        for key, base_cell in self.base_members.items():
            if key in self.data:
                if self.data[key].formula is base_cell.formula:
                    return
                else:
                    del self.data[key]

            cell = CellsImpl(space=self.space, name=base_cell.name,
                             func=base_cell.formula)
            self.data[key] = cell

        self._update_interfaces()


class DerivedSpaces(ImplMapMixin, DerivedMembers):

    def __init__(self, space, data=None, observers=None, member=''):
        ImplMapMixin.__init__(self)
        DerivedMembers.__init__(self, space, data, observers, member)

    def _update_data(self):

        self.data.clear()
        for base_space in self.base_members.values():

            space = SpaceImpl(parent=self.space, name=base_space.name,
                              bases=base_space.direct_bases,
                              paramfunc=base_space.paramfunc)

            self.data[space.name] = space

        self._update_interfaces()


class DerivedRefs(DerivedMembers):

    def _update_data(self):
        self.data.clear()
        self.data.update(self.base_members)


class SelfMembers(LazyEvalDict):

    def __init__(self, space, attr, data=None, observers=None):

        if data is None:
            data = {}
        if observers is None:
            observers = []

        LazyEvalDict.__init__(self, data, observers)
        self.space = space
        self.attr = attr


class ImplSelfMembers(ImplMapMixin, SelfMembers):

    def __init__(self, space, attr, data=None, observers=None):
        ImplMapMixin.__init__(self)
        SelfMembers.__init__(self, space, attr, data, observers)
        self._repr = self.space.get_fullname(omit_model=True) + '._self_' + attr

    def _update_data(self):
        self._update_interfaces()


class ImplChainMap(ImplMapMixin, LazyEvalChainMap):

    def __init__(self, maps=None, observers=None, observe_maps=True):
        ImplMapMixin.__init__(self)
        LazyEvalChainMap.__init__(self, maps, observers, observe_maps)

    def _update_data(self):
        LazyEvalChainMap._update_data(self)
        self._update_interfaces()


class NameSpaceDict(LazyEvalDict):

    def __init__(self, space, data=None, observers=None):

        if data is None:
            data = {}
        if observers is None:
            observers = []

        LazyEvalDict.__init__(self, data, observers)
        self.space = space

    def _update_data(self):
        _ = self.space.namespace_impl
        self.data.clear()
        self.data.update(get_interfaces(self.space.cells))
        self.data.update(get_interfaces(self.space.spaces))
        self.data.update(self.space.refs)


class SpaceImpl(SpaceContainerImpl):
    """The implementation of Space class.

    The rationales for splitting implementation from its interface are twofold,
    one is to hide from users attributes used only within the package,
    and the other is to free referring objects from getting affected by
    special methods that are meant for changing the behaviour of operations
    for users.

    namespace

        cells
            derived_cells
            self_cells

        spaces
            dynamic_spaces
            static_spaces
                derived_spaces
                self_spaces

        refs
            derived_refs
            self_refs
            global_refs
            local_refs
            arguments

        cells_parameters (Not yet implemented)

    derived_members (ChainMap)
        derived_cells
        derived_spaces
        derived_refs

    self_members
        self_cells
        self_spaces
        self_refs

        # Operations
        remove_derived
        revert_derived

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
        _derived_cells (dict): cells derived from base cells.
        _self_refs
        _derived_refs
        
        cellsnamer (AutoNamer): AutoNamer to auto-name unnamed child cells.
        
        mro (list): MRO of base spaces.
                
        _namespace (dict)
    """
    def __init__(self, parent, name, bases, paramfunc, arguments=None):

        SpaceContainerImpl.__init__(self, parent.system, if_class=Space,
                                    paramfunc=paramfunc)

        self.name = name
        self.parent = parent
        self.cellsnamer = AutoNamer('Cells')

        if arguments is None:
            self._arguments = LazyEvalDict()
        else:
            self._arguments = LazyEvalDict(arguments)

        # Set up direct base spaces and mro
        if bases is None:
            self.direct_bases = []
        elif isinstance(bases, SpaceImpl):
            self.direct_bases = [bases]
        elif isinstance(bases, Sequence) \
                and all(isinstance(base, SpaceImpl) for base in bases):
            self.direct_bases = list(bases)
        else:
            raise TypeError('bases must be space(s).')

        self.mro = []
        self._update_mro()

        # ------------------------------------------------------------------
        # Construct member containers

        self._self_cells = ImplSelfMembers(self, 'cells')
        self._self_spaces = ImplSelfMembers(self, 'spaces')
        self._dynamic_spaces = LazyEvalDict()
        self._self_refs = SelfMembers(self, 'refs')

        self_members = [self._self_cells,
                        self._self_spaces,
                        self._self_refs]

        # Add observers later to avoid circular reference
        self._self_members = LazyEvalChainMap(self_members)
        self._self_members._repr = \
            self.get_fullname(omit_model=True) + '._self_members'

        self._derived_cells = DerivedCells(self, member='cells')
        self._derived_cells._repr = \
            self.get_fullname(omit_model=True) + '._derived_cells'

        self._cells = ImplChainMap([self._self_cells,
                                    self._derived_cells])
        self._cells._repr = \
            self.get_fullname(omit_model=True) + '._cells'

        self._derived_spaces = DerivedSpaces(self, member='spaces')
        self._derived_spaces._repr = \
            self.get_fullname(omit_model=True) + '._derived_spaces'

        self._static_spaces = ImplChainMap([self._self_spaces,
                                            self._derived_spaces])
        self._static_spaces._repr = \
            self.get_fullname(omit_model=True) + '._static_spaces'

        self._spaces = ImplChainMap([self._static_spaces,
                                     self._dynamic_spaces])
        self._spaces._repr = \
            self.get_fullname(omit_model=True) + '._spaces'

        self._derived_refs = DerivedRefs(self, member='refs')
        self._derived_refs._repr = \
            self.get_fullname(omit_model=True) + '._derived_refs'

        self._local_refs = {'get_self': self.get_self_interface,
                            '_self': self.interface}

        self._refs = LazyEvalChainMap([self.model._global_refs,
                                       self._local_refs,
                                       self._arguments,
                                       self._self_refs,
                                       self._derived_refs])

        self._refs._repr = self.get_fullname(omit_model=True) + '._refs'

        derived = [self._derived_cells,
                   self._derived_spaces,
                   self._derived_refs]

        for observer in derived:
            self._self_members.append_observer(observer)

        self._namespace_impl = LazyEvalChainMap([self._cells,
                                                 self._spaces,
                                                 self._refs])
        self._namespace_impl._repr = \
            self.get_fullname(omit_model=True) + '._namespace_impl'

        self._namespace = NameSpaceDict(self)
        self._namespace_impl.append_observer(self._namespace)
        self._namespace._repr = \
            self.get_fullname(omit_model=True) + '._namespace'

    # ----------------------------------------------------------------------
    # Serialization by pickle

    state_attrs = [
        'direct_bases',
        'mro',
        '_self_cells',
        '_derived_cells',
        '_cells',
        '_self_spaces',
        '_derived_spaces',
        '_static_spaces',
        '_dynamic_spaces',
        '_local_refs',
        '_arguments',
        '_self_refs',
        '_derived_refs',
        '_refs',
        '_self_members',
        '_observed_bases',
        '_namespace_impl',
        '_namespace',
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

    @property
    def debug_info(self):

        message = dedent("""\
        name: %s
        self_cells:
            need_update=%s
            names:%s
        derived_cells:
            need_update=%s
            names:%s
        base_cells:
            need_update=%s
            names:%s
        cells: %s
        spaces: %s
        refs: %s
        """)

        return message % (
            self.name,
            self._self_cells._needs_update,
            list(self._self_cells.keys()),
            self._derived_cells._needs_update,
            list(self._derived_cells.keys()),
            self._derived_cells._base_members._needs_update,
            list(self._derived_cells._base_members.keys()),
            list(self._cells.keys()),
            list(self._spaces.keys()),
            list(self._refs.keys())
        )

    # ----------------------------------------------------------------------
    # Components and namespace

    @property
    def self_members(self):
        return self._self_members.update_data()

    @property
    def cells(self):
        return self._cells.update_data()

    @property
    def self_cells(self):
        return self._self_cells.update_data()

    def self_cells_set_update(self):
        return self._self_cells.set_update(skip_self=False)

    @property
    def derived_cells(self):
        return self._derived_cells.update_data()

    @property
    def spaces(self):
        return self._spaces.update_data()

    @property
    def self_spaces(self):
        return self._self_spaces.update_data()

    @property
    def derived_spaces(self):
        return self._derived_spaces.update_data()

    @property
    def dynamic_spaces(self):
        return self._dynamic_spaces.update_data()

    @property
    def refs(self):
        return self._refs.update_data()

    @property
    def self_refs(self):
        return self._self_refs.update_data()

    @property
    def derived_refs(self):
        return self._derived_refs.update_data()

    @property
    def namespace_impl(self):
        return self._namespace_impl.update_data()

    @property
    def namespace(self):
        return self._namespace.get_updated_data()

    # ----------------------------------------------------------------------
    # Inheritance

    def _update_mro(self):
        """Calculate the Method Resolution Order of bases using the C3 algorithm.

        Code modified from 
        http://code.activestate.com/recipes/577748-calculate-the-mro-of-a-class/

        Args:
            bases: sequence of direct base spaces.

        """
        seqs = [base.mro.copy() for base
                in self.direct_bases] + [self.direct_bases]
        res = []
        while True:
            non_empty = list(filter(None, seqs))

            if not non_empty:
                # Nothing left to process, we're done.
                self.mro.clear()
                self.mro.extend([self] + res)
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

    def _set_space(self, space):
        if space.is_dynamic():
            self._dynamic_spaces[space.name] = space
            self._dynamic_spaces.set_update(skip_self=True)
        else:
            self._self_spaces[space.name] = space
            self._self_spaces.set_update(skip_self=True)

    def del_space(self, name):
        if name not in self.spaces:
            raise ValueError("Space '%s' does not exist" % name)

        space = self.spaces[name]
        if space.is_dynamic():
            # TODO: Destroy space
            del self._dynamic_spaces[name]
            self._dynamic_spaces.set_update(skip_self=True)

        elif name in self._self_spaces[name]:
            # TODO: Destroy space
            del self._self_spaces[name]
            self._self_spaces.set_update(skip_self=True)

        else:
            raise ValueError("Derived cells cannot be deleted")

    def set_attr(self, name, value):

        if not is_valid_name(name):
            raise ValueError

        if name in self.namespace:
            if name in self.refs:
                self.refs[name] = value
                self.refs.set_update(skip_self=False)

            elif name in self.cells:
                if self.cells[name].is_scalar():
                    self.cells[name].set_value((), value)
                else:
                    raise AttributeError("Cells '%s' is not a scalar." % name)

            else:
                raise ValueError

        else:
            self._self_refs[name] = value
            self._self_refs.set_update(skip_self=True)

    def del_attr(self, name):

        if name in self.namespace:
            if name in self.cells:
                if name in self.self_cells:
                    self.del_cells(name)
                elif name in self.derived_cells:
                    raise KeyError("Derived cells cannot be removed")
                elif name in self.dynamic_spaces:
                    self.del_cells(name)
                else:
                    raise RuntimeError("Must not happen")

            elif name in self.spaces:
                if name in self.self_spaces:
                    pass
                elif name in self.derived_cells:
                    raise KeyError("Derived space cannot be removed")
                else:
                    raise RuntimeError("Must not happen")

            elif name in self.refs:
                if name in self.self_refs:
                    pass
                elif name in self.derived_refs:
                    raise KeyError("Derived refs cannot be removed")
                else:   # global refs, local refs or arguments
                    raise KeyError("'%s' cannot be removed" % name)

            else:
                raise RuntimeError("Must not happen")

        else:
            raise KeyError("'%s' not found in Space '%s'" % (name, self.name))

    def del_cells(self, name):

        if name in self.self_cells:
            # self._self_cells[name].parent = None
            cells = self.self_cells.pop(name)
            self.self_cells.set_update()

        elif name in self.dynamic_spaces:
            cells = self.dynamic_spaces.pop(name)
            self.dynamic_spaces.set_update()

        else:
            raise KeyError("Cells '%s' does not exist" % name)

        NullImpl(cells)

        # for base in self.direct_bases:
        #     if name in base.cells:
        #         base_cells = base.cells[name]
        #         self._derived_cells[name] = \
        #             self.new_cells(name=name, func=base_cells.formula)
        #     break

    def _del_derived_cells(self, name):

        if name in self.namespace:
            if name in self._derived_cells:
                self._derived_cells[name].parent = None
                del self._derived_cells[name]

            elif name in self._derived_spaces:
                self._derived_spaces[name].parent = None
                del self._derived_spaces[name]

            elif name in self._derived_refs:
                del self._derived_refs[name]

            else:
                raise RuntimeError("Name already assigned.")

            return True

        else:
            return False

    def revert_derived(self, name):
        raise NotImplementedError

    def has_bases(self):
        return len(self.mro) > 1

    def is_dynamic(self):
        return bool(self._arguments)

    def new_cells(self, name=None, func=None):
        cells = CellsImpl(space=self, name=name, func=func)
        self.set_cells(cells.name, cells)
        return cells

    def new_cells_from_module(self, module_):
        # Outside formulas only

        module_ = get_module(module_)
        newcells = {}

        for name in dir(module_):
            func = getattr(module_, name)
            if isinstance(func, FunctionType):
                # Choose only the functions defined in the module.
                if func.__module__ == module_.__name__:
                    newcells[name] = \
                        self.new_cells(name, func)

        return newcells

    def new_cells_from_excel(self, book, range_, sheet=None,
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
            cells = self.new_cells(name=cellsdata.name, func=blank_func)
            for args, value in cellsdata.items():
                cells.set_value(args, value)

    @property
    def signature(self):
        return self.paramfunc.signature

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

    def to_frame(self):

        from modelx.io.pandas import space_to_dataframe

        return space_to_dataframe(self)


class Space(SpaceContainer):
    """Container for cells and other objects referred in formulas.

    Space objects have quite a few mapping members. Those are
    MappyingProxyTypes objects, which are essentially frozen dictionaries.

    ``namespace`` stores all names, with their associated objects,
    that can be referenced in the form of attribute access to the space.
    Those names can also be referenced from within the formulas of the
    cells contained in the space.

    ``namespace`` is broken down into ``cells``, ``spaces`` and ``refs`` maps.
    ``cells`` is a map of all the cells contained in the space,
    and ``spaces`` is a map of all the subspaces of the space.
    ``refs`` contains names and their associated objects that are not
    part of the space but are accessible from the space.

    ``cells`` is further broken down into ``self_cells`` and ``derived_cells``.
    ``self_cells`` contains cells that are newly defined or overridden
    in the class. On the other hand, ``derived_cells`` contains cells
    derived from the space's base class(s).

    ``space`` is first broken down into ``static_spaces`` and
    ``dynamic_spaces``. ``static_spaces`` contains subspaces of the space
    that are explicitly created by the user by the space's ``new_space``
    method or one of its variants. ``dynamic_spaces`` contains parametrized
    subspaces that are created dynamically by ``()`` or ``[]`` operation on
    the space.

    Objects with their associated names are::

        namespace
            cells
                self_cells
                derived_cells
            spaces
                static_spaces
                    self_spaces
                    derived_spaces
                dynamic_spaces
            refs
                self_refs
                derived_refs
                global_refs
                arguments
    """
    # __slots__ = ('_impl',)

    @property
    def name(self):
        """The name of the space."""
        return self._impl.name

    # def __repr__(self):
    #     return self._impl.repr_

    # ----------------------------------------------------------------------
    # Manipulating cells

    def new_cells(self, name=None, func=None):
        """Create a cells in the space.

        Args:
            name: If omitted, the model is named automatically ``CellsN``,
                where ``N`` is an available number.
            func: The function to define the formula of the cells.

        Returns:
            The new cells.
        """
        # Outside formulas only
        return self._impl.new_cells(name, func).interface

    @property
    def cells(self):
        """A mapping of cells names to the cells objects in the space."""
        return self._impl.cells.interfaces

    @property
    def self_cells(self):
        """A mapping that associates names to cells defined in the space"""
        return self._impl.self_cells.interfaces

    @property
    def derived_cells(self):
        """A mapping associating names to derived cells."""
        return self._impl.derived_cells.interfaces

    @property
    def refs(self):
        """A map associating names to objects accessible by the names."""
        return self._impl

    def new_cells_from_module(self, module_):
        """Create a cells from a module."""
        # Outside formulas only

        newcells = self._impl.new_cells_from_module(module_)
        return get_interfaces(newcells)

    def new_cells_from_excel(self, book, range_, sheet=None,
                                names_row=None, param_cols=None,
                                param_order=None,
                                transpose=False,
                                names_col=None, param_rows=None):
        """Create multiple cells from an Excel range.

        This method reads values from a range in an Excel file,
        create cells and populate them with the values in the range.
        To use this method, ``openpyxl`` package must be installed.

        The Excel file to read data from is specified by ``book``
        parameters. The ``range_`` can be a range address, such as "$G4:$K10",
        or a named range. In case a range address is given,
        ``sheet`` must also be given.

        By default, cells data are interpreted as being laid out side-by-side.
        ``names_row`` is a row index (starting from 0) to specify the
        row that contains the names of cells and parameters.
        Cells and parameter names must be contained in a single row.
        ``param_cols`` accepts a sequence (such as list or tuple) of
        column indexes (starting from 0) that indicate columns that
        contain cells arguments.

        **2-dimensional cells definitions**

        The optional ``names_col`` and ``param_rows`` parameters are used,
        when data for one cells spans more than one column.
        In such cases, the cells data is 2-dimensional, and
        there must be parameter row(s) across the columns
        that contain arguments of the parameters.
        A sequence of row indexes that indicate parameter rows
        is passed to ``param_rows``.
        The names of those parameters must be contained in the
        same rows as parameter values (arguments), and
        ``names_col`` is to indicate the column position at which
        the parameter names are defined.

        **Horizontal arrangement**

        By default, cells data are interpreted as being placed
        side-by-side, regardless of whether one cells corresponds
        to a single column or multiple columns.
        ``transpose`` parameter is used to alter this orientation,
        and if it is set to ``True``, cells values are
        interpreted as being placed one above the other.
        "row(s)" and "col(s)" in the parameter
        names are interpreted inversely, i.e.
        all indexes passed to "row(s)" parameters are interpreted
        as column indexes,
        and all indexes passed to "col(s)" parameters as row indexes.


        Args:
            book (str): Path to an Excel file.
            range_ (str): Range expression, such as "A1", "$G4:$K10",
                or named range "NamedRange1".
            sheet (str): Sheet name (case ignored).
            names_row (optional): an index number indicating
                what row contains the names of cells and parameters.
                Defaults to the top row (0).
            param_cols (optional): a sequence of index numbers
                indicating parameter columns.
                Defaults to only the leftmost column ([0]).
            names_col (optional): an index number, starting from 0,
                indicating what column contains additional parameters.
            param_rows (optional): a sequence of index numbers, starting from
                0, indicating rows of additional parameters, in case cells are
                defined in two dimensions.
            transpose (optional): Defaults to ``False``.
                If set to ``True``, "row(s)" and "col(s)" in the parameter
                names are interpreted inversely, i.e.
                all indexes passed to "row(s)" parameters are interpreted
                as column indexes,
                and all indexes passed to "col(s)" parameters as row indexes.
            param_order (optional): a sequence to reorder the parameters.
                The elements of the sequence are the indexes of ``param_cols``
                elements, and optionally the index of ``param_rows`` elements
                shifted by the length of ``param_cols``.
        """
        return self._impl.new_cells_from_excel(
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
        self._impl.set_attr(name, value)

    def __delattr__(self, name):
        self._impl.del_attr(name)

    # ----------------------------------------------------------------------
    # Manipulating subspaces

    def has_params(self):
        """Check if the parameter function is set."""
        # Outside formulas only
        return bool(self.signature)

    def __getitem__(self, args):
        return self._impl.get_dyn_space(args).interface

    def __call__(self, *args, **kwargs):
        return self._impl.get_dyn_space(args, kwargs).interface

    def set_paramfunc(self, paramfunc):
        """Set if the parameter function."""
        self._impl.set_paramfunc(paramfunc)

    # ----------------------------------------------------------------------
    # Conversion to Pandas objects

    def to_frame(self):
        """Convert the space itself into a Pandas DataFrame object."""
        return self._impl.to_frame()

    @property
    def frame(self):
        """Alias of ``to_frame()``."""
        return self._impl.to_frame()


