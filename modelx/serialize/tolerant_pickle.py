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

"""Error-tolerant unpicklers for reading pickle files in saved models.

When objects in "_data/data.pickle" or "_data/iospecs.pickle" cannot be
unpickled in the current environment (e.g. because the packages they were
pickled with have changed), the unpicklers here substitute placeholders for
the broken objects instead of aborting, so that the rest of the model can
still be loaded. Objects assembled from broken parts are contaminated
transitively, opcode by opcode, so that e.g. a DataFrame whose internal
blocks failed to load is discarded as a whole even when its __setstate__
swallows the placeholders without raising. After loading,
``sweep_pickledata`` replaces every entry whose value is or contains a
broken object with None and reports the entry's key, so the readers can
warn the user and skip or nullify only the affected values.

The pure-Python ``pickle._Unpickler`` executes most opcodes through the
class-level ``dispatch`` dict, so the error-trapping handlers must be wired
into a copy of that dict; only ``find_class`` and ``persistent_load`` can be
overridden as regular methods.
"""

import copy
import pickle
import warnings

from . import ziputil
from .custom_pickle import ModelUnpickler, IOSpecUnpickler

try:
    from .pandas_compat import CompatBase as _CompatBase
except ImportError:     # pandas not installed
    _CompatBase = pickle._Unpickler


def _noop(*args, **kwargs):
    return None


class ErrorPlaceholder:
    """Stand-in pushed on the unpickling stack for objects that failed to load.

    Tolerates the operations pickle may perform on it afterwards, so that
    the rest of the stream keeps parsing. ``__call__``, ``__setitem__`` and
    ``__new__`` must be real methods because pickle reaches them through
    implicit type-level lookup (``__new__`` explicitly so, rather than via
    object.__new__'s leniency when only __init__ is overridden); the
    remaining operations (append, extend, add, update, __setstate__, ...)
    are explicit attribute accesses covered by ``__getattr__``.
    """

    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self

    def __setitem__(self, key, value):
        pass

    def __getattr__(self, name):
        return _noop


def _substitute_top(unpickler, exc):
    if exc is not None:
        unpickler._record(exc)
    unpickler.stack[-1] = ErrorPlaceholder()


def _append_placeholder(unpickler, exc):
    if exc is not None:
        unpickler._record(exc)
    unpickler.append(ErrorPlaceholder())


def _contaminate_top(unpickler, exc):
    # The object is memoized before BUILD and container fills run, so it
    # must stay on the stack; record its identity instead of replacing it.
    if exc is not None:
        unpickler._record(exc)
    obj = unpickler.stack[-1]
    unpickler.contaminated[id(obj)] = obj   # value kept alive so id stays valid


class _TolerantUnpickler(_CompatBase):
    """Unpickler that substitutes placeholders for objects that fail to load."""

    def __init__(self, file, reader):
        super().__init__(file)
        self.reader = reader
        self.manager = reader.system.iomanager
        self.model = reader.model
        if reader.version >= 5:
            self.iospecs = reader.iospecs
        self.errors = []
        self.contaminated = {}      # id -> object built from broken parts

    def _record(self, exc):
        self.errors.append(exc)

    def _is_bad(self, obj):
        return (obj is ErrorPlaceholder
                or isinstance(obj, ErrorPlaceholder)
                or id(obj) in self.contaminated)

    def find_class(self, module, name):
        try:
            return super().find_class(module, name)
        except Exception as exc:
            self._record(exc)
            return ErrorPlaceholder

    def persistent_load(self, pid):
        try:
            return self._persistent_load(pid)
        except Exception as exc:
            self._record(exc)
            return ErrorPlaceholder()


# Contamination is propagated per opcode with O(1) membership checks on the
# operands: every aggregate an opcode builds or fills is checked against the
# elements it consumes, so containment never requires re-scanning whole
# structures during the load (a deep scan happens once, in sweep_pickledata).

def _peek_top(u):
    return u._is_bad(u.stack[-1])


def _peek_top2(u):
    return u._is_bad(u.stack[-1]) or u._is_bad(u.stack[-2])


