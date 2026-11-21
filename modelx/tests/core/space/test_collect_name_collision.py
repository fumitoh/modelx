from importlib import import_module
import sys

import pytest

import modelx as mx


@pytest.mark.parametrize("declared", [False, True])
def test_collect_cell_keeps_its_name(declared, tmp_path, monkeypatch):
    options = {}
    if declared:
        keys = (1, 2)
        options = {
            "refs": {"keys": keys},
            "collect_over": {"policy_id": keys},
            "collect_outputs": 'lambda: {"sum": {"amount": amount()}}',
        }

    package = "collect_collision_export"
    model = mx.new_model("CollectCollision")
    try:
        space = model.new_space("Policy", formula="lambda policy_id: None", **options)
        cell = space.new_cells("collect", "lambda: 5.0")
        space.new_cells("amount", "lambda: collect() + policy_id")
        caller = model.new_space("Caller", refs={"policy": space})
        caller.new_cells("amount", "lambda: policy.collect()")

        assert space.collect is cell
        assert space.collect() == 5.0
        space.collect = 6.0
        assert cell() == 6.0
        cell.clear_all()
        assert space.collect() == 5.0
        assert space[2].collect() == 5.0
        assert space[2].amount() == 7.0
        assert caller.amount() == 5.0
        if declared:
            assert space._mx_collect().sum.amount == 13.0

        model.export(tmp_path / package)
        monkeypatch.syspath_prepend(str(tmp_path))
        exported = import_module(package).mx_model
        assert exported.Policy.collect() == 5.0
        assert exported.Policy._cells["collect"]() == 5.0
        assert exported.Policy[2].collect() == 5.0
        assert exported.Policy[2].amount() == 7.0
        assert exported.Caller.amount() == 5.0
        if declared:
            assert exported.Policy._mx_collect().sum.amount == 13.0
    finally:
        model.close()
        for name in list(sys.modules):
            if name == package or name.startswith(package + "."):
                del sys.modules[name]
