"""Guard the ``repr_parent`` key in node attribute dicts.

``BaseNode._baseattrs`` and ``BaseNode._get_attrdict`` are wire formats
consumed by spyder-modelx: MxAnalyzer splits ``node["repr_parent"]`` on
"." to build its Model/Space columns (see devnotes/DependentPackages.md;
the schema is additive-only).  An ItemSpace embeds its parent's name in
its own repr ("Space[1]"), so its repr_parent skips the parent space:
nodes under ``Space[1]`` must report "Model.Space[1]", not "Model.Space",
and the node for ``Space[1]`` itself must report "Model".
"""

import modelx as mx

import pytest


@pytest.fixture
def testmodel():

    m = mx.new_model('Model')
    s = m.new_space('Space', formula=lambda i: None)
    s.new_cells('foo', formula=lambda x: x)
    s.new_space('Child', formula=lambda j: None).new_cells(
        'bar', formula=lambda y: y)

    # Compute values so that preds/succs in the attribute dicts work
    m.Space.foo(1)
    m.Space.Child.bar(2)
    m.Space[1].foo(2)
    m.Space[1].Child[2].bar(3)

    yield m
    m._impl._check_sanity()
    m.close()


params = [
    (lambda m: m.Space.foo.node(1), "Model.Space"),
    (lambda m: m.Space.Child.bar.node(2), "Model.Space.Child"),
    (lambda m: m.Space.node(1), "Model"),
    (lambda m: m.Space[1].foo.node(2), "Model.Space[1]"),
    (lambda m: m.Space[1].Child.node(2), "Model.Space[1]"),
    (lambda m: m.Space[1].Child[2].bar.node(3), "Model.Space[1].Child[2]"),
]


@pytest.mark.parametrize("get_node, expected", params)
def test_baseattrs_repr_parent(testmodel, get_node, expected):
    assert get_node(testmodel)._baseattrs["repr_parent"] == expected


@pytest.mark.parametrize("get_node, expected", params)
def test_attrdict_repr_parent(testmodel, get_node, expected):
    assert get_node(testmodel)._get_attrdict()["repr_parent"] == expected
