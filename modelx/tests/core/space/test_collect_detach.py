"""collect_outputs values are detached from the model: a flat container of immutable scalars is copied shallowly,
anything else is walked and deep-copied as before. Either way a returned container never aliases model state."""
import copy
import enum

import pytest

import modelx as mx
from modelx.export._mx_collect_semantics import _detach


class Live:
    pass


class Colour(enum.IntEnum):
    red = 1


@pytest.mark.parametrize("value", [
    {0: 1.5, 1: 2, 2: True, 3: "a", 4: None, 5: 1 + 2j, 6: b"x"},
    [1.5, 2, False, "a", None, 3j],
    (1.5, 2, "a", None),
    {},
    [],
])
def test_flat_scalar_containers_equal_the_deep_copy(value):
    result = _detach(value, (Live,))
    assert result == copy.deepcopy(value)
    assert type(result) is type(value)
    if type(value) in (dict, list):
        assert result is not value          # a new container: mutating it leaves the source unchanged
        result_copy = copy.deepcopy(value)
        if type(value) is dict:
            result["new"] = 0.0
        else:
            result.append(0.0)
        assert value == result_copy


@pytest.mark.parametrize("value", [
    {0: [1.0, 2.0]},
    [[1.0], [2.0]],
    {0: {1: 2.0}},
    ({0: 1.0},),
    [Colour.red],                           # a subclass of int takes the walk (exact types only)
    {0: 1.0, 1: (2.0, [3.0])},
])
def test_nested_or_other_values_are_still_deep_copied(value):
    result = _detach(value, (Live,))
    assert result == value
    inner_source = [v for v in (value.values() if type(value) is dict else value) if not isinstance(v, (int, float))]
    inner_result = [v for v in (result.values() if type(result) is dict else result) if not isinstance(v, (int, float))]
    for source, copied in zip(inner_source, inner_result):
        if type(source) in (dict, list):
            assert copied is not source


def test_live_objects_are_still_rejected():
    for value in ({0: Live()}, [Live()], (1.0, Live())):
        with pytest.raises(TypeError, match="not live modelx objects"):
            _detach(value, (Live,))


def test_mutating_a_returned_container_never_changes_a_later_result():
    model = mx.new_model("CollectDetach")
    try:
        data = model.new_space("Data")
        data.new_cells("rates", "lambda: {0: 1.0, 1: 2.0}")
        data.new_cells("labels", "lambda: ['a', 'b']")
        policy_ids = (1, 2)
        space = model.new_space(
            "Projection", formula="lambda scenario, policy_id: None",
            refs={"Data": data, "policy_ids": policy_ids},
            collect_over={"policy_id": policy_ids},
            collect_outputs='lambda: {"individual": {"rates": Data.rates(), "labels": Data.labels()}}')
        first = space.collect(0)
        first.individual[1].rates[0] = -1.0
        first.individual[1].labels.append("c")
        assert first.individual[2].rates == {0: 1.0, 1: 2.0}
        assert first.individual[2].labels == ["a", "b"]
        assert data.rates() == {0: 1.0, 1: 2.0}
        assert data.labels() == ["a", "b"]
        later = space.collect(1)
        assert later.individual[1].rates == {0: 1.0, 1: 2.0}
        assert later.individual[1].labels == ["a", "b"]
    finally:
        model.close()
