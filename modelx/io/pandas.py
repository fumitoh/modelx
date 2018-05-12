# Copyright (c) 2017-2018 Fumito Hamamura <fumito.ham@gmail.com>

# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation version 3.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.

import itertools

import pandas as pd
from pandas.core.reshape.merge import MergeError
import numpy as np

_pd_ver = tuple(int(i) for i in pd.__version__.split('.'))[:-1]

if _pd_ver < (0, 20):
    # To circumvent the BUG: reset_index with NaN in MultiIndex
    # https://github.com/pandas-dev/pandas/issues/6322

    def _reset_naindex(df):
        nan_levels = [lv for lv, idx in enumerate(df.index.levels)
                      if idx.size == 0]

        for i, lv in enumerate(nan_levels):
            name = df.index.levels[lv - i].name
            df.index = df.index.droplevel(lv - i)
            df.insert(0, name, np.nan)

        return df


def space_to_dataframe(space):

    all_params = get_all_params(space.cells.values())
    result = None

    for cells in space.cells.values():
        df = cells_to_dataframe(cells)

        if df.index.names != [None]:
            if isinstance(df.index, pd.MultiIndex):
                if _pd_ver < (0, 20):
                    df = _reset_naindex(df)

            df = df.reset_index()   # TODO: consider inplace=True instead

        missing_params = set(all_params) - set(df)

        for params in missing_params:
            df[params] = np.nan

        if result is None:
            result = df
        else:
            try:
                result = pd.merge(result, df, how='outer')
            except MergeError:
                result = pd.concat([result, df], axis=1)

    return result.set_index(all_params) if all_params else result


def get_all_params(cells_iter):

    params = [cells.parameters.keys() for cells in cells_iter]
    params = list(itertools.chain.from_iterable(params))
    return sorted(set(params), key=params.index)


def cells_to_dataframe(cells):
    return pd.DataFrame(cells_to_series(cells))


def cells_to_series(cells):

    if len(cells.data) == 0:
        data = {}
        indexes = None

    elif len(cells.parameters) == 0:    # Const Cells
        data = list(cells.data.values())
        indexes = [np.nan]

    elif len(cells.parameters) == 1:
        items = [(key[0], value) for key, value in cells.data.items()]
        indexes, data = zip(*items)

    else:
        keys, data = zip(*cells.data.items())
        indexes = pd.MultiIndex.from_tuples(keys)

    result = pd.Series(data=data, name=cells.name,
                       index=indexes)

    if indexes is not None and any(i is not np.nan for i in indexes):
        result.index.names = list(cells.parameters.keys())

    return result



