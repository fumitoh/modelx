import sys
import os
import pathlib

import pandas as pd
import modelx as mx
import pytest
from modelx.export.exporter import Exporter


sample_dir = pathlib.Path(__file__).parent / 'samples'


def test_check_contents(tmp_path):
    nomx_path = tmp_path / 'model'
    m = mx.read_model(sample_dir / 'Options')
    mx.export_model(m, nomx_path / 'Options')
    assert set(os.listdir(nomx_path / 'Options')) == {
        '__init__.py', '_mx_sys.py', '_mx_classes.py', '_mx_model.py'}
    m.close()


@pytest.fixture(scope='module')
def empty_model():
    m = mx.read_model(sample_dir / 'EmptyModel')
    yield m
    m.close()


@pytest.mark.parametrize("api", ['function', 'method'])
def test_api(empty_model, tmp_path, api):
    nomx_path = tmp_path / 'model'

    try:
        sys.path.insert(0, str(nomx_path))

        if api == 'function':
            mx.export_model(empty_model , nomx_path / 'nomx_model')
        elif api == 'method':
            empty_model.export(nomx_path / 'nomx_model')
        else:
            raise RuntimeError

        from nomx_model import mx_model
        from nomx_model import EmptyModel
        assert mx_model is EmptyModel
    finally:
        sys.path.pop(0)


def test_nested_space_ref(tmp_path):
    nomx_path = tmp_path / 'model'
    m = mx.read_model(sample_dir / 'NestedSpace')
    Exporter(m, nomx_path / 'NestedSpace').export()

    try:
        sys.path.insert(0, str(nomx_path))
        from NestedSpace import mx_model
        assert mx_model.Pibling.sibling.Child.GrandChild.foo() == 'Hello!'
        assert mx_model.Parent.Child.GrandChild.grandpibling.bar() == 'Hello! World.'
    finally:
        sys.path.pop(0)


def test_pandasio(tmp_path):
    nomx_path = tmp_path / 'model'
    m = mx.read_model(sample_dir / 'PandasData')
    Exporter(m, nomx_path / 'PandasData').export()

    try:
        sys.path.insert(0, str(nomx_path))
        from PandasData import mx_model
        pd.testing.assert_frame_equal(mx_model.Foo.df, m.Foo.df)
    finally:
        sys.path.pop(0)
        m.close()


def test_pickle(tmp_path):

    m = mx.new_model('PickleSample')
    s = m.new_space('Space1')

    s.df = pd.DataFrame({
        'Name': ['John', 'Anna', 'Peter', 'Linda'],
        'Age': [28, 22, 35, 58],
        'City': ['New York', 'Los Angeles', 'Berlin', 'London']
    })

    nomx_path = tmp_path / 'model'
    Exporter(m, nomx_path / 'PickleSample').export()

    try:
        sys.path.insert(0, str(nomx_path))
        from PickleSample import mx_model
        pd.testing.assert_frame_equal(mx_model.Space1.df, m.Space1.df)
    finally:
        sys.path.pop(0)
        m.close()


def test_subscript(tmp_path):
    nomx_path = tmp_path / 'model'
    m = mx.read_model(sample_dir / 'SampleSubscript')
    Exporter(m, nomx_path / 'SampleSubscript').export()

    try:
        sys.path.insert(0, str(nomx_path))
        from SampleSubscript import mx_model
        assert mx_model.Space1.foo(1, 2, 3) == 10
    finally:
        sys.path.pop(0)
        m.close()


@pytest.fixture(scope="module")
def mortgage_model(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "FixedMortgage")
    Exporter(m, nomx_path / 'FixedMortgage').export()

    try:
        sys.path.insert(0, str(nomx_path))
        from FixedMortgage import mx_model
        yield m, mx_model
    finally:
        sys.path.pop(0)
        m._impl._check_sanity()
        m.close()


def test_literal_ref(mortgage_model):
    source, target = mortgage_model
    assert source.Fixed.Principal == target.Fixed.Principal == 100_000
    assert source.Fixed.Term == target.Fixed.Term == 30
    assert source.Fixed.Rate == target.Fixed.Rate == 0.03
    assert source.Fixed.SampleString == target.Fixed.SampleString


def test_module_ref(mortgage_model):
    source, target = mortgage_model
    assert source.Summary.itertools is sys.modules['itertools']


def test_itemspace(mortgage_model):
    source, target = mortgage_model
    assert source.Summary.Payments() == target.Summary.Payments()


@pytest.fixture(scope="session")
def sample_params(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "Params")
    m.export(nomx_path / 'Params_nomx')

    sys.path.insert(0, str(nomx_path))
    from Params_nomx import mx_model
    yield m, mx_model
    sys.path.pop(0)
    m.close()


def test_itemspace_params(sample_params):
    _, nomx = sample_params
    assert nomx.SingleParam(1).foo() == 1
    assert nomx.SingleParam[2].foo() == 2
    assert nomx.MultipleParams(3, 4).bar() == 7
    assert nomx.MultipleParams[5, 6].bar() == 11
    assert nomx.MultParamWithDefault(2).baz() == 4
    assert nomx.MultParamWithDefault[2].baz() == 4
    assert nomx.MultParamWithDefault(3, 4).baz() == 7
    assert nomx.MultParamWithDefault[3, 4].baz() == 7


