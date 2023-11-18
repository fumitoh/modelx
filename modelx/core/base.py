# Copyright (c) 2017-2023 Fumito Hamamura <fumito.ham@gmail.com>

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
from collections.abc import Sequence, Mapping
from inspect import BoundArguments
from modelx.core.chainmap import CustomChainMap
from modelx.core.errors import DeletedObjectError

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
        from inspect import _empty, _VAR_KEYWORD, _VAR_POSITIONAL

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


def get_interfaces(impls):
    """Get interfaces from their implementations."""
    if impls is None:
        return None

    if isinstance(impls, Mapping):  # LazyEvalDict and LazyEvalChainMap
        return {name: impls[name].interface for name in impls}

    elif isinstance(impls, Sequence):
        return [impl.interface for impl in impls]

    else:
        raise RuntimeError("must not happen")


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


def is_mixin(cls):
    return hasattr(cls, "_" + cls.__name__ + "__mixin_slots")


def is_concrete(cls):
    if hasattr(cls, "__slots__") and not is_mixin(cls):
        return True
    else:
        return False


def get_mixin_slots(*mixins):
    """Returns slots pushed down from mix-in classes.

    Used to define ``__slots__`` in concrete classes.
    For example::

        class A(X):             # A concrete base class (Non-empty slot)
            __slots__ = ("a",) + get_mixin_slots(X)

        class B:                # A mix-in class
            __slots__ = ()      # Mixins must have empty slots.
            __mixin_slots = ("b",)    # Mixin __mixin_slots to be pushed down.

        class C(B, A):      # Mixins must come before concrete base classes.
            __slots__ = ("c",) + get_mixin_slots(B, A)
                            # get_mixin_slots adds mixin slots ("b")
                            # before the nearest concrete class.
    """
    class Temp(*mixins):
        __slots__ = ()

    bases = Temp.__mro__[1:]
    count_concrete_or_mixin = tuple(
        is_concrete(c) or is_mixin(c) for c in bases
    ).count(True)

    bases = bases[:count_concrete_or_mixin]     # Cut off built-in classes

    assert all(is_concrete(c) != is_mixin(c) for c in bases)    # XOR

    mixin_slots = []
    concrete_bases = []
    for b in bases:
        if is_concrete(b):
            concrete_bases.append(b)
        elif is_mixin(b):
            if any(issubclass(concrete, b) for concrete in concrete_bases):
                continue
            else:
                mixin_slots.append(b)
        else:
            raise RuntimeError("must not happen")

    return tuple(attr
                 for b in mixin_slots
                 for attr in getattr(b, "_" + b.__name__ + "__mixin_slots"))


class BaseImpl:
    __slots__ = ()


