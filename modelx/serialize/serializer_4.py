# Copyright (c) 2017-2023 Fumito Hamamura <fumito.ham@gmail.com>

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

import sys
import json, types, importlib, pathlib
import ast
import enum
import shutil
from collections import namedtuple
import tokenize
import token
import tempfile
import zipfile
import modelx as mx
from modelx.core.system import mxsys
from modelx.core.model import Model
from modelx.core.base import Interface
from modelx.core.util import (
    abs_to_rel, rel_to_abs, abs_to_rel_tuple, rel_to_abs_tuple)
from modelx.io.baseio import BaseIOSpec
import asttokens
from . import ziputil
from .custom_pickle import ModelUnpickler, ModelPickler


Section = namedtuple("Section", ["id", "symbol"])
SECTION_DIVIDER = "# " + "-" * 75
SECTIONS = {
    "CELLSDEFS": Section("CELLSDEFS", "# Cells"),
    "REFDEFS": Section("REFDEFS", "# References"),
    "DEFAULT": Section("DEFAULT", "")
}

FROM_FILE_METHODS = [
    "new_space_from_excel",
    "new_cells_from_excel",
    "new_space_from_csv",
    "new_cells_from_csv"
]

FROM_PANDAS_METHODS = [
    "new_space_from_pandas",
    "new_cells_from_pandas"
]

CONSTRUCTOR_METHODS = FROM_FILE_METHODS + FROM_PANDAS_METHODS


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


class PriorityID(enum.IntEnum):
    NORMAL = 1
    AT_PARSE = 2


class SourceStructure:

    def __init__(self, source: str):
        self.source = source
        self.sections = None
        self.construct()

    def construct(self):
        self.sections = {}
        sec = "DEFAULT"
        is_divider_read = False
        for i, line in enumerate(self.source.split("\n")):
            if is_divider_read:
                sec = next(
                    (sec.id for sec in SECTIONS.values()
                     if line.strip() == sec.symbol),
                    "DEFAULT")
                is_divider_read = False
                self.sections[i] = sec
            else:
                if line.strip() == SECTION_DIVIDER:
                    is_divider_read = True

    def get_section(self, lineno):
        sections = list(self.sections.keys())
        secno = next((i for i in reversed(sections) if lineno > i), 0)
        return self.sections[secno] if secno else "DEFAULT"


class BaseInstruction:

    def execute(self):
        raise NotImplementedError


class Instruction(BaseInstruction):

    def __init__(self, func, args=(), arghook=None, kwargs=None, parser=None):

        self.func = func
        self.args = args
        self.arghook = arghook
        self.kwargs = kwargs if kwargs else {}
        self.parser = parser
        self.retval = None

    @classmethod
    def from_method(cls, obj, method, args=(), arghook=None, kwargs=None,
                    parser=None):

        if isinstance(obj, BaseInstruction):
            func = OtherInstFunctor(obj, method)
        else:
            func = getattr(obj, method)
        return cls(func, args=args, arghook=arghook, kwargs=kwargs,
                   parser=parser)

    def execute(self):
        if self.arghook:
            args, kwargs = self.arghook(self)
        else:
            args, kwargs = self.args, self.kwargs

        self.retval = self.func(*args, **kwargs)
        return self.retval

    @property
    def funcname(self):
        return self.func.__name__

    def __repr__(self):
        return "<Instruction: %s>" % self.funcname


class OtherInstFunctor:

    def __init__(self, inst, method):
        self.inst = inst
        self.method = method

    def __call__(self, *args, **kwargs):
        meth = getattr(self.inst.retval, self.method)
        return meth(*args, **kwargs)

    @property
    def __name__(self):
        return self.method


class CompoundInstruction(BaseInstruction):

    def __init__(self, instructions=None):

        self.instructions = []
        self.extend(instructions)
        self.retval = None

    def __len__(self):  # Used by __eq__
        return len(self.instructions)

    def append(self, inst):
        if inst:
            if isinstance(inst, BaseInstruction):
                self.instructions.append(inst)

    def extend(self, instructions):
        if instructions:
            for inst in instructions:
                if inst:  # Not None or empty
                    self.instructions.append(inst)

    def execute(self):
        for inst in self.instructions:
            self.retval = inst.execute()
        return self.retval

    def execute_selected(self, cond, pop_executed=True):

        pos = 0
        while pos < len(self.instructions):

            inst = self.instructions[pos]
            if isinstance(inst, CompoundInstruction):
                inst.execute_selected(cond, pop_executed)
                if inst.instructions:
                    pos += 1
                else:
                    self.instructions.pop(pos)
            else:
                if cond(inst):
                    inst.execute()
                    if pop_executed:
                        self.instructions.pop(pos)
                    else:
                        pos += 1
                else:
                    pos += 1

    def execute_selected_methods(self, methods, pop_executed=True):

        def cond(inst):
            return inst.func.__name__ in methods

        self.execute_selected(cond, pop_executed)

    def execute_selected_parser(self, parser_type, pop_executed=True):

        def cond(inst):
            return isinstance(inst.parser, parser_type)

        self.execute_selected(cond, pop_executed)

    def find_instruction(self, cond):

        for inst in self.instructions:
            if isinstance(inst, CompoundInstruction):
                result = inst.find_instruction(cond)
                if result:
                    return result
            else:
                result = cond(inst)
                if result:
                    return result


# --------------------------------------------------------------------------
# Model Writing

def output_input(obj, key):

    name = obj._get_repr(fullname=True, add_params=False)
    name = name[name.index(".")+1:]
    params = obj.parameters

    arglist = ", ".join(
        "%s=%s" % (param, repr(arg)) for param, arg in
        zip(params, key)
    )

    if obj._impl.has_node:
        return name + "(" + arglist + ")" + "=" + repr(obj(*key))
    else:
        return name + "(" + arglist + ")"