def test_itemspace_delitem(sample_params):

    _, nomx = sample_params
    assert nomx.SingleParam(1).foo() == 1
    assert nomx.SingleParam[2].foo() == 2
    assert nomx.MultipleParams(3, 4).bar() == 7
    assert nomx.MultipleParams[5, 6].bar() == 11
    assert nomx.MultParamWithDefault(2).baz() == 4
    assert nomx.MultParamWithDefault[2].baz() == 4
    assert nomx.MultParamWithDefault(3, 4).baz() == 7
    assert nomx.MultParamWithDefault[3, 4].baz() == 7

    assert len(nomx.SingleParam._mx_itemspaces) == 2
    assert len(nomx.MultipleParams._mx_itemspaces) == 2
    assert len(nomx.MultParamWithDefault._mx_itemspaces) == 2

    del nomx.SingleParam[2]
    del nomx.MultipleParams[5, 6]
    del nomx.MultParamWithDefault[3, 4]

    assert len(nomx.SingleParam._mx_itemspaces) == 1
    assert len(nomx.MultipleParams._mx_itemspaces) == 1
    assert len(nomx.MultParamWithDefault._mx_itemspaces) == 1


def test_itemspace_nested_params(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "NestedParams")
    m.export(nomx_path / 'NestedParams_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from NestedParams_nomx import mx_model
        assert mx_model.Parent[1].x == 1
        assert mx_model.Parent[1].Child.x == 1
        assert mx_model.Parent[1].Child[2].x == 1
        assert mx_model.Parent[1].Child[2].y == 2
        assert mx_model.Parent[2].Child[3].x == 2
        assert mx_model.Parent[2].Child[3].y == 3
        assert mx_model.Parent[2].Child[3].SubChild.baz == 1

    finally:
        sys.path.pop(0)
        m.close()


def test_relative_refs(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "RelativeRefs")
    m.export(nomx_path / 'RelativeRefs_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from RelativeRefs_nomx import mx_model
        assert mx_model.Parent[1].Child2.c1 is mx_model.Parent[1].Child1
        assert mx_model.Parent[2].Child2.foo() == 2
        assert mx_model.Parent[3].Child2.c1abs is mx_model.Parent.Child1

    finally:
        sys.path.pop(0)
        m.close()


def test_relative_refs2(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "RelativeRefs2")
    m.export(nomx_path / 'RelativeRefs2_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from RelativeRefs2_nomx import mx_model
        assert mx_model.Parent.Child.foo_ref() == 0
        assert mx_model.Parent[1].Child.foo_ref() == 1
        assert mx_model.Parent.Child[2].foo_ref() == 0
        assert mx_model.Parent[1].Child[2].foo_ref() == 1
        assert mx_model.Parent[1].Child[2].foo_ref.__self__ is mx_model.Parent[1].foo.__self__

    finally:
        sys.path.pop(0)
        m.close()


def test_model_path(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "ModelPath")
    m.export(nomx_path / 'ModelPath_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from ModelPath_nomx import mx_model
        assert mx_model.Space1.foo() == nomx_path / 'ModelPath_nomx'

    finally:
        sys.path.pop(0)
        m.close()


def test_parent(tmp_path_factory):
    """Test if _parent is available both in the mx and nomx model

    Code modified from: https://github.com/fumitoh/modelx/discussions/129
    """

    m = mx.new_model()
    RA = m.new_space("RA")

    # Parameterize Space RA with `calc_loop`.
    # This means RA creates exact copies of itself parameterized by calc_loop on the fly,
    # such as RA[0], RA[1], RA[2], etc.
    # They are dynamic child spaces of RA.
    RA.parameters = ("calc_loop",)
    RA.calc_loop = 0    # In RA

    # Define BEL_LAPSE in RA. In the formula, calc_loop is the value given to the parameter of RA[calc_loop].
    # For example, calc_loop == 0 in RA[0].BEL_LAPSE(), calc_loop == 1 in RA[1].BEL_LAPSE(), and so on.
    # In the formula, `_space` is a special name that represents the parent space of the Cells.
    # For example, _space is RA[2] in RA[2].BEL_LAPSE(). _space.parent represents the parent space of RA[2], which is RA.
    # So, _space.parent[1].BEL_LAPSE() means RA[1].BEL_LAPSE()

    @mx.defcells(space=RA)
    def BEL_LAPSE():
        if calc_loop == 0:
            return 0
        elif calc_loop == 1:
            return 120
        else:
            return _space._parent[1].BEL_LAPSE()

    assert RA.BEL_LAPSE() == 0
    assert RA[0].BEL_LAPSE() == 0

    for i in range(1, 5):
        RA[i].BEL_LAPSE() == 120

    nomx_path = tmp_path_factory.mktemp('model')
    m.export(nomx_path / 'Parent_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from Parent_nomx import mx_model as nomx

        assert nomx.RA.BEL_LAPSE() == 0
        assert nomx.RA[0].BEL_LAPSE() == 0
        for i in range(1, 5):
            nomx.RA[i].BEL_LAPSE() == 120

    finally:
        sys.path.pop(0)
        m.close()


def test_space_properties(tmp_path_factory):

    m = mx.new_model()
    s1 = m.new_space("Space1")
    s2 = s1.new_space("Space2")

    @mx.defcells(space=s1)
    def get_parent():
        return _space._parent

    @mx.defcells(space=s2)
    def get_parent():
        return _space._parent

    @mx.defcells(space=s1)
    def get_name():
        return _space._name

    nomx_path = tmp_path_factory.mktemp('model')
    m.export(nomx_path / 'TestSpaceProperties_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from TestSpaceProperties_nomx import mx_model as nomx

        assert nomx.Space1.get_parent() is nomx
        assert nomx.Space1.Space2.get_parent() is nomx.Space1
        assert nomx.Space1.get_name() == "Space1"

    finally:
        sys.path.pop(0)
        m.close()