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

import ast
from modelx.core.system import mxsys
from modelx.core.base import Interface
from modelx.core.util import abs_to_rel_tuple, rel_to_abs_tuple
from .serializer_2 import Instruction
from .serializer_2 import (
    BaseEncoder,
    BaseSelector,
    LiteralEncoder,
    ModuleEncoder,
    PickleEncoder
)
from .serializer_2 import ModelWriter as ModelWriter2
from .serializer_2 import SpaceWriter as SpaceWriter2
from .serializer_2 import RefViewEncoder as RefViewEncoder2

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
    PickleDecoder,
    LiteralDecoder
)


class TupleID(tuple):

    @classmethod
    def decode(cls):
        pass

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


class SpaceWriter(SpaceWriter2):
    refview_encoder_class = RefViewEncoder


class ModelWriter(ModelWriter2):

    version = 3
    space_writer = SpaceWriter
    refview_encoder_class = RefViewEncoder


class InterfaceRefEncoder(BaseEncoder):

    @classmethod
    def condition(cls, target):
        return isinstance(target, Interface)

    def encode(self):
        tupleid = abs_to_rel_tuple(
            self.target._tupleid,
            self.parent._tupleid
        )

        keys = []
        for key in tupleid:
            if isinstance(key, str):
                keys.append('"%s"' % key)
            elif isinstance(key, tuple):
                keys.append(str(id(key)))

        if len(keys) == 1:
            keystr = "(%s,)" % keys[0]
        else:
            keystr = "(%s)" % ", ".join(keys)

        return "(\"Interface\", %s)" % keystr

    def pickle_value(self):

        tupleid = abs_to_rel_tuple(
            self.target._tupleid,
            self.parent._tupleid
        )
        for key in tupleid:
            if isinstance(key, tuple):
                id_ = id(key)
                if id_ not in self.writer.pickledata:
                    self.writer.pickledata[id_] = key
            elif isinstance(key, str):
                pass
            else:
                raise ValueError("unknown tuple id")

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
    pass


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
    def decode(self):
        return ast.literal_eval(self.atok.get_text(self.node.elts[1]))

    def restore(self):
        # Decode object IDs
        decoded = []
        for key in self.decode():
            if isinstance(key, str):
                decoded.append(key)
            elif isinstance(key, int):
                decoded.append(self.reader.pickledata[key])
            else:
                raise ValueError

        decoded = rel_to_abs_tuple(tuple(decoded), self.obj._tupleid)
        return mxsys.get_object_from_tupleid(decoded)


class DecoderSelector(BaseSelector):
    classes = [
        InterfaceDecoder,
        ModuleDecoder,
        PickleDecoder,
        LiteralDecoder
    ]


RefAssignParser.selector_class = DecoderSelector