class Impl(BaseImpl):
    """The ultimate base class of *Impl classes.

    The rationales for splitting implementation from its interface are twofold,
    one is to hide from users attributes used only within the package,
    and the other is to free referring objects from getting affected by
    special methods that are meant for changing the behaviour of operations
    for users."""

    __slots__ = (
        "system",
        "interface",
        "parent",
        "name",
        "spmgr",
        "model",
        "allow_none",
        "_doc"
    )

    interface_cls = None  # Override in sub classes if interface class exists

    def __init__(self, system, parent, name, spmgr, interface=None, doc=None):

        if self.interface_cls:
            self.interface = self.interface_cls(self)
        else:
            self.interface = interface

        self.system = system
        self.parent = parent
        self.model = parent.model if parent else self
        self.name = name
        self.spmgr = spmgr
        self.allow_none = None
        self._doc = doc

    def get_property(self, name):
        prop = getattr(self, name)
        if prop is None:
            return self.parent.get_property(name)
        else:
            return prop


    def get_fullname(self, omit_model=False):

        if self.parent:
            result = self.parent.get_fullname(False) + "." + self.name
            if omit_model:
                separated = result.split(".")
                separated.pop(0)
                return ".".join(separated)
            else:
                return result
        else:
            if omit_model:
                return ""
            else:
                return self.name

    def is_model(self):
        return self.parent is None

    def has_ascendant(self, other):

        if self.is_model():
            return False
        elif other is self.parent:
            return True
        else:
            return self.parent.has_ascendant(other)

    def has_descendant(self, other):
        return other.has_ascendant(self)

    def has_linealrel(self, other):
        return self.has_ascendant(other) or self.has_descendant(other)

    def on_delete(self):
        set_null_impl(self)

    def to_node(self):
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # repr methods

    @property
    def doc(self):
        return self._doc

    # ----------------------------------------------------------------------
    # repr methods

    @property
    def idstr(self):
        return self.get_fullname(omit_model=True)

    @property
    def evalrepr(self):
        """Evaluable repr"""
        if self.is_model():
            return self.get_fullname()
        else:
            return self.parent.evalrepr + "." + self.name

    def repr_self(self, add_params=True):
        raise NotImplementedError

    def repr_parent(self):
        raise NotImplementedError

    def get_repr(self, fullname=False, add_params=True):

        if fullname and not self.is_model():
            return self.repr_parent() + "." + self.repr_self(add_params)
        else:
            return self.repr_self(add_params)

    def __repr__(self):
        return self.get_repr(fullname=True, add_params=True)


class Derivable:

    __slots__ = ()
    __mixin_slots = ("_is_derived",)

    def __init__(self, is_derived):
        self._is_derived = is_derived

    def set_defined(self):
        if not self._is_derived:
            return
        else:
            self._is_derived = False

    def is_defined(self):
        return not self._is_derived

    def is_derived(self):
        return self._is_derived

    @property
    def bases(self):
        return self.spmgr.get_deriv_bases(self)

    @property
    def defined_bases(self):
        return self.spmgr.get_deriv_bases(self, defined_only=True)

    @staticmethod
    def _get_members(other):
        raise NotImplementedError

    def on_inherit(self, updater, bases):
        raise NotImplementedError


class NullImpl(BaseImpl):
    """Singleton to represent deleted objects.

    Call ``impl.del_self`` if it exists,
    and detach ``impl`` from its interface.
    The interface points to this NllImpl singleton.
    """
    def __getattr__(self, item):
        raise DeletedObjectError("the object has been deleted")


null_impl = NullImpl()


def set_null_impl(impl):
    object.__setattr__(impl.interface, "_impl", null_impl)


