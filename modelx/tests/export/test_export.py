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


def test_itemspace_params(tmp_path_factory):
    nomx_path = tmp_path_factory.mktemp('model')
    m = mx.read_model(sample_dir / "Params")
    m.export(nomx_path / 'Params_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        from Params_nomx import mx_model
        assert mx_model.SingleParam(1).foo() == 1
        assert mx_model.SingleParam[2].foo() == 2
        assert mx_model.MultipleParams(3, 4).bar() == 7
        assert mx_model.MultipleParams[5, 6].bar() == 11
        assert mx_model.MultParamWithDefault(2).baz() == 4
        assert mx_model.MultParamWithDefault[2].baz() == 4
        assert mx_model.MultParamWithDefault(3, 4).baz() == 7
        assert mx_model.MultParamWithDefault[3, 4].baz() == 7

    finally:
        sys.path.pop(0)
        m.close()


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