class ModelWriter:

    version = 4

    def __init__(self, system, model: Model, path: pathlib.Path,
                 is_zip: bool,
                 log_input: bool,
                 compression,
                 compresslevel):

        self.system = system
        self.model = model
        self.value_id_map = {}
        self.root = path
        self.temp_root = path   # Put zip in temp dir and copy later (GH82)
        self.work_dir = path    # Sub dir in temp to put IO files before archiving
        self.is_zip = is_zip
        self.call_ids = []
        self.pickledata = {}
        self.method_encoders = []
        self.log_input = log_input
        self.input_log = []
        self.compression = compression
        self.compresslevel = compresslevel

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
            self.call_ids.clear()
            if self.is_zip:
                tempdir.cleanup()

    def _write_recursive(self, encoder):

        ziputil.write_str_utf8(encoder.encode(), encoder.srcpath,
                               compression=self.compression,
                               compresslevel=self.compresslevel)

        for space in encoder.target.spaces.values():

            if (space._is_defined()
                    and not MethodCallEncoder.from_method(space)):
                srcpath = (encoder.srcpath.parent / space.name / "__init__.py")

                e = SpaceEncoder(
                    self,
                    space,
                    srcpath=srcpath
                    )
                self._write_recursive(e)

        encoder.instruct().execute()

    def write_pickledata(self):
        if self.pickledata:
            file = self.temp_root / "_data/data.pickle"
            ziputil.write_file_utf8(
                lambda f: ModelPickler(f, writer=self).dump(self.pickledata),
                file, mode="b",
                compression=self.compression,
                compresslevel=self.compresslevel
            )


class BaseEncoder:

    def __init__(self, writer, target,
                 parent=None, name=None, srcpath=None, datapath=None):
        self.target = target
        self.parent = parent
        self.name = name
        self.srcpath = srcpath
        self.datapath = datapath
        self.writer = writer

    def encode(self):
        raise NotImplementedError

    def instruct(self):
        return None

    @property
    def call_ids(self):
        return self.writer.call_ids

    @property
    def pickledata(self):
        return self.writer.pickledata


class ModelEncoder(BaseEncoder):

    def __init__(self, writer,
                 model: Model, srcpath: pathlib.Path, datapath: pathlib.Path):
        super().__init__(writer, model,
                         parent=None,
                         name=model.name,
                         srcpath=srcpath,
                         datapath=datapath)
        self.model = model

        self.refview_encoder = RefViewEncoder(
            self,
            self.model.refs,
            parent=self.model,
            srcpath=self.srcpath
        )
        self.method_encoders = []
        for space in model.spaces.values():
            if MethodCallEncoder.from_method(space):
                enc = MethodCallSelector.select(space)(
                    self.writer,
                    space,
                    parent=self.model,
                    srcpath=self.srcpath,
                    datapath=self.datapath
                )
                if enc.callid not in self.call_ids:
                    self.method_encoders.append(enc)
                    self.call_ids.append(enc.callid)

    def encode(self):
        lines = []
        if self.model.doc is not None:
            lines.append("\"\"\"" + self.model.doc + "\"\"\"")

        lines.append("from modelx.serialize.jsonvalues import *")
        lines.append("_name = \"%s\"" % self.model.name)
        lines.append("_allow_none = " + str(self.model.allow_none))

        # Output _spaces. Exclude spaces created from methods
        spaces = []
        for name, space in self.model.spaces.items():
            if name[0] == "_":
                pass
            elif MethodCallEncoder.from_method(space):
                pass
            else:
                spaces.append(name)
        lines.append("_spaces = " + json.JSONEncoder(
            ensure_ascii=False,
            indent=4
        ).encode(spaces))
        lines.extend(enc.encode() for enc in self.method_encoders)
        lines.append(self.refview_encoder.encode())
        return "\n\n".join(lines)

    def instruct(self):
        insts = []
        insts.append(self.refview_encoder.instruct())
        insts.extend(e.instruct() for e in self.method_encoders)
        return CompoundInstruction(insts)


