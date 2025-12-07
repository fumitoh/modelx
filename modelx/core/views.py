from typing import Mapping, Sequence
from modelx.core.base import Impl
from modelx.core.execution.trace import tuplize_key
from modelx.core.cells import shareable_parameters
from modelx.core.reference import ReferenceProxy


def _to_frame_inner(cellsiter, args):

    from modelx.io.pandas import cellsiter_to_dataframe

    if len(args) == 1:
        if isinstance(args[0], Sequence) and len(args[0]) == 0:
            pass  # Empty sequence
        else:
            args = args[0]

    if len(args) and shareable_parameters(cellsiter) is None:
        raise RuntimeError("Parameters not shared")

    argkeys = []
    for arg in args:
        for cells in cellsiter.values():

            newarg = tuplize_key(cells, arg, remove_extra=True)
            cells.get_value(newarg)
            arg = tuplize_key(cells, arg, remove_extra=False)

            if arg not in argkeys:
                argkeys.append(arg)

    return cellsiter_to_dataframe(cellsiter, argkeys)


# The code below is modified from UserDict in Python's standard library.
#
# The original code was taken from the following URL:
#   https://github.com/python/cpython/blob/\
#       7e68790f3db75a893d5dd336e6201a63bc70212b/\
#       Lib/collections/__init__.py#L968-L1027


class BaseView(Mapping):

    # Start by filling-out the abstract methods
    def __init__(self, impls: Mapping[str, Impl]):
        self._impls = impls

    def __len__(self):
        return len(self._impls)

    def __getitem__(self, key):
        if isinstance(key, str):
            if key in self._impls:
                return self._impls[key].interface
            if hasattr(self.__class__, "__missing__"):
                return self.__class__.__missing__(self, key)
        elif isinstance(key, Sequence):
            return self.__class__(self._impls, key)
        raise KeyError(key)

    def __iter__(self):
        return iter(self._impls)

    # Modify __contains__ to work correctly when __missing__ is present
    def __contains__(self, key):
        return key in self._impls

    # Now, add the methods in dicts but not in MutableMapping
    def __repr__(self):
        return repr(self._impls)

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


class SelectedView(BaseView):
    """View to the original mapping but has only selected items.

    A base class for :class:`modelx.core.space.CellsView`.

    Args:
        data: The original mapping object.
        keys: Iterable of selected keys.
    """

    def __init__(self, data, keys=None):
        BaseView.__init__(self, data)
        self._set_keys(keys)

    def __getitem__(self, key):
        if isinstance(key, str):
            return BaseView.__getitem__(self, key)
        elif isinstance(key, Sequence):
            return type(self)(self._impls, key)
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
                if key in self._impls:
                    yield key

        if self.__keys is None:
            return BaseView.__iter__(self)
        else:
            return newiter()

    def __contains__(self, key):
        return key in iter(self)

    def __repr__(self):
        result = [",\n "] * (len(self) * 2 - 1)
        result[0::2] = list(self)
        return "{" + "".join(result) + "}"


class CellsView(SelectedView):

    def __delitem__(self, key):
        cells = self._impls[key]
        cells.spmgr.del_cells(cells.parent, key)


    def to_frame(self, *args):
        """Convert the cells in the view into a DataFrame object.

        If ``args`` is not given, this method returns a DataFrame that
        has an Index or a MultiIndex depending of the number of
        cells parameters and columns each of which corresponds to each
        cells included in the view.

        ``args`` can be given to calculate cells values and limit the
        DataFrame indexes to the given arguments.

        The cells in this view may have different number of parameters,
        but parameters shared among multiple cells
        must appear in the same position in all the parameter lists.
        For example,
        Having ``foo()``, ``bar(x)`` and ``baz(x, y=1)`` is okay
        because the shared parameter ``x`` is always the first parameter,
        but this method does not work if the view has ``quz(x, z=2, y=1)``
        cells in addition to the first three cells, because ``y`` appears
        in different positions.

        Args:
            args(optional): multiple arguments,
               or an iterator of arguments to the cells.
        """
        return _to_frame_inner(self._impls, args)


class SpaceView(BaseView):
    """A mapping of space names to space objects."""

    def __delitem__(self, name):
        space = self._impls[name]
        # space.parent.del_space(name)
        space.model.updater.del_defined_space(space)


class MacroView(BaseView):
    """A mapping of macro names to macro objects."""
    
    def __delitem__(self, name):
        macro = self._impls[name]
        macro.parent.del_macro(name)


class RefView(BaseView):

    @property
    def _baseattrs(self):

        result = {"type": type(self).__name__}

        result["items"] = items = {}
        for name, item in self.items():
            if name[0] != "_":
                items[name] = ReferenceProxy(self._impls[name])._baseattrs

        return result

    def _get_attrdict(self, extattrs=None, recursive=True):

        result = {"type": type(self).__name__}
        result["items"] = items = {}

        for name, item in self.items():
            if name[0] != "_":
                items[name] = ReferenceProxy(
                    self._impls[name])._get_attrdict(extattrs, recursive)

        return result