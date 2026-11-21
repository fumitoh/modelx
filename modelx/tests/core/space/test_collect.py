import pytest
import sys
from importlib import import_module
from modelx.core.errors import FormulaError
import modelx as mx


def _make_space(model):
    policy_ids = (1, 2, 3)
    space = model.new_space(
        "Projection",
        formula="lambda scenario, policy_id: None",
        refs={"policy_ids": policy_ids, "factor": 10},
        collect_over={"policy_id": policy_ids},
        collect_outputs=(
            'lambda: {'
            '"individual": {'
            '"net_cf": {t: cf(t) for t in range(3)}'
            '}, '
            '"sum": {'
            '"net_cf": {t: cf(t) for t in range(3)}, '
            '"pv": pv()'
            '}'
            '}'
        ),
    )
    space.new_cells("cf", "lambda t: factor * policy_id + scenario + t")
    space.new_cells("pv", "lambda: factor * policy_id - scenario")
    return space


def test_collect_declaration_roundtrips_in_model_serialization(tmp_path):
    model = mx.new_model("CollectRoundtrip")
    try:
        _make_space(model)
        mx.write_model(model, tmp_path / "saved")
    finally:
        model.close()

    restored = mx.read_model(tmp_path / "saved")
    try:
        result = restored.Projection.collect(5)
        assert result.sum.pv == 45
        assert result.individual[2].net_cf == {0: 25, 1: 26, 2: 27}
    finally:
        restored.close()


def test_collect_exports_transient_policy_execution(tmp_path):
    model = mx.new_model("CollectExport")
    try:
        projection = _make_space(model)
        expected = projection.collect(5)
        model.export(tmp_path / "collect_export")
    finally:
        model.close()

    sys.path.insert(0, str(tmp_path))
    try:
        exported = import_module("collect_export").mx_model
        result = exported.Projection.collect(5)
        assert result.sum.pv == expected.sum.pv
        assert result.sum.net_cf == expected.sum.net_cf
        assert result.individual[2].net_cf == expected.individual[2].net_cf
        assert exported.Projection._mx_itemspaces == {}
        assert exported.Projection(5, 2).pv() == 15
    finally:
        sys.path.pop(0)
        for name in list(sys.modules):
            if name == "collect_export" or name.startswith("collect_export."):
                del sys.modules[name]


def test_collect_cell_domain_roundtrips_and_exports(tmp_path):
    model = mx.new_model("CollectCellDomain")
    try:
        projection = model.new_space("Projection", formula="lambda policy_id: None")
        ids = projection.new_cells("ids", "lambda: (1, 2, 3)")
        projection.new_cells("collect_outputs", 'lambda: {"sum": {"value": value()}}')
        projection._impl.set_collect_spec({"policy_id": ids})
        projection.new_cells("value", "lambda: policy_id * 2")
        assert projection.collect().sum.value == 12
        mx.write_model(model, tmp_path / "saved_cell")
        model.export(tmp_path / "cell_export")
    finally:
        model.close()

    restored = mx.read_model(tmp_path / "saved_cell")
    try:
        assert restored.Projection.collect().sum.value == 12
    finally:
        restored.close()
    sys.path.insert(0, str(tmp_path))
    try:
        exported = import_module("cell_export").mx_model
        assert exported.Projection.collect().sum.value == 12
    finally:
        sys.path.pop(0)
        for name in list(sys.modules):
            if name == "cell_export" or name.startswith("cell_export."):
                del sys.modules[name]


def test_collect_supports_individual_and_sum_modes():
    model = mx.new_model("CollectBasic")
    try:
        space = _make_space(model)

        result = space.collect(5)

        assert result.individual[1].net_cf == {0: 15, 1: 16, 2: 17}
        assert result.individual[2].net_cf == {0: 25, 1: 26, 2: 27}
        assert result.individual[3].net_cf == {0: 35, 1: 36, 2: 37}
        assert result.sum.net_cf == {
            0: 75,
            1: 78,
            2: 81,
        }
        assert result.sum.pv == 45
        assert len(space.itemspaces) == 0
    finally:
        model.close()


def test_collect_keeps_normal_dynamic_space_behavior():
    model = mx.new_model("CollectNormal")
    try:
        space = _make_space(model)
        item = space(5, 2)
        assert item.cf(1) == 26

        result = space.collect(5)

        assert result.sum.pv == 45
        assert space(5, 2) is item
        assert len(space.itemspaces) == 1
    finally:
        model.close()