class SpaceEncoder(BaseEncoder):

    def __init__(self, writer, target, srcpath=None):
        super().__init__(writer, target, target.parent, target.name, srcpath,
                         datapath=srcpath.parent / "_data")
        self.space = target

        self.refview_encoder = RefViewEncoder(
            self,
            self.space._own_refs,
            parent=self.space,
            srcpath=srcpath
        )

        self.space_method_encoders = []
        for space in self.space.spaces.values():
            encoder = MethodCallSelector.select(space)
            if encoder:
                enc = encoder(
                    self.writer,
                    space,
                    parent=self.space,
                    srcpath=srcpath,
                    datapath=self.datapath
                )
                if enc.callid not in self.call_ids:
                    self.space_method_encoders.append(enc)
                    self.call_ids.append(enc.callid)

        self.cells_method_encoders = []
        for cells in self.space.cells.values():
            encoder = MethodCallSelector.select(cells)
            if encoder:
                enc = encoder(
                    self.writer,
                    cells,
                    parent=self.space,
                    srcpath=srcpath,
                    datapath=self.datapath
                )
                if enc.callid not in self.call_ids:
                    self.cells_method_encoders.append(enc)
                    self.call_ids.append(enc.callid)

        self.cells_encoders = []
        for cells in self.space.cells.values():
            if cells._is_defined():
                if not MethodCallEncoder.from_method(cells):
                    self.cells_encoders.append(
                        CellsEncoder(
                            writer,
                            cells,
                            parent=self.space,
                            name=cells.name,
                            srcpath=srcpath,
                            datapath=self.datapath / cells.name
                        )
                    )

    def encode(self):

        lines = []
        if self.space.doc is not None:
            lines.append("\"\"\"" + self.space.doc + "\"\"\"")

        lines.append("from modelx.serialize.jsonvalues import *")

        # Output formula
        if self.space.formula:
            if self.space.formula.source[:6] == "lambda":
                lines.append("_formula = " + self.space.formula.source)
            else:
                lines.append(self.space.formula.source)
        else:
            lines.append("_formula = None")

        # Output bases
        bases = []
        for base in self.space._direct_bases:
            bases.append(
                abs_to_rel(base._evalrepr, self.parent._evalrepr))
        lines.append("_bases = " + json.JSONEncoder(
            ensure_ascii=False,
            indent=4
        ).encode(bases))

        # Output allow_none
        lines.append("_allow_none = " + str(self.space.allow_none))

        # Output _spaces. Exclude spaces created from methods
        spaces = []
        for name, space in self.space.spaces.items():
            if name[0] == "_":
                pass
            elif MethodCallEncoder.from_method(space):
                pass
            elif space._is_derived():
                pass
            else:
                spaces.append(name)

        lines.append("_spaces = " + json.JSONEncoder(
            ensure_ascii=False,
            indent=4
        ).encode(spaces))
        lines.extend(e.encode() for e in self.space_method_encoders)
        lines.extend(e.encode() for e in self.cells_method_encoders)

        # Cells definitions
        if self.cells_encoders:
            separator = SECTION_DIVIDER + "\n" + SECTIONS["CELLSDEFS"].symbol
            lines.append(separator)
        for encoder in self.cells_encoders:
            lines.append(encoder.encode())

        lines.append(self.refview_encoder.encode())
        return "\n\n".join(lines)

    def instruct(self):
        insts = []
        insts.append(self.refview_encoder.instruct())
        insts.extend(e.instruct() for e in self.space_method_encoders)
        insts.extend(e.instruct() for e in self.cells_method_encoders)
        for encoder in self.cells_encoders:
            insts.append(encoder.instruct())

        insts.append(Instruction(self.pickle_dynamic_inputs))

        return CompoundInstruction(insts)

    def pickle_dynamic_inputs(self):

        datafile = self.datapath / "_dynamic_inputs"

        if self.space._named_itemspaces:

            def callback(f):
                for s in self.space._named_itemspaces.values():
                    self._pickle_dynamic_space(f, s, self.space)

            ziputil.write_file_utf8(callback, datafile, "t",
                                    compression=self.writer.compression,
                                    compresslevel=self.writer.compresslevel)

    def _pickle_dynamic_space(self, file, space, static_parent):

        for cells in space.cells.values():
            for key in cells._impl.input_keys:
                value = cells._impl.data[key]
                keyid = id(key)
                if keyid not in self.writer.pickledata:
                    self.writer.pickledata[keyid] = key
                valid = id(value)
                if valid not in self.writer.pickledata:
                    self.writer.pickledata[valid] = value

                idtuple = TupleID(abs_to_rel_tuple(
                    cells._idtuple, static_parent._idtuple))
                idtuple.pickle_args(self.writer.pickledata)
                file.write(
                    "(%s, %s, %s)\n" % (idtuple.serialize(), keyid, valid)
                )

                if self.writer.log_input:
                    self.writer.input_log.append(
                        output_input(cells, key))

        for subspace in space.named_spaces.values():
            self._pickle_dynamic_space(file, subspace, static_parent)

        for subspace in space._named_itemspaces.values():
            self._pickle_dynamic_space(file, subspace, static_parent)


class RefViewEncoder(BaseEncoder):

    def __init__(self, writer, target, parent, name=None, srcpath=None):
        super().__init__(writer, target, parent, name, srcpath,
                         datapath=srcpath.parent / "_data")

        is_model = isinstance(parent, Model)

        self.encoders = []
        for key, val in self.target.items():
            if key[0] != "_":
                ref = parent._get_object(key, as_proxy=True)
                if (is_model or not ref.is_derived()):
                    datafile = self.datapath / key
                    self.encoders.append(EncoderSelector.select(val)(
                        writer,
                        ref, parent=parent, name=key, srcpath=srcpath,
                        datapath=datafile))

    def encode(self):
        lines = []
        separator = SECTION_DIVIDER + "\n" + SECTIONS["REFDEFS"].symbol
        if self.encoders:
            lines.append(separator)
        for e in self.encoders:
            lines.append(e.name + " = " + e.encode())
        return "\n\n".join(lines)

    def instruct(self):
        return CompoundInstruction(
            [encoder.instruct() for encoder in self.encoders])


class CellsEncoder(BaseEncoder):

    def encode(self):
        lines = []
        if self.target.formula:
            if self.target.formula.source[:6] == "lambda":
                line = self.target.name + " = " + self.target.formula.source
                if self.target.doc:
                    line += "\n" + ("\"\"\"%s\"\"\"" % self.target.doc)
                lines.append(line)
            else:
                lines.append(self.target.formula.source)
        else:
            lines.append(self.target.name + " = None")

        # Output allow_none
        if self.target.allow_none is not None:
            lines.append("_allow_none = " + str(self.target.allow_none))

        return "\n\n".join(lines)

    def pickle_value(self):
        cellsdata = []
        for key in self.target._impl.data:
            if key in self.target._impl.input_keys:
                value = self.target._impl.data[key]
                keyid = id(key)
                if keyid not in self.writer.pickledata:
                    self.writer.pickledata[keyid] = key
                valid = id(value)
                if valid not in self.writer.pickledata:
                    self.writer.pickledata[valid] = value
                cellsdata.append((keyid, valid))

                if self.writer.log_input:
                    self.writer.input_log.append(
                        output_input(self.target, key))

        if cellsdata:   # Save IDs

            def write_dataid(f):
                for keyid, valid in cellsdata:
                    f.write("(%s, %s)\n" % (keyid, valid))

            ziputil.write_file_utf8(write_dataid, self.datapath, "t",
                                    compression=self.writer.compression,
                                    compresslevel=self.writer.compresslevel)

    def instruct(self):
        return Instruction(self.pickle_value)