def _peek_top3(u):
    return any(map(u._is_bad, u.stack[-3:]))


def _peek_mark(u):
    # At a mark-based opcode, self.stack is exactly the mark segment
    return any(map(u._is_bad, u.stack))


def _make_tolerant_dispatch(cls):
    """Copy ``cls.dispatch`` and wrap the handlers that can run user code
    or aggregate previously loaded objects.

    Each wrapper substitutes a placeholder (or contaminates the built
    object) when the wrapped handler raises, and also when the handler
    succeeds but its operands were broken (``peek`` inspects the operands
    on the stack before the handler pops them; ``taint`` marks the result
    afterwards).
    """

    cls.dispatch = copy.copy(cls.dispatch)

    def wrap(code, fixup=None, peek=None, taint=None):
        inner = cls.dispatch.get(code[0])
        if inner is None:
            return

        def handler(self, _inner=inner, _fixup=fixup, _peek=peek,
                    _taint=taint):
            if _peek is not None and self.errors:
                tainted = _peek(self)
            else:
                tainted = False
            if _fixup is None:
                _inner(self)
            else:
                try:
                    _inner(self)
                except Exception as exc:
                    _fixup(self, exc)
                    return
            if tainted:
                _taint(self, None)

        cls.dispatch[code[0]] = handler

    # Object construction: on failure or broken operands the result is a
    # placeholder (the failed/tainted result was never inserted anywhere yet)
    wrap(pickle.REDUCE, _substitute_top, _peek_top, _substitute_top)
    wrap(pickle.NEWOBJ, _append_placeholder, _peek_top, _substitute_top)
    wrap(pickle.NEWOBJ_EX, _append_placeholder, _peek_top2, _substitute_top)
    wrap(pickle.INST, _append_placeholder, _peek_mark, _substitute_top)
    wrap(pickle.OBJ, _append_placeholder, _peek_mark, _substitute_top)
    for code in (pickle.EXT1, pickle.EXT2, pickle.EXT4):
        wrap(code, _append_placeholder)

    # State/content mutation of an already-memoized object: keep the object
    # and contaminate it
    wrap(pickle.BUILD, _contaminate_top, _peek_top, _contaminate_top)
    wrap(pickle.SETITEM, _contaminate_top, _peek_top2, _contaminate_top)
    wrap(pickle.APPEND, _contaminate_top, _peek_top, _contaminate_top)
    for code in (pickle.SETITEMS, pickle.APPENDS, pickle.ADDITEMS):
        wrap(code, _contaminate_top, _peek_mark, _contaminate_top)

    # Builtin containers built from loaded elements: can only fail on
    # element hashing (DICT/FROZENSET); all propagate contamination
    wrap(pickle.DICT, _append_placeholder, _peek_mark, _contaminate_top)
    wrap(pickle.FROZENSET, _append_placeholder, _peek_mark, _contaminate_top)
    wrap(pickle.TUPLE, None, _peek_mark, _contaminate_top)
    wrap(pickle.LIST, None, _peek_mark, _contaminate_top)
    wrap(pickle.TUPLE1, None, _peek_top, _contaminate_top)
    wrap(pickle.TUPLE2, None, _peek_top2, _contaminate_top)
    wrap(pickle.TUPLE3, None, _peek_top3, _contaminate_top)


class TolerantModelUnpickler(_TolerantUnpickler):
    """Tolerant substitute for ModelUnpickler (reads _data/data.pickle)"""

    _persistent_load = ModelUnpickler.persistent_load
    _find_iospec = ModelUnpickler._find_iospec


class TolerantIOSpecUnpickler(_TolerantUnpickler):
    """Tolerant substitute for IOSpecUnpickler (reads _data/iospecs.pickle)"""

    _persistent_load = IOSpecUnpickler.persistent_load


_make_tolerant_dispatch(TolerantModelUnpickler)
_make_tolerant_dispatch(TolerantIOSpecUnpickler)


