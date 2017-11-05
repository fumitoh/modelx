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

import sys
import builtins
from types import MappingProxyType
from collections import Sequence, ChainMap, Mapping, UserDict
from inspect import BoundArguments


# To add new method apply_defaults to BoundArguments.
if sys.version_info < (3, 5, 0):

    def _apply_defaults(self):
        """Set default values for missing arguments.

        For variable-positional arguments (*args) the default is an
        empty tuple.

        For variable-keyword arguments (**kwargs) the default is an
        empty dict.
        """
        from collections import OrderedDict
        from inspect import (_empty, _VAR_KEYWORD, _VAR_POSITIONAL)

        arguments = self.arguments
        new_arguments = []
        for name, param in self._signature.parameters.items():
            try:
                new_arguments.append((name, arguments[name]))
            except KeyError:
                if param.default is not _empty:
                    val = param.default
                elif param.kind is _VAR_POSITIONAL:
                    val = ()
                elif param.kind is _VAR_KEYWORD:
                    val = {}
                else:
                    # This BoundArguments was likely produced by
                    # Signature.bind_partial().
                    continue
                new_arguments.append((name, val))
        self.arguments = OrderedDict(new_arguments)

    BoundArguments.apply_defaults = _apply_defaults


class ObjectArgs:
    """Pair of an object and its arguments"""

    state_attrs = ['obj_', 'argvalues']

    def __init__(self, obj_, args, kwargs=None):

        if not isinstance(args, Sequence):
            args = (args,)

        if kwargs is None:
            kwargs = {}

        self.obj_ = obj_
        self._bind_args(args, kwargs)


    def _bind_args(self, args, kwargs=None):

        if kwargs is None:
            kwargs = {}
        self.boundargs = self.obj_.signature.bind(*args, **kwargs)
        self.boundargs.apply_defaults()
        self.argvalues = tuple(self.boundargs.arguments.values())
        self.id_ = (self.obj_, self.argvalues)

    def __getstate__(self):
        state = {key: value for key, value in self.__dict__.items()
                 if key in self.state_attrs}

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._bind_args(self.argvalues)

        if self.argvalues != state['argvalues']:
            raise ValueError('Pickle Error.')

    @property
    def arguments(self):
        return self.boundargs.arguments

    @property
    def parameters(self):
        return tuple(self.obj_.signature.parameters.keys())

    def __hash__(self):
        return hash(self.id_)

    def __eq__(self, other):
        return self.id_ == other.id_

    def __repr__(self):
        # TODO: Need to generalize. Currently CellsArg specific.
        arg_repr = ""
        for param, arg in self.arguments.items():
            arg_repr += param + "=" + repr(arg) + ", "

        if len(arg_repr) > 1:
            arg_repr = arg_repr[:-2]

        return self.obj_.get_fullname() + "(" + arg_repr + ")"

def get_interfaces(impls):
    """Get interfaces from their implementations."""
    if impls is None:
        return None

    elif isinstance(impls, Mapping):
        return {name: impls[name].interface for name in impls}

    elif isinstance(impls, Sequence):
        return [impl.interface for impl in impls]

    else:
        return impls.interface


def get_impls(interfaces):
    """Get impls from their interfaces."""
    if interfaces is None:
        return None

    elif isinstance(interfaces, Mapping):
        return {name: interfaces[name]._impl for name in interfaces}

    elif isinstance(interfaces, Sequence):
        return [interfaces._impl for interfaces in interfaces]

    else:
        return interfaces._impl


class Impl:
    """The ultimate base class of *Impl classes.

    The rationales for splitting implementation from its interface are twofold,
    one is to hide from users attributes used only within the package,
    and the other is to free referring objects from getting affected by
    special methods that are meant for changing the behaviour of operations
    for users."""

    state_attrs = ['interface']

    def __init__(self, interface_class):
        self.interface = interface_class(self)

    @property
    def repr_string(self):
        """String to called by Interface.__repr__"""
        if self._repr_parent:
            return "%s in %s" % (self._repr_self, self._repr_parent)
        else:
            return self._repr_self

    @property
    def _repr_self(self):
        raise NotImplementedError

    @property
    def _repr_parent(self):
        raise NotImplementedError