class MethodCallEncoder(BaseEncoder):

    methods = []
    write_method = None

    def __init__(self, writer,
                 target, parent, name=None, srcpath=None, datapath=None):
        super().__init__(writer, target, parent, name, srcpath, datapath)

    def encode(self):
        raise NotImplementedError

    def instruct(self):
        func = type(self).write_method
        return Instruction(func, args=(self.target, self.srcpath.parent),
                           kwargs={"compression": self.writer.compression,
                                   "compresslevel": self.writer.compresslevel})

    @property
    def callid(self):
        return self.target._impl.source["kwargs"]["call_id"]

    @classmethod
    def from_method(cls, target: Interface):
        src = target._impl.source
        return src and "method" in src and src["method"]

    @classmethod
    def condition(cls, target: Interface):
        src = target._impl.source
        return src and "method" in src and src["method"]


def copy_file(obj, path_: pathlib.Path, compression, compresslevel):
    src = obj._impl.source
    srcpath = pathlib.Path(src["args"][0])
    ziputil.copy_file(
        srcpath,
        path_.joinpath(srcpath.name),
        compression=compression,
        compresslevel=compresslevel
    )


class FromFileEncoder(MethodCallEncoder):

    methods = FROM_FILE_METHODS
    write_method = copy_file

    def encode(self):
        lines = []
        src = self.target._impl.source.copy()
        call_id = src["kwargs"]["call_id"]

        args = list(src["args"])
        args[0] = pathlib.Path(args[0]).name
        src["args"] = args
        lines.append("_method = " + json.JSONEncoder(
            ensure_ascii=False,
            indent=4
        ).encode(src))

        return "\n\n".join(lines)

    @classmethod
    def condition(cls, target):
        if super(FromFileEncoder, cls).condition(target):
            return target._impl.source["method"] in cls.methods
        else:
            return False


def write_pandas(obj, path_: pathlib.Path, filename=None,
                 compression=zipfile.ZIP_DEFLATED,
                 compresslevel=None):
    src = obj._impl.source
    data = src["args"][0]
    if not filename:
        filename = obj.name + ".pandas"
    ziputil.pandas_to_pickle(data, path_.joinpath(filename),
                             compression=compression,
                             compresslevel=compresslevel)


class FromPandasEncoder(MethodCallEncoder):

    methods = FROM_PANDAS_METHODS
    write_method = write_pandas

    def encode(self):
        lines = []
        src = self.target._impl.source.copy()

        args = list(src["args"])
        enc = PickleEncoder(self.writer,
                            args[0],
                            srcpath=self.srcpath,
                            datapath=self.datapath)
        args[0] = enc.datapath.relative_to(
            self.srcpath.parent).as_posix()
        src["args"] = args
        lines.append("_method = " + json.JSONEncoder(
            ensure_ascii=False,
            indent=4
        ).encode(src))

        return "\n\n".join(lines)

    def instruct(self):
        func = type(self).write_method
        return Instruction(func, args=(
            self.target, self.datapath, self.callid),
                           kwargs={"compression": self.writer.compression,
                                   "compresslevel": self.writer.compresslevel})

    @classmethod
    def condition(cls, target):
        if super(FromPandasEncoder, cls).condition(target):
            return target._impl.source["method"] in cls.methods
        else:
            return False


class BaseSelector:
    classes = []

    @classmethod
    def select(cls, *args) -> type:
        return next((e for e in cls.classes if e.condition(*args)), None)


class MethodCallSelector(BaseSelector):
    classes = [
        FromFileEncoder,
        FromPandasEncoder
    ]


class InterfaceRefEncoder(BaseEncoder):

    @classmethod
    def condition(cls, value):
        return isinstance(value, Interface) and value._is_valid()

    def encode(self):
        idtuple = TupleID(abs_to_rel_tuple(
            self.target.value._idtuple,
            self.parent._idtuple
        ))
        if tuple(int(i) for i in mx.__version__.split(".")[:3]) < (0, 10):
            return "(\"Interface\", %s)" % idtuple.serialize()
        else:
            return "(\"Interface\", %s, \"%s\")" % (
                idtuple.serialize(),
                self.target.refmode
            )

    def pickle_value(self):

        idtuple = TupleID(abs_to_rel_tuple(
            self.target.value._idtuple,
            self.parent._idtuple
        ))
        idtuple.pickle_args(self.writer.pickledata)

    def instruct(self):
        return Instruction(self.pickle_value)


class LiteralEncoder(BaseEncoder):
    literal_types = [bool, int, float, str]

    @classmethod
    def condition(cls, value):
        return any(type(value) is t for t in cls.literal_types)

    def encode(self):
        if isinstance(self.target.value, bool):
            return str(self.target.value)
        else:
            return json.dumps(self.target.value, ensure_ascii=False)


