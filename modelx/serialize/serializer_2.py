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

import json, types, importlib, pathlib
import ast
import enum
from collections import namedtuple
import tokenize
import pickle
import tempfile
import zipfile
import modelx as mx
from modelx.core.model import Model
from modelx.core.base import Interface
from modelx.core.util import abs_to_rel, rel_to_abs
import asttokens
from . import ziputil


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

    @classmethod
    def from_method(cls, obj, method, args=(), arghook=None, kwargs=None,
                    parser=None):
        func = getattr(obj, method)
        return cls(func, args=args, arghook=arghook, kwargs=kwargs,
                   parser=parser)

    def execute(self):
        if self.arghook:
            args, kwargs = self.arghook(self)
        else:
            args, kwargs = self.args, self.kwargs

        return self.func(*args, **kwargs)

    @property
    def funcname(self):
        return self.func.__name__

    def __repr__(self):
        return "<Instruction: %s>" % self.funcname


class CompoundInstruction(BaseInstruction):

    def __init__(self, instructions=None):

        self.instructions = []
        self.extend(instructions)

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
        result = None
        for inst in self.instructions:
            result = inst.execute()
        return result

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

    version = 2
    model_encoder = None
    space_encoder = None

    def __init__(self, system, model: Model, path: pathlib.Path,
                 log_input: bool,
                 compression=None, compresslevel=None
                 ):

        self.system = system
        self.model = model
        self.root = path
        self.call_ids = []
        self.pickledata = {}
        self.method_encoders = []
        self.log_input = log_input
        self.input_log = []

    def write_model(self):

        try:
            self.system.serializing = self

            encoder = self.model_encoder(
                self, self.model,
                self.root / "_model.py",
                self.root / "data")

            self._write_recursive(encoder)
            self.write_pickledata()

            if self.log_input:
                ziputil.write_str_utf8(
                    "\n".join(self.input_log),
                    self.root / "_input_log.txt"
                )

        finally:
            self.system.serializing = None
            self.call_ids.clear()

    def _write_recursive(self, encoder):

        ziputil.write_str_utf8(encoder.encode(), encoder.srcpath)

        for space in encoder.target.spaces.values():

            if not MethodCallEncoder.from_method(space):
                if isinstance(encoder.target, Model):
                    srcpath = encoder.srcpath.parent / (space.name + ".py")
                else:
                    srcpath = (encoder.srcpath.parent /
                               encoder.target.name / (space.name + ".py"))

                e = self.space_encoder(
                    self,
                    space,
                    srcpath=srcpath
                    )
                self._write_recursive(e)

        encoder.instruct().execute()

    def write_pickledata(self):
        if self.pickledata:
            file = self.root / "data/data.pickle"
            ziputil.write_file_utf8(
                lambda f: pickle.dump(self.pickledata, f), file, mode="b")


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

    version = 2
    refview_encoder_class = None

    def __init__(self, writer,
                 model: Model, srcpath: pathlib.Path, datapath: pathlib.Path):
        super().__init__(writer, model,
                         parent=None,
                         name=model.name,
                         srcpath=srcpath,
                         datapath=datapath)
        self.model = model

        self.refview_encoder = self.refview_encoder_class(
            self,
            self.model.refs,
            parent=self.model,
            srcpath=self.srcpath
        )
        self.method_encoders = []
        for space in model.spaces.values():
            if MethodCallEncoder.from_method(space):
                enc = MethodCallSelector.select(space)(
                    self,
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


ModelWriter.model_encoder = ModelEncoder


class SpaceEncoder(BaseEncoder):

    refview_encoder_class = None

    def __init__(self, writer, target, srcpath=None, datapath=None):
        super().__init__(writer, target, target.parent, target.name, srcpath,
                         datapath=srcpath.parent / srcpath.stem / "data")
        self.space = target

        self.refview_encoder = self.refview_encoder_class(
            self,
            self.space._self_refs,
            parent=self.space,
            srcpath=srcpath
        )

        self.space_method_encoders = []
        for space in self.space.spaces.values():
            encoder = MethodCallSelector.select(space)
            if encoder:
                enc = encoder(
                    self,
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
                    self,
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
            if cells._is_defined:
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

        return CompoundInstruction(insts)


ModelWriter.space_encoder = SpaceEncoder


class RefViewEncoder(BaseEncoder):

    selector_class = None

    def __init__(self, writer, target, parent, name=None, srcpath=None):
        super().__init__(writer, target, parent, name, srcpath)

        # TODO: Refactor
        is_model = parent._impl.is_model()

        if is_model:
            datadir = srcpath.parent / "data"
        else:
            datadir = srcpath.parent / parent.name / "data"

        self.encoders = []
        for key, val in self.target.items():
            if key[0] != "_":
                # TODO: Refactor
                if (is_model or not parent._impl.refs[key].is_derived):
                    datapath = datadir / key
                    self.encoders.append(self.selector_class.select(val)(
                        writer,
                        val, parent=parent, name=key, srcpath=srcpath,
                        datapath=datapath))

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


ModelEncoder.refview_encoder_class = RefViewEncoder
SpaceEncoder.refview_encoder_class = RefViewEncoder


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

            ziputil.write_file_utf8(write_dataid, self.datapath, "t")

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
        return Instruction(func, args=(self.target, self.srcpath.parent))

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


def copy_file(obj, path_: pathlib.Path):
    src = obj._impl.source
    srcpath = pathlib.Path(src["args"][0])
    ziputil.copy_file(
        srcpath,
        path_.joinpath(srcpath.name)
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


def write_pandas(obj, path_: pathlib.Path, filename=None):
    src = obj._impl.source
    data = src["args"][0]
    if not filename:
        filename = obj.name + ".pandas"
    ziputil.pandas_to_pickle(data, path_.joinpath(filename))


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
            self.target, self.datapath, self.callid))

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
    def condition(cls, target):
        return isinstance(target, Interface)

    def encode(self):
        relname = abs_to_rel(self.target._evalrepr, self.parent._evalrepr)
        return "(\"Interface\", \"%s\")" % relname


class LiteralEncoder(BaseEncoder):
    literal_types = [bool, int, float, str]

    @classmethod
    def condition(cls, target):
        return any(type(target) is t for t in cls.literal_types)

    def encode(self):
        return json.dumps(self.target, ensure_ascii=False)


class ModuleEncoder(BaseEncoder):

    @classmethod
    def condition(cls, target):
        return isinstance(target, types.ModuleType)

    def encode(self):
        return "(\"Module\", \"%s\")" % self.target.__name__


class PickleEncoder(BaseEncoder):

    @classmethod
    def condition(cls, target):
        return True  # default encoder

    def pickle_value(self, path: pathlib.Path, value):
        key = id(value)
        ziputil.write_str_utf8(str(key), path)
        if key not in self.writer.pickledata:
            self.writer.pickledata[key] = value

    def encode(self):
        data = self.datapath.relative_to(self.srcpath.parent).as_posix()
        return "(\"Pickle\", \"%s\")" % data

    def instruct(self):
        kwargs = {"path": self.datapath,
                  "value": self.target}
        return Instruction(self.pickle_value, kwargs=kwargs)


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


class ModelReader:

    version = 2
    parser_selector_class = None

    def __init__(self, system, path: pathlib.Path):
        self.system = system
        self.path = path.resolve()
        self.kwargs = None
        self.instructions = CompoundInstruction()
        self.result = None      # To pass list of space names
        self.model = None
        self.pickledata = None
        self.tempdir = None

    def read_model(self, **kwargs):

        try:
            self.system.serializing = self
            self.kwargs = kwargs
            model = self.parse_dir()
            self.instructions.execute_selected_methods([
                "doc",
                "set_formula",
                "set_property",
                "new_cells"])

            if self.instructions.find_instruction(
                lambda inst: isinstance(inst.parser, MethodCallParser)
            ):
                if zipfile.is_zipfile(self.path):
                    with tempfile.TemporaryDirectory()as tempdir:
                        self.tempdir = pathlib.Path(tempdir)
                        self.instructions.execute_selected_parser(
                            MethodCallParser
                        )
                        self.tempdir = None
                else:
                    self.instructions.execute_selected_parser(
                        MethodCallParser
                    )

            self.instructions.execute_selected_methods(["add_bases"])
            self.read_pickledata()
            self.instructions.execute_selected_methods(["load_pickledata"])
            self.instructions.execute_selected_methods(["__setattr__"])
            self.instructions.execute_selected_methods(
                ["_set_dynamic_inputs"])
        except:
            if self.model:
                self.model.close()
            raise

        finally:
            self.system.serializing = None

        return model

    def parse_dir(self, path_: pathlib.Path = None, target=None, spaces=None):

        if target is None:
            path_ = self.path
            target = self.model = mx.new_model()
            self.parse_source(path_ / "_model.py", self.model)
            spaces = self.result

        for name in spaces:
            space = target.new_space(name=name)
            self.parse_source(path_ / ("%s.py" % name), space)
            nextdir = path_ / name
            self._parse_dynamic_inputs(nextdir)
            if ziputil.exists(nextdir) and ziputil.is_dir(nextdir):
                self.parse_dir(nextdir, target=space, spaces=self.result)

        return target

    def _parse_dynamic_inputs(self, path_):
        pass

    def parse_source(self, path_, obj: Interface):

        src = ziputil.read_str_utf8(path_)
        srcstructure = SourceStructure(src)
        atok = asttokens.ASTTokens(src, parse=True)

        for i, stmt in enumerate(atok.tree.body):
            sec = srcstructure.get_section(stmt.lineno)
            parser = self.parser_selector_class.select(stmt, sec, atok)(
                stmt, atok, self, sec, obj, srcpath=path_
            )
            ist = parser.get_instruction()
            if parser.priority == PriorityID.AT_PARSE:
                ist.execute()
            else:
                self.instructions.append(ist)

    def read_pickledata(self):
        file = self.path / "data/data.pickle"
        if ziputil.exists(file):
            self.pickledata = ziputil.read_file_utf8(pickle.load, file, "b")


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
        return Instruction.from_method(
            obj=type(self.obj).doc,
            method="fset",
            args=(self.obj, self.node.value.s)
        )


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

            if self.reader.tempdir:
                srcpath = pathlib.Path(args[0])
                rel = srcpath.relative_to(self.reader.path)
                temppath = self.reader.tempdir.joinpath(rel)
                tempargs[0] = str(temppath)
                ziputil.copy_file(srcpath, temppath)

            func = getattr(self.impl, method["method"])
            func(*tempargs, **kwargs)
            if self.reader.tempdir:
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

            if self.reader.tempdir:
                srcpath = pathlib.Path(args[0])
                rel = srcpath.relative_to(self.reader.path)
                temppath = self.reader.tempdir.joinpath(rel)
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
        if isinstance(node, cls.AST_NODE) and section == "DEFAULT":
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
            value = ast.literal_eval(self.atok.get_text(self.node.value))
            return Instruction.from_method(
                obj=self.obj,
                method="set_property",
                args=("allow_none", value)
            )

        else:
            raise RuntimeError("unknown attribute assignment")


class RefAssignParser(BaseAssignParser):
    AST_NODE = ast.Assign
    selector_class = None

    @classmethod
    def condition(cls, node, section, atok):
        if isinstance(node, cls.AST_NODE) and section == "REFDEFS":
            return True
        return False

    def get_instruction(self):

        name = self.target
        valnode = self.node.value

        decoder = self.selector_class.select(valnode)(
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

        return Instruction.from_method(
            obj=self.obj,
            method="__setattr__",
            args=(name, value),
            arghook=arghook
        )


class CellsInputDataMixin(BaseNodeParser):

    @property
    def cellsname(self):
        raise NotImplementedError

    @property
    def datapath(self) -> pathlib.Path:
        return (self.srcpath.parent
                / self.srcpath.stem / "data" / self.cellsname)

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


class LambdaAssignParser(BaseAssignParser, CellsInputDataMixin):

    @classmethod
    def condition(cls, node, section, atok):
        if isinstance(node, cls.AST_NODE) and section == "CELLSDEFS":
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
            obj=self.impl,
            method="new_cells",
            kwargs=kwargs
        )
        return CompoundInstruction([
            inst,
            Instruction(self.load_pickledata)
        ])


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
            obj=self.impl,
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
        return CompoundInstruction([
            super().get_instruction(),
            Instruction(self.load_pickledata)
        ])


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

    def elm(self, index):
        return ast.literal_eval(self.atok.get_text(self.node.elts[index]))

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
        return mx.get_object(self.decode())


class ModuleDecoder(TupleDecoder):
    DECTYPE = "Module"
    def decode(self):
        return importlib.import_module(self.elm(1))


class PickleDecoder(TupleDecoder):
    DECTYPE = "Pickle"

    def decode(self):
        return self.srcpath.parent / self.elm(1)

    def restore(self):
        key = ziputil.read_file_utf8(
            lambda f: int(f.read()), self.decode(), "t")

        return self.reader.pickledata[key]


class LiteralDecoder(ValueDecoder):

    @classmethod
    def condition(cls, node):
        return True

    def decode(self):
        return ast.literal_eval(self.node)


class DecoderSelector(BaseSelector):
    classes = [
        InterfaceDecoder,
        ModuleDecoder,
        PickleDecoder,
        LiteralDecoder
    ]


RefAssignParser.selector_class = DecoderSelector


if __name__ == "__main__":
    import doctest

    doctest.testmod()