class Interface:
    """The ultimate base class of Model, Space, Cells.

    All the properties defined in this class are available in Model,
    Space and Cells objects.
    """

    __slots__ = ("_impl",)
    properties = ["allow_none"]

    def __new__(cls, _impl):

        if isinstance(_impl, Impl):
            if not hasattr(_impl, "interface"):
                self = object.__new__(cls)
                object.__setattr__(self, "_impl", _impl)
                return self
            else:
                return _impl.interface
        elif isinstance(_impl, NullImpl):
            self = object.__new__(cls)
            object.__setattr__(self, "_impl", _impl)
            return self
        else:
            raise ValueError("Invalid direct constructor call.")

    def _get_object(self, name, as_proxy=False):
        """Get an object from its dotted name

        Used also for retrieving Leaf's attributes by spyder-modelx
        """
        parts = name.split(".")

        try:
            obj = getattr(self, parts.pop(0))
        except AttributeError:
            raise NameError("'%s' not found" % name)

        if parts:
            return obj._get_object(".".join(parts), as_proxy)
        else:
            return obj

    @property
    def name(self):
        """Name of the object."""
        return self._impl.name

    @property
    def fullname(self):
        """Dotted name of the object.

        Names joined by dots, such as 'Model1.Space1.Cells1',
        each element in the string is the name of the parent object
        of the next one joined by a dot.
        """
        return self._impl.get_fullname()

    @property
    def parent(self):
        """The parent of this object. None for models.

        The parent object of a cells is a space that contains the cells.
        The parent object of a space is either a model or another space
        that contains the space.
        """

        if self._impl.parent is None:
            return None
        else:
            return self._impl.parent.interface

    @property
    def model(self):
        """The model this object belongs to.

        This is a property of Model, Space and Cells.
        For models, this property is themselves.
        """
        return self._impl.model.interface

    @property
    def doc(self):
        """Documentation string

        :attr:`doc` is a property of :class:`~modelx.core.model.Model`,
        Space and :class:`~modelx.core.cells.Cells`
        for setting and getting a string to document the object.

        When a Model is written to files by
        :func:`~modelx.write_model` or
        its variants, the docsting of the Model and
        :class:`~modelx.core.space.UserSpace`
        objects in the Model are written at the top of the *__init__.py*
        files as if they are the docstrings of Python modules.

        The :attr:`doc` property of a Cells is linked to the docstring
        of its Formula if the Formula is not defined by a lambda function.
        When the :attr:`doc`
        property of a Cells is updated, then the docstring of the Cells'
        Formula is also updated, and vice versa::

            >>> foo.formula
            def foo(x):
                \"\"\"The docstring of foo\"\"\"
                return x

            >>> foo.doc
            'The docstring of foo'

            >>> foo.doc = "The doc propery of foo"

            >>> foo.formula
            def foo(x):
                \"\"\"The doc propery of foo\"\"\"
                return x


        See Also:
            :meth:`Cells.set_doc<modelx.core.cells.Cells.set_doc>`

        .. versionchanged:: 0.14.0
        """
        return self._impl.doc

    def __repr__(self):
        type_ = self.__class__.__name__

        if not self._is_valid():
            return "<%s null object>" % type_

        else:
            return "<%s %s>" % (type_,
                                self._impl.get_repr(
                                    fullname=True, add_params=True))

    def __getstate__(self):
        return self._impl

    def __setstate__(self, state):
        object.__setattr__(self, "_impl", state)

    def __reduce__(self):
        if self._is_valid() and self._impl.system.serializing:

            if self._impl.system.serializing.version in (3, 4, 5, 6):
                return self._reduce_serialize_3()
            else:
                raise ValueError("invalid serializer version")
        else:
            return object.__reduce__(self)

    def _reduce_serialize_3(self):

        model = self._impl.system.serializing.model
        if model is self.model:
            # Replace model name with empty string
            idtuple = ("",) + self._idtuple[1:]
        else:
            idtuple = self._idtuple

        return self._impl.system._get_object_from_idtuple_reduce, (idtuple,)

    def set_property(self, name: str, value):
        """Set property ``name``

        Set ``value`` to property ``name`` of an interface.
        Equivalent to ``x.name = value``,
        where x is a Model/Space/Cells object.
        """
        if name in self.properties:
            getattr(Interface, name).fset(self, value)
        else:
            raise ValueError("property %s not defined")

    @property
    def allow_none(self):
        """Whether a cells can have None as its value.

        This is a property of Model, Space and Cells.
        If ``allow_none`` of a cells is False,
        the cells cannot have None as its value.
        Assigning None to the cells
        or its formula returning None raises an Error.
        If True, the cells can have None as their value.
        If set to None, ``allow_none`` of its parent is looked up,
        and the search continues until True or False is found.

        Returns:
            True if the cells can have None, False if it cannot,
            or None if a default value from the parent is to be used.
        """
        return self._impl.allow_none

    @allow_none.setter
    def allow_none(self, value):
        self._impl.allow_none = value if value is None else bool(value)

    # ----------------------------------------------------------------------
    # Override base class methods

    @property
    def _baseattrs(self):
        """A dict of members expressed in literals"""

        result = {
            "type": type(self).__name__,
            "id": id(self._impl),
            "name": self.name,
            "fullname": self.fullname,
            "repr": self._get_repr(),
            "namedid": self._idstr
        }

        return result

    def _to_attrdict(self, attrs=None):
        """Get extra attributes"""
        result = self._baseattrs

        for name in attrs:
            if hasattr(self, name):
                attr = getattr(self, name)
                if hasattr(attr, "_to_attrdict"):
                    result[name] = attr._to_attrdict(attrs)
                elif callable(attr):
                    result[name] = attr()
                else:
                    result[name] = attr

        return result

    def _get_attrdict(self, extattrs=None, recursive=True):
        """Get attributes in a dict"""

        return {
            "type": type(self).__name__,
            "id": id(self._impl),
            "name": self.name,
            "fullname": self.fullname,
            "repr": self._get_repr(),
            "namedid": self._idstr
        }

    def _get_attrdict_extra(self, attrdict, extattrs=None, recursive=True):

        for name in extattrs:
            if name not in attrdict and hasattr(self, name):
                attr = getattr(self, name)
                if hasattr(attr, "_get_attrdict"):
                    attrdict[name] = attr._get_attrdict(extattrs, recursive)
                elif callable(attr):
                    attrdict[name] = attr()
                else:
                    attrdict[name] = attr

    def _get_repr(self, fullname=False, add_params=True):
        return self._impl.get_repr(fullname, add_params)

    @property
    def _evalrepr(self):
        return self._impl.evalrepr

    @property
    def _idtuple(self):
        if self._impl.is_model():
            return (self.name,)
        else:
            return self.parent._idtuple + (self.name,)

    @property
    def _idstr(self):
        return self._impl.idstr

    def _is_valid(self):
        return not isinstance(self._impl, NullImpl)