class DataClientEncoder(BaseEncoder):

    @classmethod
    def condition(cls, value):

        if not isinstance(value, Interface):    # Avoid null object

            if isinstance(value, BaseIOSpec):
                return True
            elif hasattr(value, "_mx_dataclient") and isinstance(
                    value._mx_dataclient, BaseIOSpec):
                return True

        return False

    def encode(self):
        return "(\"DataClient\", %s)" % self._get_key()

    def _is_hidden(self):
        if isinstance(self.target.value, BaseIOSpec):
            return False
        elif hasattr(self.target.value, "_mx_dataclient"):
            return True
        else:
            raise RuntimeError("must not happen")

    def _get_key(self):
        if self._is_hidden():
            return  id(self.target.value._mx_dataclient)
        else:
            return id(self.target.value)

    def pickle_value(self):
        key = self._get_key()
        if self._is_hidden():
            value = self.target.value._mx_dataclient
        else:
            value = self.target.value

        if key not in self.writer.pickledata:
            self.writer.pickledata[key] = value

    def instruct(self):
        return Instruction(self.pickle_value)


class ModuleEncoder(BaseEncoder):

    @classmethod
    def condition(cls, value):
        return isinstance(value, types.ModuleType)

    def encode(self):
        return "(\"Module\", \"%s\")" % self.target.value.__name__


class PickleEncoder(BaseEncoder):

    @classmethod
    def condition(cls, value):
        return True  # default encoder

    def pickle_value(self):
        value = self.target.value
        key = id(value)
        if key not in self.writer.pickledata:
            self.writer.pickledata[key] = value

    def encode(self):
        return "(\"Pickle\", %s)" % id(self.target.value)

    def instruct(self):
        return Instruction(self.pickle_value)


class EncoderSelector(BaseSelector):

    classes = [
        InterfaceRefEncoder,
        LiteralEncoder,
        DataClientEncoder,
        ModuleEncoder,
        PickleEncoder
    ]

# --------------------------------------------------------------------------
# Model Reading

def _replace_saved_path(space, temppath: str, path: str):

    if not space.is_model():
        if space.source and "args" in space.source:
            if space.source["args"][0] == temppath:
                space.source["args"][0] = path

        for cells in space.cells.values():
            if cells.source and cells.source["args"][0] == temppath:
                cells.source["args"][0] = path

    for child in space.spaces.values():
        _replace_saved_path(child, temppath, path)


def node_from_token(ast_, index):
    return next(
        (n for n in ast_.tree.body if
         n.first_token.index <= index <= n.last_token.index), None)


class ModelReader:

    version = ModelWriter.version

    def __init__(self, system, path: pathlib.Path):
        self.system = system
        self.path = path.resolve()
        self.kwargs = None
        self.instructions = CompoundInstruction()
        self.result = None      # To pass list of space names
        self.model = None
        self.pickledata = None
        self.temproot = None

    def read_model(self, **kwargs):

        try:
            self.system.serializing = self
            self.system.iomanager.serializing = True
            self.kwargs = kwargs

            if (sys.platform == "win32"
                    and sys.version_info >= (3, 10)
                    and zipfile.is_zipfile(self.path)):
                # workaround for https://github.com/python/cpython/issues/74168
                with tempfile.TemporaryDirectory(
                        ignore_cleanup_errors=True
                ) as tempdir:
                    self.temproot = pathlib.Path(tempdir)
                    model = self._read_model_inner()
                self.temproot = None
            elif zipfile.is_zipfile(self.path):
                with tempfile.TemporaryDirectory() as tempdir:
                    self.temproot = pathlib.Path(tempdir)
                    model = self._read_model_inner()
                self.temproot = None
            else:
                model = self._read_model_inner()

        except:
            if self.model:
                self.model.close()
            raise

        finally:
            self.system.serializing = None
            self.system.iomanager.serializing = None

        return model

    def _read_model_inner(self):

        model = self.parse_dir()
        self.instructions.execute_selected_methods([
            "doc",
            "set_formula",
            "set_property",
            "new_cells",
            "set_doc"
        ])

        if self.instructions.find_instruction(
                lambda inst: isinstance(inst.parser, MethodCallParser)
        ):
            self.instructions.execute_selected_parser(MethodCallParser)

        self.instructions.execute_selected_methods(["add_bases"])
        self.read_pickledata()
        self.instructions.execute_selected_methods(["load_pickledata"])
        self.instructions.execute_selected_methods(["__setattr__", "set_ref"])
        self.instructions.execute_selected_methods(
            ["_set_dynamic_inputs"])

        return model

    def parse_dir(self, path_: pathlib.Path = None, target=None, spaces=None):

        if target is None:
            path_ = self.path
            target = self.model = mx.new_model()
            self.parse_source(path_ / "__init__.py", self.model)
            spaces = self.result

        for name in spaces:
            space = target.new_space(name=name)
            self.parse_source(path_ / name / "__init__.py", space)
            nextdir = path_ / name
            self._parse_dynamic_inputs(nextdir, space)
            if ziputil.exists(nextdir) and ziputil.is_dir(nextdir):
                self.parse_dir(nextdir, target=space, spaces=self.result)

        return target

    def _parse_dynamic_inputs(self, path_, static_parent):

        file = path_ / "_data/_dynamic_inputs"
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
                    args + (static_parent,)
                )
                instructuions.append(inst)
            self.instructions.extend(instructuions)

    def _set_dynamic_inputs(self, idtuple, keyid, valid, static_parent):
        idtuple = TupleID.unpickle_args(idtuple, self.pickledata)
        if idtuple[0][0] == ".":    # Backward compatibility (-0.13.0)
            idtuple = rel_to_abs_tuple(idtuple, static_parent._idtuple)
        cells = mxsys.get_object_from_idtuple(idtuple)
        key = self.pickledata[keyid]
        value = self.pickledata[valid]
        cells._impl.set_value(key, value)

    def parse_source(self, path_, obj: Interface):

        src = ziputil.read_str_utf8(path_)
        srcstructure = SourceStructure(src)
        atok = asttokens.ASTTokens(src, parse=True)

        for i, stmt in enumerate(atok.tree.body):
            sec = srcstructure.get_section(stmt.lineno)
            parser = ParserSelector.select(stmt, sec, atok)(
                stmt, atok, self, sec, obj, srcpath=path_
            )
            ist = parser.get_instruction()
            if parser.priority == PriorityID.AT_PARSE:
                ist.execute()
            else:
                self.instructions.append(ist)

    def read_pickledata(self):

        def custom_load(file):
            unpickler = ModelUnpickler(file, self)
            return unpickler.load()

        def compat_load(file):
            from .pandas_compat import CompatUnpickler
            return CompatUnpickler(file, self).load()

        file = self.path / "_data/data.pickle"
        if ziputil.exists(file):
            excs_to_catch = (
                AttributeError, ImportError, ModuleNotFoundError, TypeError)
            try:
                self.pickledata = ziputil.read_file_utf8(
                    custom_load, file, "b")
            except excs_to_catch:
                self.pickledata = ziputil.read_file_utf8(
                    compat_load, file, "b")


