from importlib import import_module
import sys

import modelx as mx
import pytest


@pytest.mark.parametrize("phase", ["attach", "outputs"])
def test_failed_exported_collect_releases_worker_storage(tmp_path, monkeypatch, phase):
    name = "collect_cleanup_export"
    model = mx.new_model("CollectCleanup")
    keys = (1, 2, 3)
    try:
        model.new_space(
            "Policies", formula="lambda key: None",
            refs={"keys": keys}, collect_over={"key": keys},
            collect_outputs='lambda: {"sum": {"value": key}}',
        )
        model.export(tmp_path / name)
    finally:
        model.close()
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        policies = import_module(name).mx_model.Policies
        space_type = type(policies)
        failure = ValueError("policy failed")
        active = []
        scratch_dicts = []
        failing = True

        def attach(self, scratch, template):
            scratch.setdefault(template, object())
            scratch_dicts.append(scratch)
            active.append(self.key)
            if failing and self.key == 2 and phase == "attach":
                raise failure

        def outputs(self):
            if failing and self.key == 2 and phase == "outputs":
                raise failure
            return {"sum": {"value": self.key}}

        def release(self, scratch, template):
            active.remove(self.key)
            if failing and self.key == 2:
                raise RuntimeError("cleanup failed too")

        monkeypatch.setattr(space_type, "_mx_collect_attach", attach, raising=False)
        monkeypatch.setattr(space_type, "_mx_collect_release", release, raising=False)
        monkeypatch.setattr(space_type, "collect_outputs", outputs)
        with pytest.raises(ValueError) as error:
            policies.collect()
        assert error.value is failure
        assert not active
        assert not scratch_dicts[-1]

        failing = False
        assert policies.collect().sum.value == 6
        assert not active
        assert not policies._mx_itemspaces
    finally:
        for module in tuple(sys.modules):
            if module == name or module.startswith(name + "."):
                del sys.modules[module]
