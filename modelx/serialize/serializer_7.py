# Copyright (c) 2017-2026 Fumito Hamamura <fumito.ham@gmail.com>

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

"""Serializer version 7.

Adds a pseudo-python header comment block to serialized ``__init__.py`` files
on top of serializer 6. The DocstringParser is relaxed so the docstring no
longer needs to start at line 1, allowing the header comments to come first.
"""
import sys
import json
import pathlib
import tempfile
import shutil
import zipfile
import tokenize
import modelx as mx
from . import ziputil
from .deserializer import get_statement_tokens, StatementTokens
from . import serializer_6


PSEUDO_PYTHON_HEADER = """\
# modelx: pseudo-python
# This file is part of a modelx model.
# It can be imported as a Python module, but functions defined herein
# are model formulas and may not be executable as standard Python."""


class ModelEncoder(serializer_6.ModelEncoder):

    def encode(self):
        return PSEUDO_PYTHON_HEADER + "\n\n" + super().encode()


class SpaceEncoder(serializer_6.SpaceEncoder):

    def encode(self):
        return PSEUDO_PYTHON_HEADER + "\n\n" + super().encode()


class DocstringParser(serializer_6.DocstringParser):
    """Docstring at module level. Allows docstrings not on line 1."""
    @classmethod
    def condition(cls, stmt: StatementTokens):
        # stmt has 1 element that is STRING.
        if stmt.section == "DEFAULT" and len(stmt) == 1:
            elm = stmt[0]
            if elm.type == tokenize.STRING:
                return True

        return False


class ParserSelector(serializer_6.BaseSelector):
    classes = [
        DocstringParser,
        serializer_6.ImportFromParser,
        serializer_6.RenameParser,
        serializer_6.LambdaAssignParser,
        serializer_6.LambdaDocstringParser,
        serializer_6.ParentAttrAssignParser,
        serializer_6.CellsAttrAssignParser,
        serializer_6.RefAssignParser,
        serializer_6.SpaceFuncDefParser,
        serializer_6.CellsFuncDefParser
    ]


class ModelWriter(serializer_6.ModelWriter):

    version = 7

    def write_model(self):

        try:
            if self.is_zip:
                tempdir = tempfile.TemporaryDirectory()
                self.temp_root = pathlib.Path(tempdir.name) / self.root.name
                self.work_dir = pathlib.Path(tempdir.name) / (self.root.stem + '_temp')
                self.work_dir.mkdir(parents=True, exist_ok=True)

            self.system.serializing = self
            self.system.iomanager.serializing = True

            ziputil.make_root(self.temp_root, self.is_zip, self.compression, self.compresslevel)
            ziputil.write_str(json.dumps(
                {"modelx_version": mx.VERSION[:3],
                 "serializer_version": self.version}),
                self.temp_root / "_system.json",
                compression=self.compression,
                compresslevel=self.compresslevel)

            encoder = ModelEncoder(
                self, self.model,
                self.temp_root / "__init__.py",
                self.temp_root / "_data")

            self._write_recursive(encoder)
            self.write_pickledata()
            self.system.iomanager.write_ios(self.model, root=self.work_dir)

            if self.log_input:
                ziputil.write_str_utf8(
                    "\n".join(self.input_log),
                    self.temp_root / "_input_log.txt",
                    compression=self.compression,
                    compresslevel=self.compresslevel
                )

            if self.is_zip:
                ziputil.archive_dir(self.work_dir, self.temp_root,
                                    compression=self.compression,
                                    compresslevel=self.compresslevel)
                if self.root.exists() and self.root.is_dir():
                    raise IOError("'%s' is an existing directory" % self.root.name)
                else:
                    shutil.move(self.temp_root, self.root)

        finally:
            self.system.serializing = None
            self.system.iomanager.serializing = None
            if self.is_zip:
                tempdir.cleanup()

    def _write_recursive(self, encoder):

        ziputil.write_str_utf8(encoder.encode(), encoder.srcpath,
                               compression=self.compression,
                               compresslevel=self.compresslevel)

        for space in encoder.target.spaces.values():

            srcpath = (encoder.srcpath.parent / space.name / "__init__.py")

            e = SpaceEncoder(
                self,
                space,
                srcpath=srcpath
                )
            self._write_recursive(e)

        encoder.instruct().execute()


class ModelReader(serializer_6.ModelReader):

    version = ModelWriter.version

    def parse_source(self, path_, obj):

        for stmt in get_statement_tokens(path_):
            parser = ParserSelector.select(stmt)(
                stmt, self, obj, srcpath=path_
            )
            parser.set_instruction()
