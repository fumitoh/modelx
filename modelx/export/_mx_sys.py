import sys
import collections
import threading
import pickle
from importlib import import_module
import pathlib
from collections import OrderedDict
from typing import Dict
try:
    has_io = True
    from . import _mx_io
except ImportError:
    has_io = False


class BaseMxObject:

    __slots__ = ()


class _CollectLock:
    """Model lock with an ownership query using public lock operations."""

    __slots__ = ('_lock', '_owner')

    def __init__(self):
        self._lock = threading.RLock()
        self._owner = threading.local()

    def __enter__(self):
        depth = getattr(self._owner, 'depth', 0)
        self._lock.acquire()
        try:
            self._owner.depth = depth + 1
        except BaseException:
            self._lock.release()
            raise

    def __exit__(self, *exc):
        try:
            self._owner.depth -= 1
        finally:
            self._lock.release()

    def held_by_current_thread(self):
        return getattr(self._owner, 'depth', 0) != 0


class BaseParent(BaseMxObject):

    # Annotations only: they create no class attributes and so never
    # conflict with the __slots__ of a subclass.
    __slots__ = ()

    _mx_spaces: Dict[str, 'BaseSpace']
    _parent: 'BaseParent'
    _model: 'BaseModel'
    _name: str

    def _mx_walk(self, skip_self: bool = False):
        """Generator yielding spaces in breadth-first order"""
        if skip_self:
            que = collections.deque(self._mx_spaces.values())
        else:
            que = collections.deque([self])
        while que:
            parent = que.popleft()
            yield parent
            for child in parent._mx_spaces.values():
                que.append(child)

    def _mx_assign_refs(self, io_data, pickle_data):
        raise NotImplementedError


class BaseModel(BaseParent):

    path = pathlib.Path(__file__).parent

    def _mx_collect_init_v2(self):
        self._mx_collect_dispatch_state = threading.local()

    @property
    def collect_workers(self):
        """Number of worker threads ``collect()`` may use, or None for the default (``Model.collect_workers``
        of live modelx): the ``parallel_workers`` a compiled model was built with, else 1. Workers run in
        parallel only on a free-threaded build; with the GIL, collect evaluates serially."""
        return getattr(self, '_mx_collect_workers_override', None)

    @collect_workers.setter
    def collect_workers(self, workers):
        if workers is not None and (type(workers) is not int or workers < 1):
            raise ValueError('collect_workers must be None or a positive integer')
        self._mx_collect_workers_override = workers

    def _mx_collect_set_workers_v2(self, workers):
        # export protocol 2: the name packages built before ``collect_workers`` use
        if type(workers) is not int or workers < 1:
            raise ValueError('collect workers must be a positive integer')
        self._mx_collect_workers_override = workers

    def _mx_load_io(self):

        ios = {}
        io_data = {}
        if has_io:
            for k, v in _mx_io.ios.items():
                cls = io_types[v['type']]
                load_from = self.path / k
                ios[k] = cls(k, load_from, v)

            for k, v in _mx_io.iospecs.items():
                cls = iospec_types[v['type']]
                io_data[k] = cls(ios[v['io']], v['kwargs']).load_value()

        p = self.path / '_mx_pickled'
        if p.exists():
            with open(p, mode='rb') as f:
                pickle_data = pickle.load(f)
        else:
            pickle_data = {}

        for m_or_s in self._mx_walk():
            m_or_s._mx_assign_refs(io_data, pickle_data)


