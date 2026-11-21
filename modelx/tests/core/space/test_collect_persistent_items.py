import concurrent.futures
import importlib
import sys
import threading

import pytest

import modelx as mx


@pytest.fixture(params=[(True, ()), (False, ("SharedInput",))], ids=["slots", "locked-input"])
def exported_model(request, tmp_path, monkeypatch):
    use_slots, locked_spaces = request.param
    model = mx.new_model("PersistentItemSpaces")
    shared = model.new_space(
        "Shared", formula="lambda key: {'refs': {'datum': make_value(key)}}",
        refs={"datum": 0, "make_value": int},
    )
    shared.new_cells("value", "lambda: datum")
    inputs = model.new_space("SharedInput")
    inputs.new_cells("constant", "lambda: 1")
    keys = (1, 2, 3, 4)
    policies = model.new_space(
        "Policies", formula="lambda key: None",
        refs={"keys": keys, "evaluate": float},
        collect_over={"key": keys}, collect_outputs="lambda: {'sum': {'value': value()}}",
    )
    policies.new_cells("value", "lambda: evaluate(key)")
    package = "persistent_" + tmp_path.name
    try:
        model.export(tmp_path / package, use_slots=use_slots, locked_spaces=locked_spaces)
    finally:
        model.close()
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(sys, "_is_gil_enabled", lambda: False, raising=False)
    return importlib.import_module(package).mx_model


def test_direct_and_collect_workers_share_a_cold_persistent_item(exported_model, monkeypatch):
    model = exported_model
    lock = model._mx_lock
    if hasattr(model.SharedInput, "_mx_lock"):
        assert model.SharedInput._mx_lock is lock
    assert not hasattr(model.Shared, "_mx_lock")
    model.collect_workers = 4
    building = threading.Event()
    waiting = threading.Event()
    release = threading.Event()
    attempts = []
    worker_items = []
    enter = type(lock).__enter__

    def observe_enter(candidate):
        if candidate is lock and attempts and threading.get_ident() != attempts[0]:
            waiting.set()
        return enter(candidate)

    def make_value(key):
        attempts.append(threading.get_ident())
        building.set()
        assert release.wait(10)
        return 10 * key

    def evaluate(_):
        item = model.Shared[5]
        worker_items.append(item)
        return item.value()

    monkeypatch.setattr(type(lock), "__enter__", observe_enter)
    model.Shared.make_value = make_value
    model.Policies.evaluate = evaluate
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        direct = executor.submit(model.Shared.__getitem__, 5)
        try:
            assert building.wait(10)
            collected = executor.submit(model.Policies.collect)
            assert waiting.wait(10)
        finally:
            release.set()
        item = direct.result(timeout=10)
        assert collected.result(timeout=10).sum.value == 200
    assert len(attempts) == 1
    assert len(worker_items) == 4 and all(worker_item is item for worker_item in worker_items)
    assert not model.Policies._mx_itemspaces

    def unexpected_enter(_):
        pytest.fail("a warm ItemSpace lookup acquired the model lock")

    monkeypatch.setattr(type(lock), "__enter__", unexpected_enter)
    assert model.Shared[5] is item


def test_failed_persistent_itemspace_construction_is_retried(exported_model):
    model = exported_model
    attempts = []

    def fail_once(key):
        attempts.append(key)
        if len(attempts) == 1:
            raise ValueError("initialization failed")
        return 10 * key

    model.Shared.make_value = fail_once
    with pytest.raises(ValueError, match="initialization failed"):
        model.Shared[5]
    assert 5 not in model.Shared._mx_itemspaces
    item = model.Shared[5]
    assert model.Shared[5] is item
    assert item.value() == 50 and attempts == [5, 5]


def test_collect_in_a_persistent_itemspace_constructor_stays_serial(exported_model, monkeypatch):
    model = exported_model
    model.collect_workers = 4

    def evaluate_in_constructor(_):
        return model.Policies.collect().sum.value

    def unexpected_pool(*args, **kwargs):
        pytest.fail("nested collect attempted to start a worker pool")

    model.Shared.make_value = evaluate_in_constructor
    monkeypatch.setattr(concurrent.futures, "ThreadPoolExecutor", unexpected_pool)
    assert model.Shared[5].value() == 10
    assert not model.Policies._mx_itemspaces