class BaseNodeParser:
    AST_NODE = None
    default_priority = PriorityID.NORMAL

    def __init__(self, node, atok, reader, section, obj, srcpath, **kwargs):
        self.node = node
        self.atok = atok
        self.reader = reader
        self.section = section
        self.obj = obj
        self.impl = obj._impl
        self.srcpath = srcpath
        self.kwargs = kwargs
        self.priority = self.default_priority

    @classmethod
    def condition(cls, node, section, atok):
        return isinstance(node, cls.AST_NODE)

    def get_instruction(self):
        raise NotImplementedError


class DocstringParser(BaseNodeParser):
    AST_NODE = ast.Expr

    @classmethod
    def condition(cls, node, section, atok):
        if isinstance(node, cls.AST_NODE):
            if isinstance(node.value, ast.Str):
                return True

        return False

    def get_instruction(self):
        if self.section == "DEFAULT":
            return Instruction.from_method(
                obj=type(self.obj).doc,
                method="fset",
                args=(self.obj, self.node.value.s)
            )
        else:   # Cells.doc for lambda is processed by LambdaAssignParser
            return None


class ImportFromParser(BaseNodeParser):
    AST_NODE = ast.ImportFrom

    def get_instruction(self):
        return  # Skip any import from statement


class BaseAssignParser(BaseNodeParser):
    AST_NODE = ast.Assign

    @property
    def target(self):
        return self.node.first_token.string

    def get_instruction(self):
        raise NotImplementedError


class RenameParser(BaseAssignParser):

    default_priority = PriorityID.AT_PARSE

    @classmethod
    def condition(cls, node, section, atok):

        if not super(RenameParser, cls).condition(node, section, atok):
            return False
        if node.first_token.string == "_name":
            return True
        return False

    def get_instruction(self):

        method = "rename"
        if "name" in self.reader.kwargs and self.reader.kwargs["name"]:
            val = self.reader.kwargs["name"]
        else:
            val = ast.literal_eval(self.atok.get_text(self.node.value))

        kwargs = {"rename_old": True}

        return Instruction.from_method(
                obj=self.obj,
                method=method,
                args=(val,),
                kwargs=kwargs)


class MethodCallParser(BaseAssignParser):

    @classmethod
    def condition(cls, node, section, atok):
        if isinstance(node, cls.AST_NODE) and section == "DEFAULT":
            if node.first_token.string == "_method":
                return True
        return False


def filehook(inst):     # Not in use
    args, kwargs = inst.args, inst.kwargs
    args[0] = str(inst.kwargs["path_"].with_name(args[0]))
    return args, kwargs


class FromFileParser(MethodCallParser):

    def get_instruction(self):

        method = json.loads(
            self.atok.get_text(self.node.value)
        )
        args = method.pop("args")
        args[0] = str(self.srcpath.with_name(args[0]))

        def exec_from_file(*args, **kwargs):

            tempargs = list(args)

            if self.reader.temproot:
                srcpath = pathlib.Path(args[0])
                rel = srcpath.relative_to(self.reader.path)
                temppath = self.reader.temproot.joinpath(rel)
                tempargs[0] = str(temppath)
                ziputil.copy_file(srcpath, temppath)

            func = getattr(self.impl, method["method"])
            func(*tempargs, **kwargs)
            if self.reader.temproot:
                _replace_saved_path(self.impl, tempargs[0], args[0])

        return Instruction(
            func=exec_from_file,
            args=args,
            kwargs=method["kwargs"],
            parser=self
        )


def pandashook(inst):
    import pandas as pd
    args, kwargs = inst.args, inst.kwargs
    args[0] = pd.read_pickle(args[0])
    return args, kwargs


class FromPandasParser(MethodCallParser):

    @classmethod
    def condition(cls, node, section, atok):
        if super(FromPandasParser, cls).condition(node, section, atok):
            method = json.loads(
                atok.get_text(node.value)
            )
            if method["method"] in FROM_PANDAS_METHODS:
                return True

        return False

    def get_instruction(self):

        method = json.loads(
            self.atok.get_text(self.node.value)
        )
        args = method.pop("args")
        callid = method["kwargs"]["call_id"]
        args[0] = str(self.srcpath.parent.joinpath(args[0]) / callid)

        def exec_from_pandas(*args, **kwargs):

            newargs = list(args)

            if self.reader.temproot:
                srcpath = pathlib.Path(args[0])
                rel = srcpath.relative_to(self.reader.path)
                temppath = self.reader.temproot.joinpath(rel)
                newargs[0] = str(temppath)
                ziputil.copy_file(srcpath, temppath)

            import pandas as pd
            newargs[0] = pd.read_pickle(newargs[0])
            func = getattr(self.impl, method["method"])
            func(*newargs, **kwargs)

        return Instruction(
            func=exec_from_pandas,
            args=args,
            kwargs=method["kwargs"],
            arghook=None,
            parser=self
        )