class NullImpl(Impl):
    """Singleton to represent deleted objects.

    Call ``impl.del_self`` if it exists,
    and detach ``impl`` from its interface.
    The interface points to this NllImpl singleton.
    """
    the_instance = None

    def __new__(cls, impl):

        if cls.the_instance is None:
            cls.the_instance = object.__new__(cls)

        if hasattr(impl, 'del_self'):
            impl.del_self()

        impl.interface._impl = cls.the_instance

        return cls.the_instance

    def __init__(self, impl):
        pass

    def __getattr__(self, item):
        raise RuntimeError("Deleted object")


class Interface:
    """The ultimate base class of Model, Space, Cells.

    The subclasses of Interface have only one member, ``_impl``,
    which is their implementation objects.

    """

    def __new__(cls, _impl):

        if isinstance(_impl, Impl):
            if not hasattr(_impl, "interface"):
                self = object.__new__(cls)
                object.__setattr__(self, '_impl', _impl)
                return self
            else:
                return _impl.interface
        else:
            raise ValueError("Invalid direct constructor call.")

    @property
    def name(self):
        """Name of the interface."""
        return self._impl.name

    @property
    def fullname(self):
        """Dotted name of the interface."""
        return self._impl.fullname

    def __repr__(self):
        type_ = self.__class__.__name__
        return "<%s %s>" % (type_, self._impl.repr_string)

    def __getnewargs__(self):
        return (self._impl,)

    def __getstate__(self):
        return self._impl

    def __setstate__(self, state):
        object.__setattr__(self, '_impl', state)


class LazyEvalChain:
    """Base class for flagging observers so that they update themselves later.

    An object of a class inherited from LazyEvaluation can have its observers.
    When the data of the object is updated, the users call set_update method,
    to flag the object's observers.
    When the observers get_updated methods are called later, their data
    contents are updated depending on their update states.
    The updating operation can be customized by overwriting _update_data method.
    """

    def __init__(self, observers):
        self.needs_update = False # must be read only
        self.observers = []
        self.observing = []
        for observer in observers:
            self.append_observer(observer)

    def set_update(self, skip_self=False):

        if not skip_self:
            self.needs_update = True
        for observer in self.observers:
            if not observer.needs_update:
                observer.set_update()

    def get_updated(self):
        if not self.needs_update:
            return self
        else:
            for other in self.observing:
                other.get_updated()
            self._update_data()
            self.needs_update = False
            return self

    def _update_data(self):
        raise NotImplementedError   # To be overwritten in derived classes

    def append_observer(self, observer):
        if all(observer is not other for other in self.observers):
            self.observers.append(observer)
            observer.observing.append(self)
            observer.set_update()

    def observe(self, other):
        other.append_observer(self)

    def remove_observer(self, observer):
        self.observers.remove(observer)
        observer.observing.remove(self)

    def unobserve(self, other):
        other.remove_observer(self)

    def __getstate__(self):
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def debug_print_observers(self, indent_level=0):
        print(' ' * indent_level * 4,
              self, ':', self.needs_update)
        for observer in self.observers:
            observer.debug_print_observers(indent_level + 1)


class LazyEvalDict(LazyEvalChain, UserDict):

    def __init__(self, data=None, observers=None):

        if data is None:
            data = {}
        if observers is None:
            observers = []

        UserDict.__init__(self, data)
        LazyEvalChain.__init__(self, observers)
        self._repr = ''

    def get_updated_data(self):
        """Get updated ``data`` instead of self. """
        self.get_updated()
        return self.data

    def _update_data(self):
        pass

    def set_item(self, name, value, skip_self=False):
        UserDict.__setitem__(self, name, value)
        self.set_update(skip_self)

    def del_item(self, name, skip_self=False):
        UserDict.__delitem__(self, name)
        self.set_update(skip_self)

    def __repr__(self):

        if self._repr:
            return self._repr
        else:
            return UserDict.__repr__(self)

    def __getstate__(self):

        state = self.__dict__.copy()
        if '__builtins__' in state['data']:
            data = state['data'].copy()
            data['__builtins__'] = '__builtins__'
            state['data'] = data

        return state

    def __setstate__(self, state):

        if '__builtins__' in state['data']:
            state['data']['__builtins__'] = builtins

        self.__dict__.update(state)