class BaseSpace(BaseParent):

    # Subclasses generated with use_slots=False declare no __slots__ of
    # their own and so still get a __dict__, exactly as before.
    __slots__ = ()

    # Instance variables
    _mx_is_cells_set: bool
    _mx_cells: dict

    @property
    def _cells(self):
        if not self._mx_is_cells_set:
            for name in getattr(sys.modules[self.__class__.__module__],
                                "_v_cells_names_" + self._name):
                self._mx_cells[name] = getattr(self, name)
            self._mx_is_cells_set = True

        return self._mx_cells


    def _mx_is_in(self, parent: BaseParent):
        p = self
        while True:
            if p is parent:
                return True
            elif p is None:
                return False
            else:
                p = p._parent


    def _mx_get_object(self, keys):
        obj = self
        for name in keys:
            if name[0] == ".":
                for _ in name[1:]:
                    obj = obj._parent
            else:
                obj = getattr(obj, name)

        return obj


class CollectResult:
    """Detached values returned by an exported collect-enabled Space."""

    __slots__ = ('_fields',)

    def __init__(self, fields):
        self._fields = fields

    def __getattr__(self, name):
        try:
            return self._fields[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(self._fields))

    def __repr__(self):
        return 'CollectResult(%s)' % ', '.join(self._fields)


_mx_collect_adapter_version = 2
# Protocol 2 extension: a compiled evaluator may take the collect's other Space parameters
# (``_mx_collect_options_v2()`` returns a fifth element, True).
_mx_collect_evaluator_args = True


def _mx_collect_state(base):
    return base._model._mx_collect_dispatch_state


def _mx_collect_native_coords(coords):
    return all(type(coord) is int and -(1 << 63) <= coord < (1 << 63) for coord in coords)


def collect_from_space(base, domain, loop_name, names, args, cache=None, evaluate=None,
                       evaluate_serial=None, reuse_in_parallel=False, private_ordered=False):
    """Evaluate an exported collection without retaining policy ItemSpaces."""

    if len(names) != len(args) or loop_name in names:
        raise ValueError('invalid collect arguments')
    from ._mx_collect_semantics import normalize_domain

    coords = normalize_domain(domain)
    key = (coords, args)
    if cache is not None:
        try:
            hash(key)
        except TypeError:
            cache = None
        else:
            found = cache.get(key)
            if found is not None:
                return found

    context = _mx_collect_state(base)
    workers = 1
    options = getattr(base, '_mx_collect_options_v2', None)
    if options is not None:
        options = options()
        workers, evaluate_serial, reuse_in_parallel, private_ordered = options[:4]
        if len(options) > 4 and options[4] and evaluate_serial is not None:
            evaluator = evaluate_serial
            def evaluate_serial(coords):        # the evaluator of this call's other parameters
                return evaluator(coords, args)
    override = getattr(base._model, '_mx_collect_workers_override', None)
    if override is not None:
        workers = override
    if workers > 1 and getattr(sys, '_is_gil_enabled', lambda: True)():
        workers = 1         # with the GIL, threads cannot evaluate model code at the same time
    if workers > len(coords):
        workers = max(1, len(coords))   # one item: the serial path (the evaluator, no thread pool)

    if (evaluate_serial is not None and workers == 1
            and not getattr(context, 'active', False)
            and sys.gettrace() is None and sys.getprofile() is None):
        context.active = True
        try:
            result = evaluate_serial(coords)
        finally:
            context.active = False
        if result is not None:
            return result if cache is None else cache.setdefault(key, result)
    if evaluate is None:
        can_parallel = getattr(base._model, '_mx_collect_parallel_allowed', None)
        # A shared Cell may call collect while holding the model lock. Keep
        # that nested calculation on the owning thread to avoid a lock wait cycle.
        if (workers > 1 and len(coords) > 1
                and not getattr(context, 'active', False)
                and (can_parallel is None or can_parallel())):
            private = None
            if (reuse_in_parallel and evaluate_serial is not None
                    and sys.gettrace() is None and sys.getprofile() is None
                    and _mx_collect_native_coords(coords)):
                private = evaluate_serial
            result = _mx_collect_parallel(base, coords, loop_name, names, args, private, private_ordered, workers)
        else:
            active = getattr(context, 'active', False)
            context.active = True
            try:
                result = _mx_collect_evaluate(base, coords, loop_name, names, args)
            finally:
                context.active = active
    else:
        result = evaluate()
    return result if cache is None else cache.setdefault(key, result)