def test_collect_dependencies_survive_transient_itemspace_deletion():
    model = mx.new_model("CollectDeps")
    try:
        space = _make_space(model)
        outer = model.new_space("Outer", refs={"projection": space})
        outer.new_cells(
            "total", "lambda: projection.collect(5).sum.pv")

        assert outer.total() == 45
        assert len(space.itemspaces) == 0

        space.factor = 20

        assert outer.total() == 105
        assert len(space.itemspaces) == 0
    finally:
        model.close()


def test_collect_domain_is_live_reference():
    model = mx.new_model("CollectDomain")
    try:
        space = _make_space(model)
        outer = model.new_space("Outer", refs={"projection": space})
        outer.new_cells(
            "total", "lambda: projection.collect(5).sum.pv")

        assert outer.total() == 45

        space.policy_ids = (2, 4)

        result = space.collect(5)
        assert result.individual[2].net_cf[1] == 26
        assert result.individual[4].net_cf[1] == 46
        assert result.sum.pv == 50
        assert outer.total() == 50
    finally:
        model.close()


def test_collect_over_accepts_zero_arg_cells_domain():
    model = mx.new_model("CollectCellsDomain")
    try:
        domains = model.new_space("Domains")
        ids = domains.new_cells("ids", "lambda: (1, 3)")
        space = model.new_space(
            "Projection",
            formula="lambda policy_id: None",
            collect_over={"policy_id": ids},
            collect_outputs=(
                'lambda: {'
                '"individual": {"value": value()}, '
                '"sum": {"value": value()}'
                '}'
            ),
        )
        space.new_cells("value", "lambda: policy_id * 2")

        result = space.collect()
        assert result.individual[1].value == 2
        assert result.individual[3].value == 6
        assert result.sum.value == 8
        assert len(space.itemspaces) == 0
    finally:
        model.close()


def test_collect_rejects_multiple_collect_over_parameters():
    model = mx.new_model("CollectMulti")
    try:
        policy_ids = (1, 2)
        scenario_ids = (10, 20)
        with pytest.raises(
                ValueError, match="exactly one Space parameter"):
            model.new_space(
                "Projection",
                formula="lambda policy_id, scenario_id: None",
                refs={"policy_ids": policy_ids, "scenario_ids": scenario_ids},
                collect_over={
                    "policy_id": policy_ids,
                    "scenario_id": scenario_ids,
                },
                collect_outputs=(
                    'lambda: {'
                    '"individual": {"value": policy_id + scenario_id}'
                    '}'
                ),
            )
    finally:
        model.close()

def test_collect_rejects_nested_structure_changes():
    model = mx.new_model("CollectShape")
    try:
        policy_ids = (1, 2)
        space = model.new_space(
            "Projection",
            formula="lambda policy_id: None",
            refs={"policy_ids": policy_ids},
            collect_over={"policy_id": policy_ids},
            collect_outputs=(
                'lambda: {'
                '"individual": {'
                '"value": {t: value(t) for t in range(policy_id)}'
                '}'
                '}'
            ),
        )
        space.new_cells("value", "lambda t: 10 * policy_id + t")

        with pytest.raises(FormulaError, match="structure changed"):
            space.collect()
    finally:
        model.close()


def test_collect_modes_are_optional_but_only_known_modes_are_allowed():
    model = mx.new_model("CollectModes")
    try:
        policy_ids = (1, 2)
        individual = model.new_space(
            "IndividualOnly",
            formula="lambda policy_id: None",
            refs={"policy_ids": policy_ids},
            collect_over={"policy_id": policy_ids},
            collect_outputs='lambda: {"individual": {"value": value()}}',
        )
        individual.new_cells("value", "lambda: policy_id")
        assert individual.collect().individual[1].value == 1
        assert individual.collect().individual[2].value == 2
        with pytest.raises(AttributeError):
            individual.collect().sum

        summed = model.new_space(
            "SumOnly",
            formula="lambda policy_id: None",
            refs={"policy_ids": policy_ids},
            collect_over={"policy_id": policy_ids},
            collect_outputs='lambda: {"sum": {"value": value()}}',
        )
        summed.new_cells("value", "lambda: policy_id")
        assert summed.collect().sum.value == 3
        with pytest.raises(AttributeError):
            summed.collect().individual

        invalid = model.new_space(
            "InvalidMode",
            formula="lambda policy_id: None",
            refs={"policy_ids": policy_ids},
            collect_over={"policy_id": policy_ids},
            collect_outputs='lambda: {"mean": {"value": value()}}',
        )
        invalid.new_cells("value", "lambda: policy_id")
        with pytest.raises(FormulaError, match="unsupported top-level"):
            invalid.collect()
    finally:
        model.close()


