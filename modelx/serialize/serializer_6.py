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

import sys
import json, types, importlib, pathlib
import ast
import enum
import shutil
from types import MethodType, FunctionType
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
from modelx.core.api import _new_cells_keep_source
from . import ziputil
from .deserializer import (
    get_statement_tokens, StatementTokens, SECTION_DIVIDER, SECTIONS)
from .custom_pickle import (
    IOSpecUnpickler, ModelUnpickler,
    IOSpecPickler, ModelPickler)


class TupleID(tuple):

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

    def __init__(self, func, args=(), arghook=None, kwargs=None, parser=None, priority=0):

        self.func = func
        self.args = args
        self.arghook = arghook
        self.kwargs = kwargs if kwargs else {}
        self.parser = parser
        self.retval = None
        self.priority = priority    # Order priority in compound instructions

    @classmethod
    def from_method(cls, obj, method, args=(), arghook=None, kwargs=None,
                    parser=None, priority=0):

        if isinstance(obj, BaseInstruction):
            func = OtherInstFunctor(obj, method)
        else:
            func = getattr(obj, method)
        return cls(func, args=args, arghook=arghook, kwargs=kwargs,
                   parser=parser, priority=priority)

    @property
    def obj(self):
        if isinstance(self.func, MethodType):
            return self.func.__self__
        elif isinstance(self.func, FunctionType):
            return self.args[0]
        elif isinstance(self.func, OtherInstFunctor):
            raise ValueError("must not happen")
        else:
            raise ValueError("no object is associated with instruction")

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

    @property
    def obj(self):
        return self.inst.retval


class CompoundInstruction(BaseInstruction):

    def __init__(self, instructions=None):

        self.instructions = []
        self.extend(instructions)
        self.retval = None

    def __len__(self):  # Used by __eq__
        return len(self.instructions)

    @property
    def funcname(self):
        return self.instructions[0].func.__name__

    @property
    def obj(self):
        return self.instructions[0].obj

    @property
    def last(self):
        return self.instructions[-1]

    def append(self, inst):
        assert inst
        assert isinstance(inst, BaseInstruction)
        self.instructions.append(inst)

    def extend(self, instructions):
        if instructions:
            for inst in instructions:
                if inst:  # Not None or empty
                    self.instructions.append(inst)

    def execute(self):

        first = True
        for inst in self.instructions:
            if first:
                self.retval = inst.execute()
                first = False
            else:
                inst.execute()
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
                    retval = inst.execute()
                    if inst.priority == 0:
                        self.retval = retval
                    if pop_executed:
                        self.instructions.pop(pos)
                    else:
                        pos += 1
                else:
                    pos += 1

    def execute_selected_methods(self, methods, pop_executed=True):

        def cond(inst):
            return inst.funcname in methods

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

    version = 6

    def __init__(self, system, model: Model, path: pathlib.Path,
                 is_zip: bool,
                 log_input: bool,
                 compression,
                 compresslevel):

        self.system = system
        self.model = model
        self.iospecs = {id(sp): sp for sp in self.model.iospecs}
        self.value_id_map = {   # id(value) -> id(iospec)
            id(sp.value): id(sp) for sp in self.model.iospecs}
        self.root = path
        self.temp_root = path   # Put zip in temp dir and copy later (GH82)
        self.work_dir = path    # Sub dir in temp to put IO files before archiving
        self.is_zip = is_zip
        self.pickledata = {}
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

    def write_pickledata(self):
        if self.model.iospecs:
            file = self.temp_root / "_data/iospecs.pickle"
            ziputil.write_file_utf8(
                lambda f: IOSpecPickler(f).dump(self.iospecs),
                file, mode="b",
                compression=self.compression,
                compresslevel=self.compresslevel
            )
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
            self.writer,
            self.model.refs,
            parent=self.model,
            srcpath=self.srcpath
        )

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
            else:
                spaces.append(name)
        lines.append("_spaces = " + json.JSONEncoder(
            ensure_ascii=False,
            indent=4
        ).encode(spaces))
        lines.append(self.refview_encoder.encode())
        return "\n\n".join(lines)

    def instruct(self):
        insts = []
        insts.append(self.refview_encoder.instruct())
        return CompoundInstruction(insts)


