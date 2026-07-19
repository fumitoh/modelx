from packaging.version import Version
import pytest
import modelx as mx
from modelx.tests.testdata import (
    PD_COMPAT_DIR,
    PD_COMPAT_ZIP,
    PD_COMPAT_MORTTBL
)
import pandas as pd

mort_tables = pd.read_pickle(PD_COMPAT_MORTTBL)

@pytest.mark.skipif(Version(pd.__version__) >= Version("3.0.0"),
                    reason="Pandas compatibility fix is for Pandas < 3.0.0")
@pytest.mark.parametrize("model", [PD_COMPAT_DIR, PD_COMPAT_ZIP])
def test_pandas_compat(model):
    m = mx.read_model(model)
    assert m.Input.MortalityTables.equals(mort_tables)
    m.close()


@pytest.mark.skipif(Version(pd.__version__) < Version("3.0.0"),
                    reason="Tolerant-load fallback applies from Pandas 3.0.0")
@pytest.mark.parametrize("model", [PD_COMPAT_DIR, PD_COMPAT_ZIP])
def test_pandas_compat_tolerant(model):
    # Pandas 3 dropped the compat hooks needed to rebuild these old
    # DataFrames, so the model loads with the tables replaced by None
    # instead of failing to load altogether.
    with pytest.warns(UserWarning, match="could not be restored"):
        m = mx.read_model(model)
    assert m.Input.MortalityTables is None
    m.close()
