import os, sys

test_path = (
    os.path.dirname(sys.modules[__name__].__file__) + "/../data/"
)
ONE_PARAM_SAMPLE = test_path + "single_param.csv"
TWO_PARAMS_SAMPLE = test_path + "multi_params.csv"
ONE_PARAM_ONE_COL_SAMPLE = test_path + "single_param_single_col.csv"
IRIS_SAMPLE = test_path + "iris.csv"