null_interface = Interface(null_impl)


class LazyEval:
    """Base class for flagging observers so that they update themselves later.

    An object of a class inherited from LazyEvaluation can have its observers.
    When the data of the object is updated, the users call set_refresh method,
    to flag the object's observers.
    When the observers get_updated methods are called later, their data
    contents are updated depending on their update states.
    The updating operation can be customized by overwriting _refresh method.
    """
    __slots__ = ()
    __mixin_slots = ("is_fresh", "observers", "observing")

    update_methods = None

    def __init__(self, observers):
        self.is_fresh = True  # must be read only
        self.observers = []
        self.observing = []
        for observer in observers:
            self.append_observer(observer)

    def set_refresh(self):
        self.is_fresh = False
        for observer in self.observers:
            if observer.is_fresh:
                observer.set_refresh()

    @property
    def fresh(self):
        if not self.is_fresh:
            for other in self.observing:
                other.fresh
            self._refresh()
            self.is_fresh = True
        return self

    def _refresh(self):
        raise NotImplementedError  # To be overwritten in derived classes

    def append_observer(self, observer):
        # Speed deteriorates by a lot if below
        # if observer not in self.observers:
        if all(observer is not other for other in self.observers):
            self.observers.append(observer)
            observer.observing.append(self)
            observer.set_refresh()

    def observe(self, other):
        other.append_observer(self)

    def remove_observer(self, observer):
        self.observers.remove(observer)
        observer.observing.remove(self)

    def unobserve(self, other):
        other.remove_observer(self)

    def on_update(self, method, args=()):
        is_fresh = self.is_fresh
        if not is_fresh:
            self.fresh
        args = self.update_methods[method](self, *args)
        if is_fresh:    # if not fresh, all observers are not fresh too
            for observer in self.observers:
                if observer.is_fresh:
                    observer.on_update(method, args)


def _rename_item(self, old_name, new_name):
    """Rename a key without changing its position.
    """
    keys = list(self.keys())
    i = keys.index(old_name)
    n = len(keys)

    # Remove old_name and append it as new_name
    value = self.pop(old_name)
    dict.__setitem__(self, new_name, value)
    i += 1

    # Remove and append all the items after old_name
    while i < n:
        value = self.pop(keys[i])
        dict.__setitem__(self, keys[i], value)
        i += 1


