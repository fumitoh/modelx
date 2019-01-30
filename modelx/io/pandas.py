# Copyright (c) 2017-2019 Fumito Hamamura <fumito.ham@gmail.com>

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
import numpy as np

_pd_ver = tuple(int(i) for i in pd.__version__.split('.'))[:-1]

if _pd_ver < (0, 20):
    from pandas.tools.merge import MergeError

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
else:
    from pandas.core.reshape.merge import MergeError


def cellsiter_to_dataframe(cellsiter, args, drop_allna=True):
    """Convert multiple cells to a frame.

    If args is an empty sequence, all values are included.
    If args is specified, cellsiter must have shareable parameters.

    Args:
        cellsiter: A mapping from cells names to CellsImpl objects.
        args: A sequence of arguments
    """
    from modelx.core.cells import shareable_parameters

    if len(args):
        indexes = shareable_parameters(cellsiter)
    else:
        indexes = get_all_params(cellsiter.values())

    result = None

    for cells in cellsiter.values():
        df = cells_to_dataframe(cells, args)

        if drop_allna and df.isnull().all().all():
            continue  #  Ignore all NA or empty

        if df.index.names != [None]:
            if isinstance(df.index, pd.MultiIndex):
                if _pd_ver < (0, 20):
                    df = _reset_naindex(df)

            df = df.reset_index()

        missing_params = set(indexes) - set(df)

        for params in missing_params:
            df[params] = np.nan

        if result is None:
            result = df
        else:
            try:
                result = pd.merge(result, df, how='outer')
            except MergeError:
                # When no common column exists, i.e. all cells are scalars.
                result = pd.concat([result, df], axis=1)
            except ValueError:
                # When common columns are not coercible (numeric vs object),
                # Make the numeric column object type
                cols = set(result.columns) & set(df.columns)
                for col in cols:

                    # When only either of them has object dtype
                    if len([str(frame[col].dtype) for frame in (result, df)
                            if str(frame[col].dtype) == 'object']) == 1:

                        if str(result[col].dtype) == 'object':
                            frame = df
                        else:
                            frame = result
                        frame[[col]] = frame[col].astype('object')

                # Try again
                result = pd.merge(result, df, how='outer')

    if result is None:
        return pd.DataFrame()
    else:
        return result.set_index(indexes) if indexes else result


def get_all_params(cells_iter):

    params = [cells.parameters.keys() for cells in cells_iter]
    params = list(itertools.chain.from_iterable(params))
    return sorted(set(params), key=params.index)


def cells_to_dataframe(cells, args):
    return pd.DataFrame(cells_to_series(cells, args))


def cells_to_series(cells, args):
    """Convert a CellImpl into a Series.

    `args` must be a sequence of argkeys.

    `args` can be longer or shorter then the number of cell's parameters.
    If shorter, then defaults are filled if any, else raise error.
    If longer, then redundant args are ignored.
    """

    paramlen = len(cells.parameters)
    is_multidx = paramlen > 1

    if len(cells.data) == 0:
        data = {}
        indexes = None

    elif paramlen == 0:    # Const Cells
        data = list(cells.data.values())
        indexes = [np.nan]

    else:

        if len(args) > 0:
            defaults = tuple(param.default for param
                             in cells.parameters.values())
            updated_args = []
            for arg in args:

                if len(arg) > paramlen:
                    arg = arg[:paramlen]
                elif len(arg) < paramlen:
                    arg += defaults[len(arg):]

                updated_args.append(arg)

            items = [(arg, cells.data[arg]) for arg in updated_args
                     if arg in cells.data]
        else:
            items = [(key, value) for key, value in cells.data.items()]

        if not is_multidx: # Peel 1-element tuple
            items = [(key[0], value) for key, value in items]

        if len(items) == 0:
            indexes, data = None, {}
        else:
            indexes, data = zip(*items)
            if is_multidx:
                indexes = pd.MultiIndex.from_tuples(indexes)

    result = pd.Series(data=data, name=cells.name, index=indexes)

    if indexes is not None and any(i is not np.nan for i in indexes):
        result.index.names = list(cells.parameters.keys())

    return result



