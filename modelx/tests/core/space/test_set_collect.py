"""Space.set_collect: the collect declaration of an existing Space, whose domain may be a Cells of the
Space itself; it survives write_model/read_model and export."""
from importlib import import_module

import modelx as mx
import pytest


def _model(name):
    model = mx.new_model(name)
    space = model.new_space('Projection', formula=lambda point_id: None,
                            refs={'points': (3, 1, 2)})
    space.new_cells('policy_ids', lambda: tuple(points))
    space.new_cells('value', lambda: point_id * 1.5)
    return model, space


def test_set_collect_with_a_cells_domain(tmp_path, monkeypatch):
    model, space = _model('SetCollect')
    try:
        with pytest.raises(TypeError):
            space.set_collect(over={'point_id': space.policy_ids})        # no outputs yet
        space.set_collect(over={'point_id': space.policy_ids},
                          outputs=lambda: {'sum': {'value': value()},
                                           'individual': {'v': value()}})
        result = space.collect()
        assert result.sum.value == 9.0
        assert list(result.individual) == [3, 1, 2]
        space.points = (2, 4)                                              # the domain Cell follows
        assert space.collect().sum.value == 9.0 and list(space.collect().individual) == [2, 4]
        space.set_collect(over={'point_id': space.policy_ids},             # new outputs replace old ones
                          outputs=lambda: {'sum': {'twice': 2 * value()}})
        assert space.collect().sum.twice == 18.0
        space.set_collect(over={'point_id': (1,)})                         # keep the outputs
        assert space.collect().sum.twice == 3.0
        space.set_collect(over={'point_id': space.policy_ids})
        with pytest.raises(ValueError):
            space.set_collect(over={'other': space.policy_ids})
        mx.write_model(model, tmp_path / 'saved')
        model.export(tmp_path / 'set_collect_exported')
    finally:
        model.close()
    loaded = mx.read_model(tmp_path / 'saved', name='SetCollectRead')
    try:
        assert loaded.Projection.collect().sum.twice == 18.0
        loaded.Projection.points = (5,)
        assert loaded.Projection.collect().sum.twice == 15.0
    finally:
        loaded.close()
    monkeypatch.syspath_prepend(str(tmp_path))
    exported = import_module('set_collect_exported').mx_model
    assert exported.Projection.collect().sum.twice == 18.0


def test_set_collect_needs_a_parameter_formula():
    model = mx.new_model('SetCollectNoFormula')
    try:
        space = model.new_space('Plain')
        space.new_cells('ids', lambda: (1, 2))
        with pytest.raises(TypeError):
            space.set_collect(over={'x': space.ids}, outputs=lambda: {'sum': {'n': 1}})
    finally:
        model.close()