def _mx_collect_parallel(base, coords, loop_name, names, args, private, private_ordered, workers):
    from concurrent.futures import ThreadPoolExecutor

    workers = min(workers, len(coords))
    if private is None:
        return _mx_collect_ordered(base, coords, loop_name, names, args, workers)
    from ._mx_collect_semantics import _add, _check_shape, _shape

    chunks = [coords[i * len(coords) // workers:(i + 1) * len(coords) // workers]
              for i in range(workers)]
    result = None
    individual_shape = None
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_mx_collect_chunk, base, chunk, loop_name, names, args, private)
                   for chunk in chunks]
        # Only private scalar chunks may merge in completion order.
        ordered_futures = futures
        if private is not None and not private_ordered:
            from concurrent.futures import as_completed
            futures = as_completed(futures)
        for future in futures:
            if private is not None and future.exception() is not None:
                # Keep successful scalar merging in completion order, but
                # propagate the first failure in original domain order.
                for ordered_future in ordered_futures:
                    ordered_future.result()
            fields = future.result()._fields
            if result is None:
                modes = tuple(fields)
                result = {mode: OrderedDict() if mode == 'individual' else None for mode in modes}
            elif tuple(fields) != modes:
                raise ValueError('collect_outputs modes changed between policies')
            for mode, values in fields.items():
                if mode == 'individual':
                    for coordinate, item in values.items():
                        if individual_shape is None:
                            individual_shape = _shape(item._fields)
                        else:
                            _check_shape(individual_shape, item._fields, (mode,))
                        result[mode][coordinate] = item
                else:
                    current = result[mode]
                    result[mode] = values._fields if current is None else _add(current, values._fields, (mode,))
    return CollectResult({mode: value if mode == 'individual' else CollectResult(value)
                          for mode, value in result.items()})


def _mx_collect_chunk(base, coords, loop_name, names, args, private=None):
    context = _mx_collect_state(base)
    active = getattr(context, 'active', False)
    context.active = True
    try:
        if private is not None:
            result = private(coords)
            if result is not None:
                return result
        return _mx_collect_evaluate(base, coords, loop_name, names, args)
    finally:
        context.active = active


def _mx_collect_batch(base, coords, loop_name, names, args):
    events = []
    context = _mx_collect_state(base)
    active = getattr(context, 'active', False)
    context.active = True
    try:
        events.extend(_mx_collect_policy_outputs(base, coords, loop_name, names, args))
    except BaseException as error:
        return events, error
    finally:
        context.active = active
    return events, None