def _sort_all(self):
    sorted_ = sorted(self.keys())

    # Find i to start replacement
    i = 0
    for name in self:
        if name == sorted_[i]:
            i += 1
        else:
            break

    for j in range(i, len(sorted_)):
        k = sorted_[j]
        self[k] = self.pop(k)


def _sort_partial(self, sorted_keys):
    """Sort a part of a map

    The part to sort in the map must be consecutive

    Example:
        self: {'a':1, 'bb':1, 'aa':1, 'cc':1, 'b':1}
        sorted_keys: ['aa', 'bb', 'cc']
        result: {'a':1, 'aa':1, 'bb':1, 'cc':1, 'b':1}

    """
    i = 0
    i0 = -1  # Start position

    self_keys = list(self.keys())
    for name in self_keys:
        if name in sorted_keys:
            if i0 < 0:
                i0 = i
            if name != sorted_keys[i-i0]:
                break
        i += 1

    sort_len = len(sorted_keys)
    i0 = max(i0, 0)
    while i < i0 + sort_len:
        name = sorted_keys[i-i0]
        self[name] = self.pop(name)
        i += 1

    self_len = len(self_keys)
    while i < self_len:
        name = self_keys[i]
        self[name] = self.pop(name)
        i += 1


class LazyEvalDict(LazyEval, dict):

    __slots__ = ("name", "_repr") + get_mixin_slots(LazyEval, dict)

    def __init__(self, name, data=None, observers=None):

        if data is None:
            data = {}
        if observers is None:
            observers = []

        dict.__init__(self, data)
        LazyEval.__init__(self, observers)
        self.name = name
        self._repr = ""

    def _refresh(self):
        pass

    def _update_item(self, name):
        raise NotImplementedError

    def _rename_item(self, old_name, new_name):
        _rename_item(self, old_name, new_name)
        return old_name, new_name

    def _sort(self, sorted_keys=None):
        if sorted_keys is None:
            _sort_all(self)
        else:
            _sort_partial(self, sorted_keys)

    def set_item(self, name, value):
        dict.__setitem__(self, name, value)
        self.set_refresh()

    def del_item(self, name):
        dict.__delitem__(self, name)
        self.set_refresh()

    def add_item(self, name, value):
        """Adding new item"""
        self.on_add_item(None, name, value)

    def on_add_item(self, sender, name, value):
        dict.__setitem__(self, name, value)
        if self.is_fresh:
            self._update_item(name)
            for observer in self.observers:
                if observer.is_fresh:
                    observer.on_add_item(self, name, value)

    def delete_item(self, name):
        self.on_delete_item(None, name)

    def on_delete_item(self, sender, name):
        dict.__delitem__(self, name)
        if self.is_fresh:
            self._update_item(name)
            for observer in self.observers:
                if observer.is_fresh:
                    observer.on_delete_item(self, name)

    def rename_item(self, old_name, new_name):
        self.on_update("rename", (old_name, new_name))

    def sort_items(self, sort_keys):
        self.on_update("sort", (self, sort_keys))


assert issubclass(LazyEvalDict, Mapping)


class LazyEvalChainMap(LazyEval, CustomChainMap):

    __slots__ = ("name", "_repr") + get_mixin_slots(LazyEval, CustomChainMap)

    def __init__(self, name, maps=None, observers=None):

        if maps is None:
            maps = []
        if observers is None:
            observers = []

        CustomChainMap.__init__(self, *maps)
        LazyEval.__init__(self, observers)
        self.name = name
        self._repr = ""

        for other in maps:
            other.append_observer(self)

    def _refresh(self):
        pass

    def on_add_item(self, sender, name, value):
        if self.is_fresh:
            self._update_item(name)
            map_ = next((m for m in self.maps if name in m), None)
            if map_ is sender:
                for observer in self.observers:
                    if observer.is_fresh:
                        observer.on_add_item(self, name, value)

    def on_delete_item(self, sender, name):
        if self.is_fresh:
            self._update_item(name)
            # map_ = next((m for m in self.maps if name in m), None)
            for observer in self.observers:
                if observer.is_fresh:
                    observer.on_delete_item(self, name)

    def __setitem__(self, name, value):
        raise NotImplementedError

    def __delitem__(self, name):
        raise NotImplementedError