def test_collect_policy_formula_edits_invalidate_downstream():
    model = mx.new_model('CollectFormulaEdit')
    try:
        space = _make_space(model)
        outer = model.new_space('Outer', refs={'projection': space})
        outer.new_cells('total', 'lambda: projection.collect(5).sum.pv')
        assert outer.total() == 45
        space.pv.formula = 'lambda: 2 * (factor * policy_id - scenario)'
        assert not space._impl.collect_runner.data
        assert len(outer.total) == 0
        assert outer.total() == 90
        space.collect_outputs.formula = 'lambda: {"sum": {"pv": 3 * pv()}}'
        assert outer.total() == 270
    finally:
        model.close()


def test_collect_signature_defaults_refresh_after_formula_edit():
    model = mx.new_model('CollectSignatureEdit')
    try:
        space = _make_space(model)
        space.formula = 'lambda scenario=5, policy_id=1: None'
        assert space.collect().sum.pv == 45
        space.formula = 'lambda scenario=10, policy_id=1: None'
        assert space.collect().sum.pv == 30
        assert space.collect() is space.collect(scenario=10)
    finally:
        model.close()


def test_collect_derived_formula_edits_invalidate_collected_template():
    model = mx.new_model('CollectBaseEdit')
    try:
        base = model.new_space('Base')
        base.new_cells('v', 'lambda: policy_id * 10')
        space = model.new_space(
            'Projection', bases=base, formula='lambda policy_id: None',
            collect_over={'policy_id': (1, 2)},
            collect_outputs='lambda: {"sum": {"v": v()}}')
        assert space.collect().sum.v == 30
        base.v.formula = 'lambda: policy_id * 20'
        assert space.collect().sum.v == 60
    finally:
        model.close()


def test_nested_collect_keeps_earlier_policy_external_dependencies():
    model = mx.new_model('CollectNested')
    try:
        inputs = model.new_space('Inputs', refs={'first': 10, 'second': 20})
        inputs.new_cells('value', 'lambda policy_id: first if policy_id == 1 else second')
        actual = model.new_space(
            'Actual', formula='lambda policy_id: None', refs={'Inputs': inputs},
            collect_over={'policy_id': (1, 2)},
            collect_outputs='lambda: {"individual": {"state": Inputs.value(policy_id)}}')
        valuation = model.new_space(
            'Valuation', formula='lambda t, policy_id, shock=-1: {"refs": {"state": Actual.collect().individual[policy_id].state}}',
            refs={'Actual': actual}, collect_over={'policy_id': (1, 2)},
            collect_outputs='lambda: {"sum": {"pv": state + t + shock}}')
        outer = model.new_space('Outer', refs={'Valuation': valuation})
        outer.new_cells('pv', 'lambda: Valuation.collect(12).sum.pv')
        assert outer.pv() == 52
        assert not actual.itemspaces and not valuation.itemspaces
        inputs.first = 40
        assert not actual._impl.collect_runner.data
        assert not valuation._impl.collect_runner.data
        assert len(outer.pv) == 0
        assert outer.pv() == 82
    finally:
        model.close()


def test_collect_cache_canonicalizes_defaults_and_keywords():
    model = mx.new_model('CollectCanonical')
    try:
        space = model.new_space(
            'Valuation', formula='lambda t, policy_id, shock=-1: None',
            collect_over={'policy_id': (1, 2)},
            collect_outputs='lambda: {"sum": {"pv": t + policy_id + shock}}')
        result = space.collect(12)
        assert result.sum.pv == 25
        assert space.collect(12, -1) is result
        assert space.collect(t=12, shock=-1) is result
        assert space.collect(12, shock=-1) is result
        assert space.collect(24) is not result
        with pytest.raises(TypeError):
            space.collect()
        with pytest.raises(TypeError):
            space.collect(12, 1, -1)
        with pytest.raises(TypeError):
            space.collect(12, policy_id=1)
    finally:
        model.close()


