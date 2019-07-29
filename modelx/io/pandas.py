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
import uuid

import pandas as pd
import numpy as np

from modelx.core.node import tuplize_key
from modelx.core.util import is_valid_name, get_param_func

_pd_ver = tuple(int(i) for i in pd.__version__.split("."))[:-1]

if _pd_ver < (0, 20):
    from pandas.tools.merge import MergeError

    # To circumvent the BUG: reset_index with NaN in MultiIndex
    # https://github.com/pandas-dev/pandas/issues/6322
    def _reset_naindex(df):
        nan_levels = [
            lv for lv, idx in enumerate(df.index.levels) if idx.size == 0
        ]

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
                result = pd.merge(result, df, how="outer")
            except MergeError:
                # When no common column exists, i.e. all cells are scalars.
                result = pd.concat([result, df], axis=1)
            except ValueError:
                # When common columns are not coercible (numeric vs object),
                # Make the numeric column object type
                cols = set(result.columns) & set(df.columns)
                for col in cols:

                    # When only either of them has object dtype
                    if (
                        len(
                            [
                                str(frame[col].dtype)
                                for frame in (result, df)
                                if str(frame[col].dtype) == "object"
                            ]
                        )
                        == 1
                    ):

                        if str(result[col].dtype) == "object":
                            frame = df
                        else:
                            frame = result
                        frame[[col]] = frame[col].astype("object")

                # Try again
                result = pd.merge(result, df, how="outer")

    if result is None:
        return pd.DataFrame()
    else:
        return result.set_index(indexes) if indexes else result


def get_all_params(cells_iter):

    params = [cells.formula.parameters for cells in cells_iter]
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

    paramlen = len(cells.formula.parameters)
    is_multidx = paramlen > 1

    if len(cells.data) == 0:
        data = {}
        indexes = None

    elif paramlen == 0:  # Const Cells
        data = list(cells.data.values())
        indexes = [np.nan]

    else:

        if len(args) > 0:
            defaults = tuple(
                param.default
                for param in cells.formula.signature.parameters.values()
            )
            updated_args = []
            for arg in args:

                if len(arg) > paramlen:
                    arg = arg[:paramlen]
                elif len(arg) < paramlen:
                    arg += defaults[len(arg) :]

                updated_args.append(arg)

            items = [
                (arg, cells.data[arg])
                for arg in updated_args
                if arg in cells.data
            ]
        else:
            items = [(key, value) for key, value in cells.data.items()]

        if not is_multidx:  # Peel 1-element tuple
            items = [(key[0], value) for key, value in items]

        if len(items) == 0:
            indexes, data = None, {}
        else:
            indexes, data = zip(*items)
            if is_multidx:
                indexes = pd.MultiIndex.from_tuples(indexes)

    result = pd.Series(data=data, name=cells.name, index=indexes)

    if indexes is not None and any(i is not np.nan for i in indexes):
        result.index.names = list(cells.formula.parameters)

    return result


def _get_param_names(obj, param):
    """Get list of param names from Series or DataFrame and ``param``"""
    param_len = obj.index.nlevels

    if param_len == 1 and isinstance(param, str):
        param = [param]

    param_names = list(obj.index.names)

    if param:
        param = param + [None] * max(param_len - len(param), 0)
        param_names = [
            param[i] if is_valid_name(param[i]) else n
            for i, n in enumerate(param_names)
        ]

    if not all([is_valid_name(n) for n in param_names]):
        raise ValueError("invalid parameter names")

    return param_names


def _new_cells_from_series(self, series, name, param, source):

    if is_valid_name(name):
        pass
    else:
        if is_valid_name(series.name):
            name = series.name

    cells = self.new_cells(
        name=name,
        formula=get_param_func(_get_param_names(series, param)),
        source=source
    )

    for i, v in series.items():
        cells.set_value(tuplize_key(cells, i), v)

    return cells


def _overwrite_colnames(self, frame, names):

    if frame.columns.nlevels > 1:
        raise ValueError("columns must not be MultiIndex")

    cells_names = list(frame.columns)

    if names is not None:
        is_overwritten = [is_valid_name(n) for n in names] + [False] * max(
            len(cells_names) - len(names), 0)
        cells_names = [
            names[i] if is_overwritten[i] else n
            for i, n in enumerate(cells_names)]
    else:
        is_overwritten = [False] * len(cells_names)

    for name in cells_names:
        if not is_valid_name(name):
            raise ValueError("%s is not a valid name" % name)
        else:
            if name in self.namespace:
                raise ValueError("%s already exists" % name)

    return cells_names


def new_cells_from_pandas(self, obj, cells, param, source):

    if isinstance(obj, pd.Series):
        return _new_cells_from_series(
            self, obj, cells, param, source).interface

    else:
        cells_names = _overwrite_colnames(self, obj, cells)

        for i, c in enumerate(obj.columns):
            _new_cells_from_series(
                self,
                obj[c],
                name=cells_names[i],
                param=param,
                source=source
            )

        return self.interface.cells[cells_names]


def new_space_from_pandas(
        self, obj, space, cells, param, space_params, cells_params, source):

    param_names = _get_param_names(obj, param)

    def normalize_params(paramlist):
        """Covert index elements to str"""
        return [p if isinstance(p, str) else param_names[p]
                for p in paramlist]

    if space_params is None:
        if cells_params is None:
            cells_params = param_names
        else:
            cells_params = normalize_params(cells_params)
            if set(param_names) == set(cells_params):
                pass
            else:
                raise ValueError("invalid cells_params")
    else:
        space_params = normalize_params(space_params)
        if cells_params is None:
            cells_params = [p for p in param_names if p not in space_params]
        else:
            cells_params = normalize_params(cells_params)

            if (set(space_params) | set(cells_params) == set(param_names)
                    and len(set(space_params) & set(cells_params)) == 0):
                pass
            else:
                raise ValueError("invalid cells_params")

    if space_params is None:
        space_func = None
    else:
        space_func = get_param_func(space_params)

    newspace = self.new_space(name=space, formula=space_func, source=source)

    if isinstance(obj, pd.Series):
        obj = obj.to_frame()

    cells_names = _overwrite_colnames(self, obj, names=cells)

    for c in cells_names:
        newspace.new_cells(name=c, formula=get_param_func(cells_params))

    cells_paramidxs = [param_names.index(p) for p in cells_params
                       if p in param_names]

    if space_params is not None:
        space_paramsidxs = [param_names.index(p) for p in space_params
                            if p in param_names]

    def idx_to_arg(idx):

        cargs = tuple(idx[i] for i in cells_paramidxs)
        if space_params is not None:
            sargs = tuple(idx[i] for i in space_paramsidxs)
        else:
            sargs = None

        return sargs, cargs

    if space_params is None:
        for idx in obj.index:
            _, cargs = idx_to_arg(idx if obj.index.nlevels > 1 else (idx,))
            for i, col in enumerate(obj.columns):
                cells = newspace.cells[cells_names[i]]
                cells.set_value(cargs, obj.at[idx, col])
    else:
        for idx in obj.index:
            sargs, cargs = idx_to_arg(idx if obj.index.nlevels > 1 else (idx,))
            for i, col in enumerate(obj.columns):
                subspace = newspace.get_dynspace(sargs)
                cells = subspace.cells[cells_names[i]]
                cells.set_value(cargs, obj.at[idx, col])

    return newspace