assert issubclass(LazyEvalChainMap, Mapping)


class InterfaceMixin:
    """Mixin to LazyEval to update interface with impl

    _update_interfaces needs to be manually called from _refresh.
    """
    __slots__ = ()
    __mixin_slots = ("_interfaces", "map_class", "interfaces")

    def __init__(self, map_class):
        self._interfaces = dict()
        self.map_class = map_class
        self._set_interfaces(map_class)

    def _set_interfaces(self, map_class):
        if map_class is None:
            self.interfaces = self._interfaces
        elif map_class is dict:
            raise RuntimeError
        else:
            self.interfaces = map_class(self._interfaces, self)

    def _update_interfaces(self):
        self._interfaces.clear()
        self._interfaces.update(get_interfaces(self))

    def _update_item(self, name):
        if name in self:
            self._interfaces[name] = self[name].interface
        else:
            del self._interfaces[name]

    def _rename_item(self, old_name, new_name):
        _rename_item(self._interfaces, old_name, new_name)

    def _sort(self, sorted_keys=None):
        if sorted_keys is None:
            _sort_all(self._interfaces)
        else:
            _sort_partial(self._interfaces, sorted_keys)


bases = InterfaceMixin, LazyEvalDict


class ImplDict(*bases):

    __slots__ = ("owner",) + get_mixin_slots(*bases)

    def __init__(self, name, owner, ifclass, data=None, observers=None):
        self.owner = owner
        InterfaceMixin.__init__(self, ifclass)
        LazyEvalDict.__init__(self, name, data, observers)

    def _refresh(self):
        LazyEvalDict._refresh(self)
        self._update_interfaces()

    def _rename_item(self, old_name, new_name):
        LazyEvalDict._rename_item(self, old_name, new_name)
        InterfaceMixin._rename_item(self, old_name, new_name)
        return old_name, new_name

    def _sort(self, map_, sorted_keys):
        LazyEvalDict._sort(self, sorted_keys)
        InterfaceMixin._sort(self, sorted_keys)
        # Return self to pass it as argt to LazyEvalChainMap observers
        return (self, sorted_keys)

    update_methods = {
        "rename": _rename_item,
        "sort": _sort
    }


bases = InterfaceMixin, LazyEvalChainMap


class ImplChainMap(*bases):

    __slots__ = ("owner", "map_ids") + get_mixin_slots(*bases)

    def __init__(
        self, name, owner, ifclass, maps=None, observers=None,
            map_ids=None
    ):
        self.owner = owner
        self.map_ids = map_ids
        InterfaceMixin.__init__(self, ifclass)
        LazyEvalChainMap.__init__(self, name, maps, observers)

    def _refresh(self):
        LazyEvalChainMap._refresh(self)
        self._update_interfaces()

    def _rename_item(self, old_name, new_name):
        InterfaceMixin._rename_item(self, old_name, new_name)
        return old_name, new_name

    def _sort(self, map_, sorted_keys):
        if isinstance(map_, (LazyEvalDict, LazyEvalChainMap)):
            assert any(map_ is m for m in self.maps)

            if sorted_keys is None:
                prev_keys = map_.keys()
            else:
                prev_keys = sorted_keys

            # Filter out overwritten items
            keys = []
            for name in prev_keys:
                m = next(m for m in self.maps if name in m)
                if m is map_:
                    keys.append(name)
        else:
            raise RuntimeError("must not happen")

        InterfaceMixin._sort(self, keys)
        return (self, keys)

    update_methods = {
        "rename": _rename_item,
        "sort": _sort
    }


