import sys

import pandas as pd
import modelx as mx
import pytest
from modelx.export.exporter import Exporter


@pytest.fixture(scope="session")
def lifelib_savings(tmp_path_factory):
    import lifelib
    tmp = tmp_path_factory.mktemp('tmp') / 'savings'
    lifelib.create('savings', tmp)

    cv_ex4 = mx.read_model(tmp / 'CashValue_ME_EX4')
    nomx_path = tmp_path_factory.mktemp('nomx_models')
    Exporter(cv_ex4, nomx_path / 'CashValue_ME_EX4').export()

    try:
        sys.path.insert(0, str(nomx_path))
        from CashValue_ME_EX4 import mx_model
        yield cv_ex4, mx_model
    finally:
        sys.path.pop(0)
        cv_ex4.close()


def test_cv_ex4(lifelib_savings):
    source, target = lifelib_savings
    pd.testing.assert_frame_equal(
        source.Projection.result_pv(),
        target.Projection.result_pv())