class SpaceEncoder(BaseEncoder):

    def __init__(self, writer, target, srcpath=None):
        super().__init__(writer, target, target.parent, target.name, srcpath,
                         datapath=srcpath.parent / "_data")
        self.space = target

        self.refview_encoder = RefViewEncoder(
            self.writer,
            self.space._own_refs,
            parent=self.space,
            srcpath=srcpath
        )

        self.cells_encoders = []
        for cells in self.space.cells.values():
            if cells._is_defined():
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
            else:
                spaces.append(name)

        lines.append("_spaces = " + json.JSONEncoder(
            ensure_ascii=False,
            indent=4
        ).encode(spaces))

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
                    self.encoders.append(EncoderSelector.select(ref, writer)(
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

        # Output is_cached
        if self.target.is_cached == False:
            lines.append("_is_cached = False")

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


class BaseSelector:
    classes = []

    @classmethod
    def select(cls, *args) -> type:
        return next((e for e in cls.classes if e.condition(*args)), None)


class InterfaceRefEncoder(BaseEncoder):

    @classmethod
    def condition(cls, ref, writer):
        value = ref.value
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
    literal_types = [bool, int, float, str, type(None)]

    @classmethod
    def condition(cls, ref, writer):
        value = ref.value
        return any(type(value) is t for t in cls.literal_types)

    def encode(self):
        # True, False, None
        if isinstance(self.target.value, bool) or isinstance(self.target.value, type(None)):
            return str(self.target.value)
        else:
            return json.dumps(self.target.value, ensure_ascii=False)


class IOSpecEncoder(BaseEncoder):

    @classmethod
    def condition(cls, ref, writer):

        if not isinstance(ref, Interface): # Avoid null object
            return id(ref.value) in writer.value_id_map
        else:
            return False

    def encode(self):
        value_id = id(self.target.value)
        spec_id = self.writer.value_id_map[value_id]
        return "(\"IOSpec\", %s, %s)" % (value_id, spec_id)

    def pickle_value(self):
        key = id(self.target.value)

        if key not in self.writer.pickledata:
            self.writer.pickledata[key] = self.target.value

    def instruct(self):
        return Instruction(self.pickle_value)


class ModuleEncoder(BaseEncoder):

    @classmethod
    def condition(cls, ref, writer):
        value = ref.value
        if id(value) in writer.value_id_map:   # Use PickleEncoder
            return False
        else:
            return isinstance(value, types.ModuleType)

    def encode(self):
        return "(\"Module\", \"%s\")" % self.target.value.__name__


class PickleEncoder(BaseEncoder):

    @classmethod
    def condition(cls, ref, writer):
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
        IOSpecEncoder,
        ModuleEncoder,
        PickleEncoder
    ]

# --------------------------------------------------------------------------
# Model Reading


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
        self.iospecs = None
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
            "_new_cells_keep_source",
            "new_cells",
            "set_doc"
        ])
        self.instructions.execute_selected_methods(["add_bases"])
        self.read_pickledata()
        self.instructions.execute_selected_methods(["load_pickledata"])
        self.instructions.execute_selected_methods(
            ["__setattr__", "set_ref"])
        self.instructions.execute_selected_methods(
            ["_set_dynamic_inputs"])

        assert not self.instructions

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

        for stmt in get_statement_tokens(path_):
            parser = ParserSelector.select(stmt)(
                stmt, self, obj, srcpath=path_
            )
            parser.set_instruction()

    def read_pickledata(self):

        def custom_load(file):
            unpickler = ModelUnpickler(file, self)
            return unpickler.load()

        def compat_load(file):
            from .pandas_compat import CompatUnpickler
            return CompatUnpickler(file, self).load()

        file = self.path / "_data/iospecs.pickle"
        file_old = self.path / "_data/dataspecs.pickle"     # before mx v0.20.0

        for f in (file, file_old):
            if ziputil.exists(f):
                self.iospecs = ziputil.read_file_utf8(
                    lambda f: IOSpecUnpickler(f, self).load(), f, "b"
                )
                break

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

    def __init__(self, stmt, reader, obj, srcpath, **kwargs):
        self.stmt = stmt
        self.reader = reader
        self.obj = obj
        self.impl = obj._impl
        self.srcpath = srcpath
        self.kwargs = kwargs
        self.priority = self.default_priority

    @property
    def prev_inst(self):
        return self.reader.instructions.last

    @property
    def instructions(self):
        return self.reader.instructions

    @property
    def section(self):
        return self.stmt.section

    @classmethod
    def condition(cls, stmt):
        raise NotImplementedError


