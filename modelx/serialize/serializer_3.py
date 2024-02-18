# Copyright (c) 2017-2024 Fumito Hamamura <fumito.ham@gmail.com>

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

import ast
from modelx.core.system import mxsys
from modelx.core.base import Interface
from modelx.core.util import abs_to_rel_tuple, rel_to_abs_tuple
from .serializer_2 import Instruction
from .serializer_2 import (
    BaseEncoder,
    BaseSelector,
    LiteralEncoder,
    ModuleEncoder
)
from .serializer_2 import ModelWriter as ModelWriter2
from .serializer_2 import ModelEncoder as ModelEncoder2
from .serializer_2 import SpaceEncoder as SpaceEncoder2
from .serializer_2 import RefViewEncoder as RefViewEncoder2
from .serializer_2 import PickleEncoder as PickleEncoder2

from .serializer_2 import ModelReader as ModelReader2
from .serializer_2 import RefAssignParser as RefAssignParser2

from .serializer_2 import (
    DocstringParser,
    ImportFromParser,
    RenameParser,
    FromPandasParser,
    FromFileParser,
    LambdaAssignParser,
    AttrAssignParser,
    SpaceFuncDefParser,
    CellsFuncDefParser
)

from .serializer_2 import (
    TupleDecoder,
    ModuleDecoder,
    LiteralDecoder
)
from .serializer_2 import PickleDecoder as PickleDecoder2
from .serializer_2 import output_input
from . import ziputil


class TupleID(tuple):

    @classmethod
    def tuplize(cls, expr):
        return ast.literal_eval(expr)

    @classmethod
    def unpickle_args(cls, keys, argsdict):

        decoded = []
        for key in keys:
            if isinstance(key, str):
                decoded.append(key)
            elif isinstance(key, int):
                decoded.append(argsdict[key])
            else:
                raise ValueError

        return tuple(decoded)

    def serialize(self):
        keys = []
        for key in self:
            if isinstance(key, str):
                keys.append('"%s"' % key)
            elif isinstance(key, tuple):
                keys.append(str(id(key)))

        if len(keys) == 1:
            keystr = "(%s,)" % keys[0]
        else:
            keystr = "(%s)" % ", ".join(keys)

        return keystr

    def pickle_args(self, argsdict):
        for key in self:
            if isinstance(key, tuple):
                id_ = id(key)
                if id_ not in argsdict:
                    argsdict[id_] = key
            elif isinstance(key, str):
                pass
            else:
                raise ValueError("unknown tuple id")


class RefViewEncoder(RefViewEncoder2):
    pass


class SpaceEncoder(SpaceEncoder2):
    refview_encoder_class = RefViewEncoder

    def pickle_dynamic_inputs(self):

        datafile = self.datapath / "_dynamic_inputs"

        if self.space._named_itemspaces:

            def callback(f):
                for s in self.space._named_itemspaces.values():
                    self._pickle_dynamic_space(f, s)

            ziputil.write_file_utf8(callback, datafile, "t")

    def _pickle_dynamic_space(self, file, space):

        for cells in space.cells.values():
            for key in cells._impl.input_keys:
                value = cells._impl.data[key]
                keyid = id(key)
                if keyid not in self.writer.pickledata:
                    self.writer.pickledata[keyid] = key
                valid = id(value)
                if valid not in self.writer.pickledata:
                    self.writer.pickledata[valid] = value

                idtuple = TupleID(cells._idtuple)
                idtuple.pickle_args(self.writer.pickledata)
                file.write(
                    "(%s, %s, %s)\n" % (idtuple.serialize(), keyid, valid)
                )

                if self.writer.log_input:
                    self.writer.input_log.append(
                        output_input(cells, key))

        for subspace in space.named_spaces.values():
            self._pickle_dynamic_space(file, subspace)

        for subspace in space._named_itemspaces.values():
            self._pickle_dynamic_space(file, subspace)

    def instruct(self):
        inst = super().instruct()
        inst.append(Instruction(self.pickle_dynamic_inputs))
        return inst


class ModelEncoder(ModelEncoder2):

    refview_encoder_class = RefViewEncoder


class ModelWriter(ModelWriter2):

    version = 3
    space_encoder = SpaceEncoder
    model_encoder = ModelEncoder


class InterfaceRefEncoder(BaseEncoder):

    @classmethod
    def condition(cls, target):
        return isinstance(target, Interface)

    def encode(self):
        idtuple = TupleID(abs_to_rel_tuple(
            self.target._idtuple,
            self.parent._idtuple
        ))
        return "(\"Interface\", %s)" % idtuple.serialize()

    def pickle_value(self):

        idtuple = TupleID(abs_to_rel_tuple(
            self.target._idtuple,
            self.parent._idtuple
        ))
        idtuple.pickle_args(self.writer.pickledata)

    def instruct(self):
        return Instruction(self.pickle_value)


class PickleEncoder(PickleEncoder2):

    def pickle_value(self):
        value = self.target
        key = id(value)
        if key not in self.writer.pickledata:
            self.writer.pickledata[key] = value

    def encode(self):
        return "(\"Pickle\", %s)" % id(self.target)

    def instruct(self):
        return Instruction(self.pickle_value)


class EncoderSelector(BaseSelector):
    classes = [
        InterfaceRefEncoder,
        LiteralEncoder,
        ModuleEncoder,
        PickleEncoder
    ]


RefViewEncoder.selector_class = EncoderSelector

# --------------------------------------------------------------------------
# Model Reading


class ModelReader(ModelReader2):

    version = ModelWriter.version
    def _parse_dynamic_inputs(self, path_):

        file = path_ / "data/_dynamic_inputs"
        if ziputil.exists(file):

            lines = ziputil.read_file_utf8(
                lambda f: f.readlines(),
                file,
                "t"
            )

            instructuions = []
            for line in lines:
                args = ast.literal_eval(line)
                inst = Instruction(
                    self._set_dynamic_inputs,
                    args
                )
                instructuions.append(inst)
            self.instructions.extend(instructuions)

    def _set_dynamic_inputs(self, idtuple, keyid, valid):
        idtuple = TupleID.unpickle_args(idtuple, self.pickledata)
        cells = mxsys.get_object_from_idtuple(idtuple)
        key = self.pickledata[keyid]
        value = self.pickledata[valid]
        cells._impl.set_value(key, value)


class RefAssignParser(RefAssignParser2):
    pass


class ParserSelector(BaseSelector):
    classes = [
        DocstringParser,
        ImportFromParser,
        RenameParser,
        FromPandasParser,
        FromFileParser,
        LambdaAssignParser,
        AttrAssignParser,
        RefAssignParser,
        SpaceFuncDefParser,
        CellsFuncDefParser
    ]


ModelReader.parser_selector_class = ParserSelector


class InterfaceDecoder(TupleDecoder):
    DECTYPE = "Interface"

    def restore(self):
        decoded = TupleID.unpickle_args(
            TupleID.tuplize(self.atok.get_text(self.node.elts[1])),
            self.reader.pickledata
        )
        decoded = rel_to_abs_tuple(decoded, self.obj._idtuple)
        return mxsys.get_object_from_idtuple(decoded)


class PickleDecoder(PickleDecoder2):

    def decode(self):
        return self.elm(1)

    def restore(self):
        return self.reader.pickledata[self.decode()]


class DecoderSelector(BaseSelector):
    classes = [
        InterfaceDecoder,
        ModuleDecoder,
        PickleDecoder,
        LiteralDecoder
    ]


RefAssignParser.selector_class = DecoderSelector