class AttrAssignParser(BaseAssignParser):

    @classmethod
    def condition(cls, node, section, atok):
        if isinstance(node, cls.AST_NODE) and (
                section == "DEFAULT" or section == "CELLSDEFS"):
            return True
        return False

    def get_instruction(self):

        if self.target == "_formula":
            # lambda formula definition
            method = "set_formula"
            val = self.atok.get_text(self.node.value)
            if val == "None":
                val = None

            kwargs = {"formula": val}
            return Instruction.from_method(
                    obj=self.impl,
                    method=method,
                    kwargs=kwargs
                )

        elif self.target == "_bases":

            bases = [
                rel_to_abs(base, self.obj.parent.fullname)
                for base in ast.literal_eval(
                    self.atok.get_text(self.node.value))
            ]

            def bases_hook(inst):
                args = [mx.get_object(base) for base in inst.args]
                return args, inst.kwargs

            return Instruction.from_method(
                obj=self.obj,
                method="add_bases",
                args=bases,
                arghook=bases_hook)

        elif self.target == "_spaces":
            self.reader.result = json.loads(
                self.atok.get_text(self.node.value)
            )
            return

        elif self.target == "_allow_none":
            if self.section == "DEFAULT":
                value = ast.literal_eval(self.atok.get_text(self.node.value))
                return Instruction.from_method(
                    obj=self.obj,
                    method="set_property",
                    args=("allow_none", value))
            else:
                # Cells.allow_none is processed
                # by LambdaAssignParser and CellsFuncDefParser
                return

        else:
            raise RuntimeError("unknown attribute assignment")


class RefAssignParser(BaseAssignParser):
    AST_NODE = ast.Assign

    @classmethod
    def condition(cls, node, section, atok):
        if isinstance(node, cls.AST_NODE) and section == "REFDEFS":
            return True
        return False

    def get_instruction(self):

        name = self.target
        valnode = self.node.value

        decoder_class = DecoderSelector.select(valnode)
        decoder = decoder_class(
            self.reader, valnode, self.atok,
            self.obj, name=name, srcpath=self.srcpath)

        if hasattr(decoder, "restore"):
            def restore_hook(inst):
                dec = inst.args[1]
                return (inst.args[0], dec.restore()), inst.kwargs

            value = decoder
            arghook = restore_hook
        else:
            value = decoder.decode()
            arghook = None

        if (isinstance(self.obj, Model)
                or not isinstance(decoder, TupleDecoder)
                or decoder.size() < 3):
            setter = Instruction.from_method(
                obj=self.obj,
                method="__setattr__",
                args=(name, value),
                arghook=arghook
            )
        else:
            refmode = decoder.elm(2)
            setter = Instruction.from_method(
                obj=self.obj,
                method="set_ref",
                args=(name, value),
                arghook=arghook,
                kwargs={'refmode': refmode}
            )

        return setter


class CellsInputDataMixin(BaseNodeParser):

    @property
    def cellsname(self):
        raise NotImplementedError

    @property
    def datapath(self) -> pathlib.Path:
        return self.srcpath.parent / "_data" / self.cellsname

    def set_values(self, data):
        cells = self.impl.cells[self.cellsname]
        for key, val in data.items():
            cells.set_value(key, val)

    def load_pickledata(self):
        if ziputil.exists(self.datapath):
            data = {}
            lines = ziputil.read_file_utf8(lambda f: f.readlines(),
                                      self.datapath,
                                      "t")
            for line in lines:
                keyid, valid = ast.literal_eval(line)
                key = self.reader.pickledata[keyid]
                val = self.reader.pickledata[valid]
                data[key] = val
            self.set_values(data)


if sys.version_info < (3, 7):
    def skip_blank_tokens(tokens, idx):
        # There may be trailing comments that must be skipped.
        # See FunctionDefParser
        while (tokens[idx].type == token.NEWLINE or
               tokens[idx].type == token.INDENT or
               tokens[idx].type == token.DEDENT or
               tokens[idx].string == "\n"   # token 58 (TYPE_COMMENT?)
        ):
            idx += 1
        return idx
else:
    def skip_blank_tokens(tokens, idx):
        # There may be trailing comments that must be skipped.
        # See FunctionDefParser
        while (tokens[idx].type == token.NEWLINE or
               tokens[idx].type == token.INDENT or
               tokens[idx].type == token.DEDENT or
               tokens[idx].type == token.NL or      # New in Python 3.7
               tokens[idx].type == token.COMMENT):  # New in Python 3.7
            idx += 1
        return idx