def _mx_collect_ordered(base, coords, loop_name, names, args, workers):
    from concurrent.futures import ThreadPoolExecutor
    from itertools import islice
    from ._mx_collect_semantics import Accumulator

    # Bound unmerged output by keeping at most one small batch per worker.
    size = max(1, min(8, len(coords) // workers))
    starts = iter(range(0, len(coords), size))
    accumulator = Accumulator(CollectResult)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        def submit(start):
            return executor.submit(_mx_collect_batch, base, coords[start:start + size],
                                   loop_name, names, args)

        pending = collections.deque(submit(start) for start in islice(starts, workers))
        while pending:
            events, error = pending.popleft().result()
            for coordinate, outputs in events:
                accumulator.add(coordinate, outputs)
            if error is not None:
                raise error
            start = next(starts, None)
            if start is not None:
                pending.append(submit(start))
    return accumulator.result()


def _mx_collect_evaluate(base, coords, loop_name, names, args):
    from contextlib import closing
    from ._mx_collect_semantics import Accumulator

    accumulator = Accumulator(CollectResult)
    with closing(_mx_collect_policy_outputs(base, coords, loop_name, names, args)) as events:
        for coordinate, outputs in events:
            accumulator.add(coordinate, outputs)
    return accumulator.result()


def _mx_collect_policy_outputs(base, coords, loop_name, names, args):
    from ._mx_collect_semantics import prepare_output

    scratch = {}
    # A compiled class may offer the construction and release its own collect evaluator and items use
    # (modelx-cython D116): the root is then built and freed the same way on every collect path.
    shared_root = getattr(base, '_mx_collect_new_root', None)
    try:
        for coordinate in coords:
            values = dict(zip(names, args))
            values[loop_name] = coordinate
            root = shared_root() if shared_root is not None else None
            shared = root is not None
            releases = []
            complete = False
            try:
                if shared:
                    base._mx_assign_params(root, **values)
                    spaces = [(root, base)]
                else:
                    root = base.__class__(base)
                    spaces = list(zip(root._mx_walk(), base._mx_walk()))
                    for space, template in spaces:
                        space._mx_copy_refs(template, base)
                        for previous_root in base._mx_roots:
                            previous_root._mx_copy_params(space)
                        base._mx_assign_params(space, **values)
                        space._mx_roots.extend(base._mx_roots)
                        space._mx_roots.append(root)
                apply_formula = getattr(root, '_mx_apply_formula', None)
                if apply_formula is not None:
                    apply_formula(**values)
                for space, template in spaces:
                    release = getattr(space, '_mx_collect_release', None)
                    if release is not None:
                        releases.append((release, template))
                    attach = getattr(space, '_mx_collect_attach', None)
                    if attach is not None:
                        attach(scratch, template)
                outputs = prepare_output(root.collect_outputs(), (BaseMxObject,))
                complete = True
            finally:
                cleanup_error = None
                for release, template in releases:
                    try:
                        release(scratch, template)
                    except BaseException as error:
                        if cleanup_error is None:
                            cleanup_error = error
                if not complete or cleanup_error is not None:
                    scratch.clear()
                if shared:
                    base._mx_collect_release_root(root)
                if complete and cleanup_error is not None:
                    raise cleanup_error
            del root
            yield coordinate, outputs
    finally:
        scratch.clear()


class MiniBaseSharedIO:

    def __init__(self, path, load_from, kwargs):
        self.path = path
        self.load_from = load_from
        self.kwargs = kwargs

    def __getattr__(self, item):
        return self.kwargs[item]

    def load_io(self, root):
        raise NotImplementedError


class MiniBaseIOSpec:

    def __init__(self, io, kwargs):
        self._io = io
        self.kwargs = kwargs

    def load_value(self):
        raise NotImplementedError


class MiniPandasIO(MiniBaseSharedIO):

    def load_io(self, root):
        pass


class MiniPandasData(MiniBaseIOSpec):

    def load_value(self):
        self._on_unserialize(self.kwargs)
        return self._value

    def _on_unserialize(self, state):
        if self._io.file_type is None:
            self._io.file_type = state["filetype"]
        self._read_args = state["read_args"]
        if "squeeze" in state:
            self._squeeze = state["squeeze"]
        elif "squeeze" in self._read_args:
            self._squeeze = self._read_args.pop("squeeze")
        else:
            self._squeeze = False
        self.name = state["name"]
        self._sheet = state["sheet"] if "sheet" in state else None
        self._read_pandas()

    def _read_pandas(self):
        import pandas as pd

        if self._io.file_type == "excel":
            self._value = pd.read_excel(
                self._io.load_from, **self._read_args)
        elif self._io.file_type == "csv":
            self._value = pd.read_csv(
                self._io.load_from, **self._read_args)
        else:
            raise ValueError

        if self._squeeze:
            self._value = self._value.squeeze("columns")

        if isinstance(self._value, pd.Series):
            self._value.name = self.name

        if hasattr(self, "_is_hidden") and self._is_hidden:
            self._value._mx_dataclient = self


io_types = {
    'PandasIO': MiniPandasIO
}


iospec_types = {
    'PandasData': MiniPandasData
}

