# Copyright (c) 2017 Fumito Hamamura <fumito.ham@gmail.com>

# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
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


def space_to_dataframe(space):

    all_params = get_all_params(space.cells.values())
    result = None

    for cells in space.cells.values():
        # params += cells.parameters.keys()

        cells = cells_to_dataframe(cells)

        if cells.index.names != [None]:
            cells = cells.reset_index()

        missing_params = set(all_params) - set(cells)

        for params in missing_params:
            cells[params] = np.nan

        if result is None:
            result = cells
        else:
            result = pd.merge(result, cells, how='outer')

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
        indexes = None

    elif len(cells.parameters) == 1:
        data = {key[0]: value for key, value in cells.data.items()}
        indexes = list(cells.parameters.keys())

    else:
        data = cells.data
        indexes = list(cells.parameters.keys())

    result = pd.Series(data=data, name=cells.name)

    if indexes:
        result.index.names = list(cells.parameters.keys())

    return result