def test_collect_positional_cache_hit_avoids_binding_and_frame_creation(monkeypatch):
    from inspect import Signature
    from modelx.core.collect import CollectRunner
    model = mx.new_model('CollectFastHit')
    try:
        space = _make_space(model)
        result = space.collect(5)
        def forbidden(*args, **kwargs):
            raise AssertionError('cached all-positional call should not bind or calculate')
        with monkeypatch.context() as patch:
            patch.setattr(Signature, 'bind', forbidden)
            patch.setattr(CollectRunner, '_new_frame', forbidden)
            assert space.collect(5) is result
    finally:
        model.close()


def test_collect_unhashable_arguments_are_identity_keyed():
    model = mx.new_model('CollectUnhashable')
    try:
        space = model.new_space(
            'Projection', formula='lambda inputs, policy_id: None',
            collect_over={'policy_id': (1, 2)},
            collect_outputs='lambda: {"sum": {"value": inputs[policy_id]}}')
        first, second = {1: 10, 2: 20}, {1: 10, 2: 20}
        result = space.collect(first)
        assert result.sum.value == 30
        assert space.collect(inputs=first) is result
        assert space.collect(second) is not result
    finally:
        model.close()


def test_collect_releases_each_frame_before_next(monkeypatch):
    from modelx.core.collect import CollectRunner
    model = mx.new_model('CollectRelease')
    seen = []
    original = CollectRunner._new_frame
    def monitored(self, key):
        if seen:
            assert not seen[-1]._is_valid()
        assert not self.space.named_itemspaces
        root = original(self, key)
        seen.append(root.interface)
        return root
    try:
        space = _make_space(model)
        monkeypatch.setattr(CollectRunner, '_new_frame', monitored)
        assert space.collect(5).sum.pv == 45
        assert len(seen) == 3
        assert all(not item._is_valid() for item in seen)
        assert not space._impl.dynamic_cache
        assert not space._impl._dynamic_subs
    finally:
        model.close()


def test_collect_exception_releases_frame_and_does_not_cache_partial_result():
    model = mx.new_model('CollectErrorCleanup')
    try:
        space = model.new_space(
            'Projection', formula='lambda policy_id: None',
            collect_over={'policy_id': (1, 2, 3)},
            collect_outputs='lambda: {"sum": {"v": 1 / (policy_id - 2)}}')
        with pytest.raises(FormulaError):
            space.collect()
        assert not space._impl.collect_runner.data
        assert not space._impl.named_itemspaces
        assert not space._impl.dynamic_cache
        assert not space._impl._dynamic_subs
        space.collect_outputs.formula = 'lambda: {"sum": {"v": policy_id}}'
        assert space.collect().sum.v == 6
    finally:
        model.close()


def test_collect_clear_all_clears_result_and_downstream_cache():
    model = mx.new_model('CollectExplicitClear')
    try:
        space = _make_space(model)
        outer = model.new_space('Outer', refs={'projection': space})
        outer.new_cells('total', 'lambda: projection.collect(5).sum.pv')
        assert outer.total() == 45
        previous = space.collect(5)
        space.clear_all()
        assert not space._impl.collect_runner.data
        assert len(outer.total) == 0
        assert space.collect(5) is not previous
        assert outer.total() == 45
    finally:
        model.close()


def test_collect_is_visible_in_normal_dependency_node_inspection():
    model = mx.new_model('CollectNodeInspection')
    try:
        space = _make_space(model)
        outer = model.new_space('Outer', refs={'projection': space})
        outer.new_cells('total', 'lambda: projection.collect(5).sum.pv')
        assert outer.total() == 45
        node = outer.total.preds()[0]
        assert 'Projection.collect(scenario=5)' in repr(node)
        assert node.args == (5,)
        assert node.value is space.collect(5)
        assert node.obj(5) is node.value
        assert outer.total.node() in node.succs
        assert any(ref.value == 10 for ref in node.precedents)
        assert 'Projection.collect' in repr(outer.total.precedents())
        assert node._baseattrs['type'] == 'ItemNode'
    finally:
        model.close()
