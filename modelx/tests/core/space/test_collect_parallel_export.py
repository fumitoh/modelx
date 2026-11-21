from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
import sys
import threading
import time
from types import SimpleNamespace

import modelx as mx
import pytest


@pytest.fixture(autouse=True)
def free_threaded(monkeypatch):
    # These tests exercise the parallel paths; on a GIL build collect would clamp to one worker.
    monkeypatch.setattr(sys, '_is_gil_enabled', lambda: False, raising=False)


@pytest.mark.parametrize('workers,ordered,expected', [(1, False, 10.0), (4, False, 8.0), (4, True, 9.0)])
def test_optional_native_adapter_order_cache_and_retry(monkeypatch, workers, ordered, expected):
    from concurrent import futures
    from modelx.export import _mx_sys as runtime
    assert runtime._mx_collect_adapter_version == 2
    monkeypatch.setattr(futures, 'as_completed', lambda tasks: (tasks[i] for i in (2, 0, 1, 3)))
    values = (1e16, 1.0, -1e16, 1.0, 2.0, 3.0, 4.0, -0.0)
    base = SimpleNamespace(_model=SimpleNamespace())
    runtime.BaseModel._mx_collect_init_v2(base._model)
    runtime.BaseModel._mx_collect_set_workers_v2(base._model, workers)
    failure = LookupError('retry')
    failing = True
    def evaluate(coords):
        if failing:
            raise failure
        total = values[coords[0]]
        for index in coords[1:]:
            total += values[index]
        return runtime.CollectResult({'sum': runtime.CollectResult({'value': total})})
    cache = {}
    def collect():
        return runtime.collect_from_space(base, range(8), 'key', (), (), cache=cache,
            evaluate_serial=evaluate, reuse_in_parallel=True, private_ordered=ordered)
    with pytest.raises(LookupError) as error:
        collect()
    assert error.value is failure and not cache
    assert not getattr(base._model._mx_collect_dispatch_state, 'active', False)
    failing = False
    result = collect()
    assert result.sum.value == expected
    assert collect() is result