class RefChainMap(ImplChainMap):

    def __init__(self, name, owner, ifclass, maps=None, observers=None):
        ImplChainMap.__init__(self, name, owner, ifclass,
            maps=maps, observers=observers)


# The code below is modified from UserDict in Python's standard library.
#
# The original code was taken from the following URL:
#   https://github.com/python/cpython/blob/\
#       7e68790f3db75a893d5dd336e6201a63bc70212b/\
#       Lib/collections/__init__.py#L968-L1027


class BaseView(Mapping):

    # Start by filling-out the abstract methods
    def __init__(self, data, impl):
        self._data = data
        self.impl = impl

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        if key in self._data:
            return self._data[key]
        if hasattr(self.__class__, "__missing__"):
            return self.__class__.__missing__(self, key)
        raise KeyError(key)

    def __iter__(self):
        return iter(self._data)

    # Modify __contains__ to work correctly when __missing__ is present
    def __contains__(self, key):
        return key in self._data

    # Now, add the methods in dicts but not in MutableMapping
    def __repr__(self):
        return repr(self._data)

    # ----------------------------------------------------------------------
    # Override base class methods

    @property
    def _baseattrs(self):
        """A dict of members expressed in literals"""

        result = {"type": type(self).__name__}
        try:
            result["items"] = {
                name: item._baseattrs
                for name, item in self.items()
                if name[0] != "_"
            }
        except:
            raise RuntimeError("%s literadict raised an error" % self)

        return result

    @property
    def _baseattrs_private(self):
        """For spyder-modelx to populate SpaceView for named_itemspace"""

        result = {"type": type(self).__name__}
        try:
            result["items"] = {
                name: item._baseattrs
                for name, item in self.items()
            }
        except:
            raise RuntimeError("%s literadict raised an error" % self)

        return result

    def _to_attrdict(self, attrs=None):
        """Used by spyder-modelx"""

        result = {"type": type(self).__name__}
        try:
            result["items"] = {
                name: item._to_attrdict(attrs) for name, item in self.items()
            }
        except:
            raise RuntimeError("%s literadict raised an error" % self)

        return result

    def _get_attrdict(self, extattrs=None, recursive=True):
        """Get extra attributes"""
        result = {"type": type(self).__name__}
        result["items"] = {
            name: item._get_attrdict(extattrs, recursive)
            for name, item in self.items()
        }
        # To make it possible to detect order change by comparison operation
        result["keys"] = list(self.keys())

        return result


def _map_repr(self):
    result = [",\n "] * (len(self) * 2 - 1)
    result[0::2] = list(self)
    return "{" + "".join(result) + "}"


class SelectedView(BaseView):
    """View to the original mapping but has only selected items.

    A base class for :class:`modelx.core.space.CellsView`.

    Args:
        data: The original mapping object.
        keys: Iterable of selected keys.
    """

    def __init__(self, data, impl, keys=None):
        BaseView.__init__(self, data, impl)
        self._set_keys(keys)

    def __getitem__(self, key):
        if isinstance(key, str):
            return BaseView.__getitem__(self, key)
        if isinstance(key, Sequence):
            return type(self)(self._data, self.impl, key)
        else:
            raise KeyError

    def _set_keys(self, keys=None):

        if keys is None:
            self.__keys = None
        else:
            self.__keys = list(keys)

    def __len__(self):
        return len(list(iter(self)))

    def __iter__(self):
        def newiter():
            for key in self.__keys:
                if key in self._data:
                    yield key

        if self.__keys is None:
            return BaseView.__iter__(self)
        else:
            return newiter()

    def __contains__(self, key):
        return key in iter(self)

    __repr__ = _map_repr


