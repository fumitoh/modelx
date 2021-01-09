# Copyright (c) 2017-2020 Fumito Hamamura <fumito.ham@gmail.com>

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

import pathlib
from .baseio import BaseDataClient, BaseSharedData
import pandas as pd


class PandasIO(BaseSharedData):

    def __init__(self, path, load_from):
        super().__init__(path, load_from)
        self.is_updated = True  # Not Used

    def _on_save(self, path):
        for c in self.clients.values():     # Only one client
            c._write_pandas(path)


class PandasData(BaseDataClient):
    """ Class for reference pandas objects

    A PandasData object holds a pandas DataFrame or Series object,
    and associates it with a file and format to save the object.

    Args:
        path: Path to a file for saving data. If a relative
            path is given, it is relative to the model folder.
        format(:obj:`str`): String to specify the file format. "excel" or "csv"
        data: a pandas DataFrame or Series.

    See Also:


    """

    data_class = PandasIO

    def __init__(self, path, filetype, data):

        self.path = pathlib.Path(path)
        self._manager = None
        self._data = None
        self.filetype = filetype.lower()
        self._value = data

        self._read_args = {}
        if self.filetype == "excel" or self.filetype == "csv":
            if isinstance(data, pd.DataFrame) and data.columns.nlevels > 1:
                self._read_args["header"] = list(range(data.columns.nlevels))
            if data.index.nlevels > 1:
                self._read_args["index_col"] = list(range(data.index.nlevels))
        else:
            raise ValueError("Pandas IO type not supported")

    def _on_load_value(self):
        pass

    def _on_unpickle(self):
        self._read_pandas()

    def _can_add_other(self, other):
        return False

    def _read_pandas(self):
        if self.filetype == "excel":
            self._value = pd.read_excel(
                self._data.load_from, **self._read_args)
        elif self.filetype == "csv":
            self._value = pd.read_csv(
                self._data.load_from, **self._read_args)
        else:
            raise ValueError

    def _write_pandas(self, path):
        if self.filetype == "excel":
            self._value.to_excel(path)
        elif self.filetype == "csv":
            self._value.to_csv(path)
        else:
            raise ValueError

    @property
    def value(self):
        """pandas DataFrame or Series held in the object"""
        return self._value

    def __call__(self):
        """Returns pandas DataFrame or Series held in the object"""
        return self._value