class DocstringParser(BaseNodeParser):
    """Docstring at module level"""
    @classmethod
    def condition(cls, stmt: StatementTokens):
        # stmt has 1 element that is STRING and starts at line 1.
        if stmt.section == "DEFAULT" and len(stmt) == 1:
            elm = stmt[0]
            if elm.type == tokenize.STRING:
                if elm.start[0] == 1:
                    return True

        return False

    def set_instruction(self):
        if self.section == "DEFAULT":
            inst = Instruction.from_method(
                obj=type(self.obj).doc,
                method="fset",
                args=(self.obj, self.docstr)
            )
            self.instructions.append(inst)
            return inst
        else:   # Cells.doc for lambda is processed by LambdaAssignParser
            # must not happen
            raise ValueError

    @property
    def docstr(self):
        return ast.literal_eval(self.stmt.str_)


class ImportFromParser(BaseNodeParser):
    AST_NODE = ast.ImportFrom

    @classmethod
    def condition(cls, stmt: StatementTokens):
        # first element is NAME 'import'.
        if stmt.section == "DEFAULT":
            elm = stmt[0]
            if elm.type == tokenize.NAME and elm.string == 'from':
                return True

        return False

    def set_instruction(self):
        return  # Skip any import from statement


class BaseAssignParser(BaseNodeParser):
    AST_NODE = ast.Assign

    @classmethod
    def condition(cls, stmt):
        if stmt[0].type == tokenize.NAME:
            if stmt[1].type == tokenize.OP and stmt[1].string == '=':
                return True

        return False

    @property
    def name(self):
        return self.stmt[0].string

    @property
    def value(self):

        if self.stmt[2].string == 'lambda': # Return source text
            lines = []
            first = True
            for tk in self.stmt[2:]:
                if first:
                    last_line = tk.end[0]
                    lines.append(tk.line)
                    first = False
                else:
                    if tk.start[0] == tk.end[0]:  # single line

                        if last_line < tk.end[0]:
                            lines.append(tk.line)
                            last_line = tk.end[0]
                    else:
                        ls = tk.line.splietlines(keepends=True)
                        start_line = tk.start[0]
                        end_line = tk.end[0]
                        while last_line < end_line:
                            if start_line <= last_line:
                                lines.append(ls[last_line - start_line])
                            last_line += 1

            start_pos = self.stmt[2].start[1]
            lines[0] = lines[0][start_pos:]
            lines[-1] = lines[-1][:self.stmt[-1].end[1] - start_pos]
            return ''.join(lines)
        else:
            txt = ' '.join(s.string for s in self.stmt[2:])
            return ast.literal_eval(txt)

    @property
    def target(self):
        return self.stmt[0].string

    def set_instruction(self):
        raise NotImplementedError


class RenameParser(BaseAssignParser):

    default_priority = PriorityID.AT_PARSE

    @classmethod
    def condition(cls, stmt):
        if not super(RenameParser, cls).condition(stmt):
            return False

        if stmt.section == "DEFAULT":
            if stmt[0].string == '_name':
                return True

        return False

    @property
    def new_name(self):
        return ast.literal_eval(self.stmt[2].string)

    def set_instruction(self):

        method = "rename"
        if "name" in self.reader.kwargs and self.reader.kwargs["name"]:
            val = self.reader.kwargs["name"]
        else:
            val = self.new_name

        kwargs = {"rename_old": True}

        inst = Instruction.from_method(
                obj=self.obj,
                method=method,
                args=(val,),
                kwargs=kwargs)

        inst.execute()
        return inst


class ParentAttrAssignParser(BaseAssignParser):

    @classmethod
    def condition(cls, stmt):
        if not super(ParentAttrAssignParser, cls).condition(stmt):
            return False

        if stmt.section == "DEFAULT":
            return True

        return False

    def set_instruction(self):

        if self.target == "_formula":
            # lambda formula definition
            method = "set_formula"
            val = self.value

            kwargs = {"formula": val}
            inst = Instruction.from_method(
                    obj=self.impl,
                    method=method,
                    kwargs=kwargs
                )

        elif self.target == "_bases":

            bases = [
                rel_to_abs(base, self.obj.parent.fullname)
                for base in self.value
            ]

            def bases_hook(inst):
                args = [mx.get_object(base) for base in inst.args]
                return args, inst.kwargs

            inst = Instruction.from_method(
                obj=self.obj,
                method="add_bases",
                args=bases,
                arghook=bases_hook)

        elif self.target == "_spaces":
            self.reader.result = self.value
            return

        elif self.target in ("_allow_none", "_is_cached"):
            name = self.target[1:]  # Remove first _
            inst = Instruction.from_method(
                obj=self.obj,
                method="set_property",
                args=(name, self.value))

        else:
            raise RuntimeError("unknown attribute assignment")

        self.instructions.append(inst)
        return inst