def _contains_error(value, contaminated):

    if (value is ErrorPlaceholder or isinstance(value, ErrorPlaceholder)
            or id(value) in contaminated):
        return True
    if not isinstance(value, (list, tuple, dict, set, frozenset)):
        return False

    # Deep scan of builtin containers: contamination tracking covers
    # aggregates the unpickler built, but cyclic or reordered fills can
    # bury a broken object without contaminating every ancestor
    seen = set()
    stack = [value]
    while stack:
        obj = stack.pop()
        if (obj is ErrorPlaceholder or isinstance(obj, ErrorPlaceholder)
                or id(obj) in contaminated):
            return True
        if isinstance(obj, (list, tuple, set, frozenset)):
            if id(obj) not in seen:
                seen.add(id(obj))
                stack.extend(obj)
        elif isinstance(obj, dict):
            if id(obj) not in seen:
                seen.add(id(obj))
                stack.extend(obj.keys())
                stack.extend(obj.values())
    return False


def sweep_pickledata(data, contaminated=()):
    """Replace dict entries holding unrestorable objects with None.

    Returns the set of keys whose values were replaced.
    """
    error_keys = set()
    for key, value in data.items():
        if _contains_error(value, contaminated):
            data[key] = None
            error_keys.add(key)
    return error_keys


def load_pickle_tolerantly(reader, path, kind):
    """Load a pickle file substituting None for unrestorable values.

    ``kind`` is "model" for _data/data.pickle or "iospecs" for
    _data/iospecs.pickle. Records caught errors and the affected entries'
    keys on the reader. Returns an empty dict if the file cannot be parsed
    at all (e.g. a truncated stream).
    """
    manager = reader.system.iomanager

    if kind == "iospecs" or reader.version < 5:
        # The aborted strict attempt may have registered IOs and attached
        # specs (from iospecs.pickle, or from data.pickle in v4 models
        # where specs are pickled by value); discard them before retrying,
        # including specs attached to absolute-path IOs, whose stale
        # presence would veto the retried specs and null their refs
        manager.rollback_journal(reader.io_journal_mark, io_group=reader.model)

    cls = TolerantModelUnpickler if kind == "model" else TolerantIOSpecUnpickler
    unpickler = None

    def loadfunc(file):
        nonlocal unpickler
        unpickler = cls(file, reader)
        return unpickler.load()

    mark = manager.journal_mark()
    try:
        data = ziputil.read_file_utf8(loadfunc, path, "b")
        if not isinstance(data, dict):
            raise TypeError("unexpected data in '%s': %r" % (path, data))
    except Exception as exc:
        # The whole file's values are lost; ios/specs the aborted
        # tolerant attempt registered would otherwise outlive the read
        # (their refs load as None, so nothing else removes them)
        manager.rollback_journal(mark, io_group=reader.model)
        reader.unpickle_errors.append(exc)
        warnings.warn(
            "'%s' could not be read (%r); "
            "all values stored in it are lost" % (path, exc))
        return {}

    reader.unpickle_errors.extend(unpickler.errors)
    reader.error_ids.update(
        sweep_pickledata(data, unpickler.contaminated))
    return data


def finalize_tolerant_read(reader):
    """Post-process a read that recorded unpickling errors: warn a summary
    of all recorded errors and remove IOs left with no specs by failed
    spec loads."""
    excs = []
    seen = set()
    for exc in reader.unpickle_errors:
        r = repr(exc)
        if r not in seen:
            seen.add(r)
            excs.append(r)
    shown = "; ".join(excs[:5])
    if len(excs) > 5:
        shown += "; and %d more" % (len(excs) - 5)
    warnings.warn(
        "%d error(s) occurred while restoring pickled values in model '%s'; "
        "the affected values are replaced with None or skipped: %s"
        % (len(reader.unpickle_errors), reader.model.name, shown))

    delete_orphan_ios(reader)


def delete_orphan_ios(reader):
    """Remove IOs left with no specs by failed spec loads."""
    manager = reader.system.iomanager
    ios = list(manager.get_ios(reader.model).values())
    ios.extend(manager.get_ios(None).values())     # absolute-path IOs
    for io_ in ios:
        if not io_.specs:
            manager._del_io(io_)
