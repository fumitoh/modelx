import os, sys
import pathlib

data_path = pathlib.Path(
    os.path.dirname(sys.modules[__name__].__file__)
)
CSV_SINGLE_PARAM = data_path / "single_param.csv"
CSV_MULTI_PARAMS = data_path / "multi_params.csv"
CSV_SINGLE_PARAM_SINGLE_COL = data_path / "single_param_single_col.csv"
CSV_IRIS = data_path / "iris.csv"

XL_TESTDATA = str(data_path / "testdata.xlsx")