class MapProxyMixin:

    def __init__(self, data):
        self.mproxy = MappingProxyType(data)

    def __getstate__(self):
        state = super().__getstate__()
        del state['mproxy']
        return state

    def __setstate__(self, state):
        super().__setstate__(state)
        self.mproxy = MappingProxyType(self)


class LazyEvalDictWithMapProxy(MapProxyMixin, LazyEvalDict):

    def __init__(self, data=None, observers=None):
        LazyEvalDict.__init__(self, data, observers)
        MapProxyMixin.__init__(self, self.data)


class LazyEvalChainMap(LazyEvalChain, ChainMap):

    def __init__(self, maps=None, observers=None, observe_maps=True):

        if maps is None:
            maps = []
        if observers is None:
            observers = []

        ChainMap.__init__(self, *maps)
        LazyEvalChain.__init__(self, observers)
        self._repr = ''

        if observe_maps:
            for other in maps:
                if isinstance(other, LazyEvalChain):
                    other.append_observer(self)

        self.get_updated()

    def _update_data(self):
        for map_ in self.maps:
            if isinstance(map_, LazyEvalChain):
                map_.get_updated()

    def __setitem__(self, name, value):
        raise NotImplementedError

    def __delitem__(self, name):
        raise NotImplementedError

    def __repr__(self):

        if self._repr:
            return self._repr
        else:
            return ChainMap.__repr__(self)

    def __getstate__(self):
        state = LazyEvalChain.__getstate__(self)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)


class ChainMapWithMapProxy(MapProxyMixin, LazyEvalChainMap):

    def __init__(self, maps=None, observers=None, observe_maps=True):
        LazyEvalChainMap.__init__(self, maps, observers, observe_maps)
        self.mproxy = MappingProxyType(self)

    def _update_data(self):
        LazyEvalChainMap._update_data(self)


class InterfaceMixin:
    """Mixin to LazyEvalChain to update interface with impl

    _update_interfaces needs to be manually called from _update_data.
    """
    def __init__(self, map_class):
        self._interfaces = {}
        self.map_class = map_class
        self.interfaces = map_class(self._interfaces)

    def _update_interfaces(self):
        self._interfaces.clear()
        self._interfaces.update(get_interfaces(self))

    def __getstate__(self):
        state = super().__getstate__()
        if self.map_class is MappingProxyType:
            state['map_class'] = 'MappingProxyType'
        del state['interfaces']
        return state

    def __setstate__(self, state):
        super().__setstate__(state)
        if self.map_class == 'MappingProxyType':
            self.map_class = MappingProxyType
        self.interfaces = self.map_class(self._interfaces)


class ImplLazyEvalDict(InterfaceMixin, LazyEvalDict):

    def __init__(self, ifmap_class, data=None, observers=None):
        InterfaceMixin.__init__(self, ifmap_class)
        LazyEvalDict.__init__(self, data, observers)

    def _update_data(self):
        LazyEvalDict._update_data(self)
        self._update_interfaces()


class ImplChainMap(InterfaceMixin, LazyEvalChainMap):

    def __init__(self, ifmap_class, maps=None,
                 observers=None, observe_maps=True):
        InterfaceMixin.__init__(self, ifmap_class)
        LazyEvalChainMap.__init__(self, maps, observers, observe_maps)

    def _update_data(self):
        LazyEvalChainMap._update_data(self)
        self._update_interfaces()

# The code below is modified from UserDict in Python's standard library.
#
# The original code was taken from the following URL:
#   https://github.com/python/cpython/blob/\
#       7e68790f3db75a893d5dd336e6201a63bc70212b/\
#       Lib/collections/__init__.py#L968-L1027


class ImmutableMapWrapper(Mapping):

    # Start by filling-out the abstract methods
    def __init__(self, data):
        self.data = data

    def __len__(self): return len(self.data)

    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        if hasattr(self.__class__, "__missing__"):
            return self.__class__.__missing__(self, key)
        raise KeyError(key)

    def __iter__(self):
        return iter(self.data)

    # Modify __contains__ to work correctly when __missing__ is present
    def __contains__(self, key):
        return key in self.data

    # Now, add the methods in dicts but not in MutableMapping
    def __repr__(self): return repr(self.data)