class LambdaAssignParser(BaseAssignParser, CellsInputDataMixin):

    @classmethod
    def condition(cls, node, section, atok):
        # Exclude assignments of names starting "_"
        if isinstance(node, cls.AST_NODE) and section == "CELLSDEFS" and (
            node.targets[0].id[0] != "_"
        ):
            return True
        return False

    @property
    def cellsname(self):
        return self.atok.get_text(self.node.targets[0])

    def get_instruction(self):
        kwargs = {
            "name": self.cellsname,
            "formula": self.atok.get_text(self.node.value)
        }
        # lambda cells definition
        inst = Instruction.from_method(
            obj=self.obj,
            method="new_cells",
            kwargs=kwargs
        )

        # find doc
        next_idx = skip_blank_tokens(
            self.atok.tokens, self.node.last_token.index + 1)
        next_node = node_from_token(self.atok, next_idx)

        compinst = [inst]
        if self.atok.tokens[next_idx].type == token.STRING:
            doc = ast.literal_eval(self.atok.tokens[next_idx].string)
            inst_doc = Instruction.from_method(
                obj=inst,
                method="set_doc",
                kwargs={'doc': doc}
            )
            compinst.append(inst_doc)

            next_idx = skip_blank_tokens(
                self.atok.tokens, next_idx + 1)
            next_node = node_from_token(self.atok, next_idx)

            if isinstance(next_node, ast.Assign) and (
                    next_node.first_token.string == "_allow_none"):
                value = ast.literal_eval(self.atok.get_text(next_node.value))
                inst_allow_none = Instruction.from_method(
                    obj=inst,
                    method="set_property",
                    args=("allow_none", value)
                )
                compinst.append(inst_allow_none)

        elif isinstance(next_node, ast.Assign) and (
                next_node.first_token.string == "_allow_none"):
            value = ast.literal_eval(self.atok.get_text(next_node.value))
            inst_allow_none = Instruction.from_method(
                obj=inst,
                method="set_property",
                args=("allow_none", value)
            )
            compinst.append(inst_allow_none)

        compinst.append(Instruction(self.load_pickledata))
        return CompoundInstruction(compinst)


class FunctionDefParser(BaseNodeParser):
    AST_NODE = ast.FunctionDef
    METHOD = None

    def get_instruction(self):

        funcdef = self.atok.get_text(self.node)

        # The code below is just for adding back comment in the last line
        # such as:
        # def foo():
        #     return 0  # Comment
        nxtok = self.node.last_token.index + 1
        if nxtok < len(self.atok.tokens) and (
                self.atok.tokens[nxtok].type == tokenize.COMMENT
        ) and self.node.last_token.line == self.atok.tokens[nxtok].line:
            deflines = funcdef.splitlines()
            deflines.pop()
            deflines.append(self.node.last_token.line.rstrip())
            funcdef = "\n".join(deflines)

        kwargs = {"formula": funcdef}
        return Instruction.from_method(
            obj=self.obj,
            method=self.METHOD,
            kwargs=kwargs
        )


class SpaceFuncDefParser(FunctionDefParser):

    METHOD = "set_formula"

    @classmethod
    def condition(cls, node, section, atok):
        if super(SpaceFuncDefParser, cls).condition(node, section, atok):
            if node.name == "_formula":
                return True
        return False


class CellsFuncDefParser(FunctionDefParser, CellsInputDataMixin):

    METHOD = "new_cells"

    @property
    def cellsname(self):
        return self.node.name

    def get_instruction(self):

        inst = super().get_instruction()
        compinst = [inst]

        next_idx = skip_blank_tokens(
            self.atok.tokens, self.node.last_token.index + 1)
        next_node = node_from_token(self.atok, next_idx)

        if isinstance(next_node, ast.Assign) and (
                next_node.first_token.string == "_allow_none"):
            value = ast.literal_eval(self.atok.get_text(next_node.value))
            inst_allow_none = Instruction.from_method(
                obj=inst,
                method="set_property",
                args=("allow_none", value)
            )
            compinst.append(inst_allow_none)

        compinst.append(Instruction(self.load_pickledata))
        return CompoundInstruction(compinst)


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


class ValueDecoder:

    def __init__(self, reader, node, atok, obj, name=None, srcpath=None):
        self.reader = reader
        self.node = node
        self.atok = atok
        self.obj = obj
        self.name = name
        self.srcpath = srcpath

    def decode(self):
        raise NotImplementedError


class TupleDecoder(ValueDecoder):
    DECTYPE = None

    def elm(self, index, decoder=ast.literal_eval):
        return decoder(self.atok.get_text(self.node.elts[index]))

    def size(self):
        return len(self.node.elts)

    @classmethod
    def condition(cls, node):
        if isinstance(node, ast.Tuple):
            if node.elts[0].s == cls.DECTYPE:
                return True
        return False


class InterfaceDecoder(TupleDecoder):
    DECTYPE = "Interface"

    def decode(self):
        return rel_to_abs(self.elm(1), self.obj.fullname)

    def restore(self):
        decoded = TupleID.unpickle_args(
            TupleID.tuplize(self.atok.get_text(self.node.elts[1])),
            self.reader.pickledata
        )
        decoded = rel_to_abs_tuple(decoded, self.obj._idtuple)
        return mxsys.get_object_from_idtuple(decoded)


class DataClientDecoder(TupleDecoder):
    DECTYPE = "DataClient"

    def decode(self):
        return self.elm(1)

    def restore(self):
        spec = self.reader.pickledata[self.decode()]
        if hasattr(spec, "_is_hidden") and spec._is_hidden:
            return spec.value
        else:
            return spec


class ModuleDecoder(TupleDecoder):
    DECTYPE = "Module"

    def decode(self):
        return importlib.import_module(self.elm(1))


class PickleDecoder(TupleDecoder):
    DECTYPE = "Pickle"

    def decode(self):
        return self.elm(1)

    def restore(self):
        return self.reader.pickledata[self.decode()]


class LiteralDecoder(ValueDecoder):

    @classmethod
    def condition(cls, node):
        return True

    def decode(self):
        return ast.literal_eval(self.node)


class DecoderSelector(BaseSelector):
    classes = [
        InterfaceDecoder,
        DataClientDecoder,
        ModuleDecoder,
        PickleDecoder,
        LiteralDecoder
    ]


if __name__ == "__main__":
    import doctest

    doctest.testmod()