class RefAssignParser(BaseAssignParser):
    AST_NODE = ast.Assign

    @classmethod
    def condition(cls, stmt):
        if not super(RefAssignParser, cls).condition(stmt):
            return False

        if stmt.section == "REFDEFS":
            return True
        return False

    def set_instruction(self):

        name = self.target
        decoder_class = DecoderSelector.select(self.stmt)
        decoder = decoder_class(
            self.reader, self.stmt,
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
            refmode = decoder.value[2]
            setter = Instruction.from_method(
                obj=self.obj,
                method="set_ref",
                args=(name, value),
                arghook=arghook,
                kwargs={'refmode': refmode}
            )
        self.instructions.append(setter)
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
    """Cells definition as a lambda expression"""
    @classmethod
    def condition(cls, stmt):
        if not super(LambdaAssignParser, cls).condition(stmt):
            return False

        if stmt.section == "CELLSDEFS":
            if stmt[2].type == tokenize.NAME and stmt[2].string == 'lambda':
                return True

        return False

    @property
    def cellsname(self):
        return self.stmt[0].string

    def set_instruction(self):

        # get lambda expression
        expr = ""
        first_token = True
        first_line = 0
        for token in self.stmt[2:]:
            if first_token:
                expr += token.line[token.start[1]:]
                first_line = token.start[0]
                first_token = False
            elif token.start[0] == first_line:
                continue
            else:
                expr += token.line

        kwargs = {
            "name": self.cellsname,
            "formula": expr
        }
        # lambda cells definition
        inst = Instruction.from_method(
            obj=self.obj,
            method="new_cells",
            kwargs=kwargs
        )
        inst_list = [inst]

        if ziputil.exists(self.datapath):
            inst_list.append(Instruction(self.load_pickledata, priority=2))

        compinst = CompoundInstruction(inst_list)
        self.instructions.append(compinst)
        return compinst


class LambdaDocstringParser(BaseNodeParser):

    @classmethod
    def condition(cls, stmt):
        """String in CELLSDEFS section for docstring of lambda cells"""
        if stmt.section == "CELLSDEFS" and len(stmt) == 1:
            if stmt[0].type == tokenize.STRING:
                return True

        return False

    def set_instruction(self):
        doc = ast.literal_eval(self.stmt.str_)
        inst = Instruction.from_method(
            obj=self.prev_inst,
            method="set_doc",
            kwargs={'doc': doc},
            priority=1
        )
        assert isinstance(self.prev_inst, CompoundInstruction)
        self.prev_inst.append(inst)
        return inst


class CellsAttrAssignParser(BaseAssignParser):

    @classmethod
    def condition(cls, stmt):
        if stmt.section == "CELLSDEFS":
            first_elm = stmt[0]
            if first_elm.type == tokenize.NAME:
                if stmt[0].string in ("_allow_none", "_is_cached"):
                    return True

        return False

    def set_instruction(self):

        name = self.name[1:]    # Remove prefix '_'
        inst = Instruction.from_method(
            obj=self.prev_inst,
            method="set_property",
            args=(name, self.value),
            priority=1
        )
        assert isinstance(self.prev_inst, CompoundInstruction)
        self.prev_inst.append(inst)
        return inst


class FunctionDefParser(BaseNodeParser):
    AST_NODE = ast.FunctionDef
    METHOD = None

    @classmethod
    def condition(cls, stmt):

        if stmt[0].type == tokenize.NAME and stmt[0].string == 'def':
            if stmt[1].type == tokenize.NAME:
                return True
        return False

    def get_funcdef(self):

        funcdef = self.stmt.str_
        # The code below is just for adding back comment in the last line
        # such as:
        # def foo():
        #     return 0  # Comment
        lines = funcdef.splitlines()
        n = len(self.stmt[-1].line) - len(lines[-1])
        if n > 0:
            funcdef += self.stmt[-1].line[-n:]

        return funcdef

    def set_instruction(self):

        kwargs = {"formula": self.get_funcdef()}
        inst = Instruction.from_method(
            obj=self.obj,
            method=self.METHOD,
            kwargs=kwargs
        )
        self.instructions.append(inst)
        return inst


class SpaceFuncDefParser(FunctionDefParser):

    METHOD = "set_formula"

    @classmethod
    def condition(cls, stmt):
        if stmt.section == 'DEFAULT':
            if super(SpaceFuncDefParser, cls).condition(stmt):
                return True

        return False


class CellsFuncDefParser(FunctionDefParser, CellsInputDataMixin):

    METHOD = "new_cells"
    @classmethod
    def condition(cls, stmt):
        if stmt.section == 'CELLSDEFS':
            if super(CellsFuncDefParser, cls).condition(stmt):
                return True

        return False

    @property
    def cellsname(self):
        return self.stmt[1].string

    def set_instruction(self):

        inst = Instruction(_new_cells_keep_source,
                                args=(self.obj,),
                                kwargs={
                                    "formula": self.get_funcdef()
                                })
        instlist = [inst]

        if ziputil.exists(self.datapath):
            instlist.append(Instruction(self.load_pickledata, priority=2))
        compinst = CompoundInstruction(instlist)
        self.instructions.append(compinst)
        return compinst


class ParserSelector(BaseSelector):
    classes = [
        DocstringParser,
        ImportFromParser,
        RenameParser,
        LambdaAssignParser,
        LambdaDocstringParser,
        ParentAttrAssignParser,
        CellsAttrAssignParser,
        RefAssignParser,
        SpaceFuncDefParser,
        CellsFuncDefParser
    ]


class ValueDecoder:

    def __init__(self, reader, stmt, obj, name=None, srcpath=None):
        self.reader = reader
        self.stmt = stmt
        self.obj = obj
        self.name = name
        self.srcpath = srcpath

    def decode(self):
        raise NotImplementedError

    @property
    def value(self):
        expr = ' '.join(token.string for token in self.stmt[2:])
        try:
            return ast.literal_eval(expr)
        except ValueError:
            return json.loads(expr)


class TupleDecoder(ValueDecoder):
    DECTYPE = ''
    DECTYPE_COMPAT = ''

    def size(self):
        return len(self.value)

    @classmethod
    def condition(cls, stmt):
        if stmt.section == "REFDEFS":
            if stmt[2].string == '(' and stmt[-1].string == ')':
                if stmt[3].type == tokenize.STRING:
                    s = ast.literal_eval(stmt[3].string)
                    if s == cls.DECTYPE or s == cls.DECTYPE_COMPAT:
                        return True
        else:
            return False


class InterfaceDecoder(TupleDecoder):
    DECTYPE = "Interface"

    def decode(self):
        return rel_to_abs(self.value[1], self.obj.fullname)

    def restore(self):
        decoded = TupleID.unpickle_args(
            self.value[1],
            self.reader.pickledata
        )
        decoded = rel_to_abs_tuple(decoded, self.obj._idtuple)
        return mxsys.get_object_from_idtuple(decoded)


class IOSpecDecoder(TupleDecoder):
    DECTYPE = "IOSpec"
    DECTYPE_COMPAT = "DataSpec"     # for backward compatibility > mx v0.20.0

    def decode(self):
        return self.value[1]

    def restore(self):
        return self.reader.pickledata[self.decode()]


class ModuleDecoder(TupleDecoder):
    DECTYPE = "Module"

    def decode(self):
        return importlib.import_module(self.value[1])


class PickleDecoder(TupleDecoder):
    DECTYPE = "Pickle"

    def decode(self):
        return self.value[1]

    def restore(self):
        return self.reader.pickledata[self.decode()]


class LiteralDecoder(ValueDecoder):

    @classmethod
    def condition(cls, stmt):
        return True

    def decode(self):
        return self.value


class DecoderSelector(BaseSelector):
    classes = [
        InterfaceDecoder,
        IOSpecDecoder,
        ModuleDecoder,
        PickleDecoder,
        LiteralDecoder
    ]


if __name__ == "__main__":
    import doctest

    doctest.testmod()