def test_v2_dispatch_is_isolated_across_models_and_threads():
    from modelx.export import _mx_sys as runtime

    models = (SimpleNamespace(), SimpleNamespace())
    for model, workers in zip(models, (1, 4)):
        runtime.BaseModel._mx_collect_init_v2(model)
        runtime.BaseModel._mx_collect_set_workers_v2(model, workers)
    bases = tuple(SimpleNamespace(_model=model) for model in models)
    rendezvous = threading.Barrier(2)
    serial_cache = {}
    failure = LookupError('serial retry')

    def total(coords):
        return runtime.CollectResult({'sum': runtime.CollectResult({'value': sum(coords)})})

    def evaluate_parallel_chunk(coords):
        assert len(coords) == 2
        assert models[1]._mx_collect_dispatch_state.active
        assert not getattr(models[0]._mx_collect_dispatch_state, 'active', False)
        return total(coords)

    def evaluate_serial(coords):
        assert models[0]._mx_collect_dispatch_state.active
        assert not getattr(models[1]._mx_collect_dispatch_state, 'active', False)
        rendezvous.wait(timeout=10)
        raise failure

    def collect_serial():
        with pytest.raises(LookupError) as error:
            runtime.collect_from_space(bases[0], range(8), 'key', (), (), cache=serial_cache,
                                       evaluate_serial=evaluate_serial)
        assert error.value is failure
        assert not serial_cache
        assert not models[0]._mx_collect_dispatch_state.active
        return runtime.collect_from_space(bases[0], range(8), 'key', (), (), cache=serial_cache,
                                          evaluate_serial=total)

    def collect_parallel():
        rendezvous.wait(timeout=10)
        return runtime.collect_from_space(bases[1], range(8), 'key', (), (),
                                          evaluate_serial=evaluate_parallel_chunk,
                                          reuse_in_parallel=True, private_ordered=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        serial, parallel = pool.submit(collect_serial), pool.submit(collect_parallel)
        assert serial.result(timeout=15).sum.value == 28
        assert parallel.result(timeout=15).sum.value == 28


@pytest.mark.parametrize('workers', [1, 2, 4])
def test_exported_parallel_collect_order_retry_and_shared_lock(tmp_path, monkeypatch, workers):
    name = 'parallel_collect_export'
    model = mx.new_model('ParallelCollect')
    keys = (7, 3, 9, 2, 11, 4, 6, 8)
    try:
        table = model.new_space('Shared', refs={'callback': abs})
        table.new_cells('value', 'lambda: callback(10)')
        policies = model.new_space(
            'Policies', formula='lambda key: {"refs": {"opening": Shared.value()}}',
            refs={'keys': keys, 'Shared': table, 'callback': abs},
            collect_over={'key': keys},
            collect_outputs='lambda: {"individual": {"state": [value()]}, '
                            '"sum": {"value": value(), "series": {0: value()}}}',
        )
        policies.new_cells('value', 'lambda: opening + callback(key)')
        caller = model.new_space('Caller', refs={'Policies': policies})
        caller.new_cells('total', 'lambda: Policies.collect().sum.value')
        model.export(tmp_path / name, locked_spaces=['Shared', 'Caller'])
    finally:
        model.close()
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        package = import_module(name)
        package.mx_model.collect_workers = workers
        policies = package.mx_model.Policies
        shared_calls = []
        package.mx_model.Shared.callback = lambda n: shared_calls.append(n) or n
        active = set()
        lock = threading.Lock()
        failing = True
        def callback(key):
            with lock:
                active.add(key)
            try:
                if failing and key in (7, 9):
                    if key == 7:
                        time.sleep(0.02)
                    raise LookupError(key)
                return key
            finally:
                with lock:
                    active.remove(key)
        policies.callback = callback
        with pytest.raises(LookupError) as error:
            policies.collect()
        assert error.value.args == (7,)
        assert not active and not policies._mx_collect_cache
        failing = False
        assert package.mx_model.Caller.total() == sum(keys) + 10 * len(keys)
        result = policies.collect()
        assert list(result.individual) == list(keys)
        assert result.sum.value == result.sum.series[0] == sum(keys) + 10 * len(keys)
        assert shared_calls == [10]
        assert result is policies.collect()
        result.individual[7].state[0] = -999
        assert policies[7].value() == 17
        assert len(policies._mx_itemspaces) == 1
    finally:
        for module in tuple(sys.modules):
            if module == name or module.startswith(name + '.'):
                del sys.modules[module]


@pytest.mark.parametrize('workers', [1, 2, 4])
def test_exported_parallel_shape_error_precedes_later_formula_error(tmp_path, monkeypatch, workers):
    name = 'parallel_shape_export'
    model = mx.new_model('ParallelShape')
    try:
        policies = model.new_space('Policies', formula='lambda key: None',
            refs={'keys': (1, 2, 3, 4)}, collect_over={'key': (1, 2, 3, 4)},
            collect_outputs='lambda: {"sum" if key == 1 else "individual": {"value": value()}}')
        policies.new_cells('value', 'def value():\n    if key == 4:\n        raise LookupError("later")\n    return key')
        model.export(tmp_path / name)
    finally:
        model.close()
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        package = import_module(name)
        package.mx_model.collect_workers = workers
        with pytest.raises(ValueError, match='modes changed'):
            package.mx_model.Policies.collect()
        assert not package.mx_model.Policies._mx_collect_cache
    finally:
        for module in tuple(sys.modules):
            if module == name or module.startswith(name + '.'):
                del sys.modules[module]


@pytest.mark.parametrize('workers', [1, 2, 4])
def test_generic_parallel_collect_adds_in_policy_order(tmp_path, monkeypatch, workers):
    name = 'ordered_sum_export'
    model = mx.new_model('OrderedSum')
    try:
        keys = (0, 1, 2, 3)
        policies = model.new_space(
            'Policies', formula='lambda key: None', collect_over={'key': keys},
            refs={'keys': keys, 'amounts': (1e16, 0.0, -1e16, 1.0)},
            collect_outputs='lambda: {"sum": {"total": amounts[key]}, '
                            '"individual": {"amount": amounts[key]}}',
        )
        assert policies.collect().sum.total == 1.0
        model.export(tmp_path / name)
    finally:
        model.close()
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        package = import_module(name)
        assert name + '._mx_collect_semantics' in sys.modules
        package.mx_model.collect_workers = workers
        result = package.mx_model.Policies.collect()
        assert result.sum.total == 1.0
        assert tuple(result.individual) == keys
    finally:
        for module in tuple(sys.modules):
            if module == name or module.startswith(name + '.'):
                del sys.modules[module]


def _exported(tmp_path, name):
    model = mx.new_model(name)
    try:
        keys = tuple(range(6))
        space = model.new_space('Policies', formula='lambda key: None', refs={'keys': keys},
                                collect_over={'key': keys},
                                collect_outputs='lambda: {"sum": {"value": value()}}')
        space.new_cells('value', 'lambda: float(key) * 1.5')
        model.export(tmp_path / name)
    finally:
        model.close()
    return name


def test_collect_workers_property_live_and_exported(tmp_path, monkeypatch):
    model = mx.new_model('WorkersLive')
    try:
        assert model.collect_workers is None
        model.collect_workers = 4
        assert model.collect_workers == 4
        for bad in (0, -1, True, 2.0, '2'):
            with pytest.raises(ValueError):
                model.collect_workers = bad
        assert model.collect_workers == 4
        model.collect_workers = None
        assert model.collect_workers is None
        assert 'collect_workers' not in model.refs
    finally:
        model.close()
    name = _exported(tmp_path, 'workers_exported')
    monkeypatch.syspath_prepend(str(tmp_path))
    package = import_module(name)
    exported = package.mx_model
    assert exported.collect_workers is None
    serial = exported.Policies.collect().sum.value
    for workers in (1, 4, 100):          # more workers than the six items: one per item
        exported = type(exported)()     # a fresh model: an exported model has no clear
        exported.collect_workers = workers
        assert exported.collect_workers == workers
        assert exported.Policies.collect().sum.value == serial == 22.5
    for bad in (0, -2, False, 1.0):
        with pytest.raises(ValueError):
            exported.collect_workers = bad
    exported._mx_collect_set_workers_v2(3)          # export protocol 2 alias
    assert exported.collect_workers == 3
    with pytest.raises(ValueError):
        exported._mx_collect_set_workers_v2(None)


def test_collect_with_the_gil_evaluates_serially(monkeypatch):
    from concurrent import futures
    from modelx.export import _mx_sys as runtime
    monkeypatch.setattr(sys, '_is_gil_enabled', lambda: True, raising=False)
    monkeypatch.setattr(futures, 'ThreadPoolExecutor', None)    # a worker pool would fail
    base = SimpleNamespace(_model=SimpleNamespace())
    runtime.BaseModel._mx_collect_init_v2(base._model)
    runtime.BaseModel.collect_workers.fset(base._model, 4)
    seen = []

    def evaluate(coords):
        seen.append(tuple(coords))
        return runtime.CollectResult({'sum': runtime.CollectResult({'value': float(sum(coords))})})
    result = runtime.collect_from_space(base, range(8), 'key', (), (), evaluate_serial=evaluate,
                                        reuse_in_parallel=True)
    assert result.sum.value == 28.0 and seen == [tuple(range(8))]


def test_one_item_with_several_workers_takes_the_serial_evaluator(monkeypatch):
    from concurrent import futures
    from modelx.export import _mx_sys as runtime
    monkeypatch.setattr(futures, 'ThreadPoolExecutor', None)    # a worker pool would fail
    base = SimpleNamespace(_model=SimpleNamespace())
    runtime.BaseModel._mx_collect_init_v2(base._model)
    runtime.BaseModel.collect_workers.fset(base._model, 4)
    seen = []

    def evaluate(coords):
        seen.append(tuple(coords))
        return runtime.CollectResult({'sum': runtime.CollectResult({'value': 1.5})})
    result = runtime.collect_from_space(base, (7,), 'key', (), (), evaluate_serial=evaluate,
                                        reuse_in_parallel=True)
    assert result.sum.value == 1.5 and seen == [(7,)]
