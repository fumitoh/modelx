import importlib
import sys
import math

import numpy as np
import pandas as pd
import modelx as mx
import pytest
from modelx.export.exporter import Exporter


samples = [
    ['basiclife', 'BasicTerm_S', 1],
    ['basiclife', 'BasicTerm_M', None],
    ['basiclife', 'BasicTerm_SE', 1],
    ['basiclife', 'BasicTerm_ME', None],
    ['savings', 'CashValue_SE', 1],
    ['savings', 'CashValue_ME', None],
    ['savings', 'CashValue_ME_EX4', None]
]

@pytest.fixture(scope="session", params=samples)
def basiclife_and_savings(request, tmp_path_factory):
    import lifelib
    library, name, arg = request.param

    tmp = tmp_path_factory.mktemp('tmp') / library
    lifelib.create(library, tmp)

    model = mx.read_model(tmp / name)
    nomx_path = tmp_path_factory.mktemp('nomx_models')
    model.export(nomx_path / (name + '_nomx'))

    try:
        sys.path.insert(0, str(nomx_path))
        nomx = importlib.import_module((name + '_nomx')).mx_model
        yield model, nomx, arg
    finally:
        sys.path.pop(0)
        model.close()


def test_basiclife_and_savings(basiclife_and_savings):
    source, target, arg = basiclife_and_savings

    pd.testing.assert_frame_equal(
        source.Projection.result_pv(),
        target.Projection.result_pv())

    if arg:
        pd.testing.assert_frame_equal(
            source.Projection[arg].result_pv(),
            source.Projection[arg].result_pv()
        )


def test_appliedlife(tmp_path_factory):
    import lifelib
    library, name = 'appliedlife', 'IntegratedLife'

    work_dir = tmp_path_factory.mktemp('tmp') / library
    lifelib.create(library, work_dir)

    model = mx.read_model(work_dir / name)
    model.export(work_dir / (name + '_nomx'))

    try:
        sys.path.insert(0, str(work_dir))
        nomx = importlib.import_module((name + '_nomx')).mx_model

        pd.testing.assert_frame_equal(
            model.Run[1].GMXB.result_pv(),
            nomx.Run[1].GMXB.result_pv()
        )

        pd.testing.assert_frame_equal(
            model.Run[1].GMXB.result_sample(),
            nomx.Run[1].GMXB.result_sample()
        )

    finally:
        sys.path.pop(0)
        model.close()


def test_assets(tmp_path_factory):
    import lifelib
    library, name, arg = 'assets', 'BasicBonds', None

    tmp = tmp_path_factory.mktemp('tmp') / library
    lifelib.create(library, tmp)

    model = mx.read_model(tmp / name)
    nomx_path = tmp_path_factory.mktemp('nomx_models')
    model.export(nomx_path / (name + '_nomx'))

    try:
        sys.path.insert(0, str(nomx_path))
        nomx = importlib.import_module((name + '_nomx')).mx_model
        assert model.Bonds.market_values() == nomx.Bonds.market_values()
    finally:
        sys.path.pop(0)
        model.close()


def test_economic(tmp_path_factory):
    import lifelib
    library, name, arg = 'economic', 'BasicHullWhite', None

    tmp = tmp_path_factory.mktemp('tmp') / library
    lifelib.create(library, tmp)

    model = mx.read_model(tmp / name)
    nomx_path = tmp_path_factory.mktemp('nomx_models')
    model.export(nomx_path / (name + '_nomx'))

    try:
        sys.path.insert(0, str(nomx_path))
        nomx = importlib.import_module((name + '_nomx')).mx_model.HullWhite
        space = model.HullWhite
        for cells in ['mean_short_rate', 'mean_disc_factor', 'var_short_rate']:
            assert np.array_equal(getattr(nomx, cells)(),
                                  getattr(space, cells)(),
                                  equal_nan=True)
    finally:
        sys.path.pop(0)
        model.close()


def test_smithwilson(tmp_path_factory):
    import lifelib
    library, name, arg = 'smithwilson', 'model', None

    tmp = tmp_path_factory.mktemp('tmp') / library
    lifelib.create(library, tmp)

    model = mx.read_model(tmp / name)
    nomx_path = tmp_path_factory.mktemp('nomx_models')
    model.export(nomx_path / 'smithwilson_nomx')

    try:
        sys.path.insert(0, str(nomx_path))
        nomx = importlib.import_module('smithwilson_nomx').mx_model.SmithWilson
        space = model.SmithWilson
        for i in range(10, 101, 5):
            assert math.isclose(nomx.R(i), space.R[i])

    finally:
        sys.path.pop(0)
        model.close()