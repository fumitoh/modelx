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

import json, types, collections, importlib, builtins, pathlib
import ast
from collections import namedtuple
import tokenize
import shutil
from numbers import Number
import modelx as mx
from modelx.core.model import Model
from modelx.core.space import BaseSpace
from modelx.core.base import Interface
from modelx.core.cells import Cells
import asttokens


def _write_file(obj, path_):
    src = obj._impl.source.copy()
    srcpath = pathlib.Path(src["args"][0])
    shutil.copyfile(
        str(srcpath),
        str(path_.joinpath(srcpath.name))
    )
    src["args"][0] = srcpath.name
    return src


def _read_file():
    pass


def write_pandas(obj, path_: pathlib.Path):
    src = obj._impl.source.copy()
    data = src["args"][0]
    filename = obj.name + ".data"
    data.to_pickle(str(path_.joinpath(filename)))
    src["args"][0] = filename
    return src


def refhook(inst):
    args, kwargs = inst.args, inst.kwargs

    if args:
        key, val = args
        val = _restore_ref(val)
        args = (key, val)
    return args, kwargs


def basehook(inst):
    args, kwargs = inst.args, inst.kwargs

    if args:
        args = _restore_ref(args)

    return args, kwargs


def filehook(inst):
    args, kwargs = inst.args, inst.kwargs
    args[0] = str(inst.path_.with_name(args[0]))
    return args, kwargs


def pandashook(inst):
    import pandas as pd
    args, kwargs = inst.args, inst.kwargs
    filepath = str(inst.path_.with_name(args[0]))
    args[0] = pd.read_pickle(filepath)
    return args, kwargs


class _Instruction:

    _METHODS = {
        "new_space_from_excel": {
            "writer": _write_file,
            "reader": filehook},
        "new_cells_from_excel": {
            "writer": _write_file,
            "reader": filehook},
        "new_space_from_csv": {
            "writer": _write_file,
            "reader": filehook},
        "new_cells_from_csv": {
            "writer": _write_file,
            "reader": filehook},
        "new_space_from_pandas": {
            "writer": write_pandas,
            "reader": pandashook},
        "new_cells_from_pandas": {
            "writer": write_pandas,
            "reader": pandashook}
    }

    def __init__(self, path_, obj, method, args=(), kwargs=None, arghook=None):

        self.path_ = path_
        self.obj = obj
        self.method = method
        self.args = args
        if kwargs is None:
            kwargs = {}
        self.kwargs = kwargs

        if arghook is None:
            if method in self._METHODS:
                self.arghook = self._METHODS[method]["reader"]
            else:
                self.arghook = None
        else:
            self.arghook = arghook

    def run(self):

        if self.arghook:
            args, kwargs = self.arghook(self)
        else:
            args, kwargs = self.args, self.kwargs

        getattr(self.obj, self.method)(*args, **kwargs)


class _InstructionList(list):

    def run_methods(self, methods, obj=None, pop_items=True):

        if pop_items:
            list_ = self
        else:
            list_ = self.copy()

        pos = 0
        while pos < len(list_):
            c = list_[pos]
            if ((obj is None) or (c.obj is obj)) and (c.method in methods):
                c.run()
                list_.pop(pos)
            else:
                pos += 1


class ModelWriter:

    def __init__(self, model: Model, path: pathlib.Path):
        self.model = model
        self.root = path
        self.call_ids = []

    def write_model(self):

        def visit_spaces():
            """Generator yielding spaces in breadth-first order"""
            que = collections.deque([self.model])
            while que:
                space = que.pop()
                yield space
                for child in space.spaces.values():
                    que.append(child)

        gen = visit_spaces()
        model = next(gen)

        try:
            # Create _model.py
            with open(self.root / "_model.py", "w", encoding="utf-8") as f:

                if model.doc is not None:
                    f.write("\"\"\"" + model.doc + "\"\"\"")

                f.write("_name = " + json.JSONEncoder().encode(model.name))
                f.write("\n\n")

                self._write_allow_none(model, f)

                f.write("_refs = " + _RefViewEncoder(
                    owner=model,
                    ensure_ascii=False,
                    indent=4
                ).encode(model.refs))
                f.write("\n\n")

                for space in model.spaces.values():
                    self._write_method(
                        space, f, path_=self.root)

            # Create Space.py
            for space in gen:
                if not self._has_method(space):
                    space_path = "/".join(space.parent.fullname.split(".")[1:])
                    path_ = self.root / space_path
                    if not path_.exists():
                        path_.mkdir()
                    self._write_space(space, path_ / (space.name + ".py"))
        finally:
            self.call_ids = []

    def _has_method(self, obj: Interface):
        src = obj._impl.source
        return (src and "method" in src
                and src["method"] in _Instruction._METHODS)

    def _has_new_callid(self, obj: Interface):
        src = obj._impl.source
        return src["kwargs"]["call_id"] not in self.call_ids

    def _write_method(self, obj, file, path_):

        if self._has_method(obj) and self._has_new_callid(obj):

            src = obj._impl.source
            writer = _Instruction._METHODS[src["method"]]["writer"]
            src = writer(obj, path_)

            file.write("_method = " + json.JSONEncoder(
                ensure_ascii=False,
                indent=4
            ).encode(src))
            file.write("\n\n")
            self.call_ids.append(src["kwargs"]["call_id"])

    def _write_space(self, space: BaseSpace, file: pathlib.Path):

        def format_formula(obj):

            if isinstance(obj, Cells):
                target = obj.name
            else:
                target = "_formula"

            if obj.formula:
                if obj.formula.source[:6] == "lambda":
                    return target + " = " + obj.formula.source
                else:
                    return obj.formula.source
            else:
                return target + " = None"

        with open(file, "w", encoding="utf-8") as f:

            if space.doc is not None:
                f.write("\"\"\"" + space.doc + "\"\"\"\n\n")

            f.write(format_formula(space))
            f.write("\n\n")

            if space._direct_bases:
                f.write(
                    "_bases = " +
                    _BaseEncoder(
                        owner=space,
                        ensure_ascii=False,
                        indent=4
                    ).encode(space._direct_bases)
                )
                f.write("\n\n")

            self._write_allow_none(space, f)

            for cells in space.cells.values():
                if cells._is_defined:
                    if self._has_method(cells):
                        self._write_method(
                            cells,
                            f,
                            path_=file.parent)
                    else:
                        f.write(format_formula(cells))
                        if cells.allow_none is not None:
                            f.write("\n")
                            f.write(cells.name + ".allow_none = "
                                    + json.JSONEncoder().encode(
                                        cells.allow_none)
                                    )
                        f.write("\n\n")

            f.write(
                "_refs = " +
                _RefViewEncoder(
                    owner=space,
                    ensure_ascii=False,
                    indent=4
                ).encode(space._self_refs)
            )
            f.write("\n\n")

            for child in space.spaces.values():
                self._write_method(child, f, path_=file.parent)

    def _write_allow_none(self, obj, file):
        if obj.allow_none is not None:
            s = "_allow_none = " + json.JSONEncoder().encode(obj.allow_none)
            file.write(s + "\n\n")


class _RefViewEncoder(json.JSONEncoder):
    """JSON encoder for converting refs"""

    def __init__(self, owner, ensure_ascii, indent):
        json.JSONEncoder.__init__(
            self,
            ensure_ascii=ensure_ascii,
            indent=indent
        )
        self.owner = owner

    def encode(self, refview):
        # Not adding meta data to refview itself
        # Exclude system names, which starts with "_"
        data = {key: self._encode_refs(value, self.owner.fullname)
                for key, value in refview.items()
                if key[0] != "_"}
        return super(_RefViewEncoder, self).encode(data)

    def _encode_refs(self, obj, namespace):

        default_types = [str, Number, bool]

        if any(isinstance(obj, type_) for type_ in default_types):
            return obj

        cls = type(obj)
        builtins_name = type(int).__module__
        if cls.__module__ is not None and cls.__module__ != builtins_name:
            module = cls.__module__
        else:
            module = ""

        result = {
            "__module": module,
            "__type": cls.__qualname__
        }

        if obj is None:
            result.update({
                "__encoding": "None",
                "__value": "None"
            })
        elif isinstance(obj, types.ModuleType):
            result.update({
                "__encoding": "Module",
                "__value": obj.__name__,
            })
        elif isinstance(obj, Interface):
            result.update({
                "__encoding": "Interface",
                "__value": abs_to_rel(obj._evalrepr, namespace),
            })

        elif isinstance(obj, collections.Sequence):
            result.update({
                "__encoding": "Sequence",
                "__value": [
                    self._encode_refs(item, namespace) for item in obj],
            })
        elif isinstance(obj, collections.Mapping):
            result.update({
                "__encoding": "Mapping",
                "__value": [
                    (self._encode_refs(key, namespace),
                     self._encode_refs(value, namespace))
                    for key, value in obj.items()
                ],
            })
        else:
            raise TypeError("Type %s not supported by JSON" % str(cls))

        return result


class _BaseEncoder(json.JSONEncoder):
    """JSON encoder for storing list of base spaces"""

    def __init__(self, owner, ensure_ascii, indent):
        json.JSONEncoder.__init__(
            self,
            ensure_ascii=ensure_ascii,
            indent=indent
        )
        self.owner = owner

    def encode(self, data):
        data = [abs_to_rel(base.fullname, self.owner.fullname)
                for base in data]
        return super().encode(data)


class ModelReader:

    def __init__(self, path: pathlib.Path):
        self.path = path
        self.kwargs = None

    def read_model(self, **kwargs):

        self.kwargs = kwargs
        instructions, model = self._parse_dir()

        instructions.run_methods([
            "fset",
            "set_formula",
            "set_property",
            "new_cells"] + list(_Instruction._METHODS.keys()))
        instructions.run_methods(["add_bases"])
        instructions.run_methods(["__setattr__"])

        return model

    def _parse_dir(self, path_: pathlib.Path = None, target=None):

        result = _InstructionList()
        if target is None:
            path_ = self.path
            target = model = mx.new_model(path_.name)
            result.extend(self._parse_source(path_ / "_model.py", model))

        for source in path_.glob("[!_]*.py"):
            name = source.name[:-3]
            space = target.new_space(name=name)
            result.extend(self._parse_source(source, space))

        for subdir in path_.iterdir():
            if subdir.is_dir():
                next_target = target.spaces[subdir.name]
                result.extend(self._parse_dir(subdir, target=next_target)[0])

        return result, target

    def _parse_source(self, path_, obj: Interface):

        impl = obj._impl

        with open(path_, "r", encoding="utf-8") as f:
            src = f.read()

        atok = asttokens.ASTTokens(src, parse=True)

        def parse_stmt(node):
            """Return (list of) instructions"""
            if isinstance(node, ast.FunctionDef):
                if node.name == "_formula":
                    method = "set_formula"
                else:
                    method = "new_cells"

                funcdef = atok.get_text(node)

                # The code below is just for adding back comment in the last line
                # such as:
                # def foo():
                #     return 0  # Comment
                nxtok = node.last_token.index + 1
                if nxtok < len(atok.tokens) and (
                    atok.tokens[nxtok].type == tokenize.COMMENT
                )and node.last_token.line == atok.tokens[nxtok].line:
                    deflines = funcdef.splitlines()
                    deflines.pop()
                    deflines.append(node.last_token.line.rstrip())
                    funcdef = "\n".join(deflines)

                return [_Instruction(
                    path_=path_,
                    obj=impl,
                    method=method,
                    kwargs={"formula": funcdef}
                )]

            if isinstance(node, ast.Assign):

                if node.first_token.string == "_name":
                    method = "rename"
                    if "name" in self.kwargs and self.kwargs["name"]:
                        val = self.kwargs["name"]
                    else:
                        val = ast.literal_eval(atok.get_text(node.value))
                    _Instruction(
                        path_=path_,
                        obj=obj,
                        method=method,
                        args=(val,),
                        kwargs={"rename_old": True}).run()
                    return []

                elif node.first_token.string == "_formula":
                    # lambda formula definition
                    method = "set_formula"
                    val = atok.get_text(node.value)
                    if val == "None":
                        val = None
                    kwargs = {"formula": val}
                    return [
                        _Instruction(
                            path_=path_,
                            obj=impl,
                            method=method,
                            kwargs=kwargs)
                    ]

                elif node.first_token.string == "_refs":

                    def bound_decode_refs(data):
                        return self._decode_refs(data, obj.fullname)

                    refs = json.loads(
                        atok.get_text(node.value),
                        object_hook=bound_decode_refs
                    )

                    result = []
                    for key, val in refs.items():
                        result.append(_Instruction(
                            path_=path_,
                            obj=obj,
                            method="__setattr__",
                            args=(key, val),
                            arghook=refhook
                        ))
                    return result

                elif node.first_token.string == "_bases":

                    bases = [
                        _RefData(rel_to_abs(base, obj.fullname)) for base in
                        ast.literal_eval(atok.get_text(node.value))
                    ]

                    return [_Instruction(
                        path_=path_,
                        obj=obj,
                        method="add_bases",
                        args=bases,
                        arghook=basehook)]

                elif node.first_token.string == "_method":

                    _method = json.loads(
                        atok.get_text(node.value)
                    )
                    return [_Instruction(
                        path_=path_,
                        obj=impl,
                        method=_method["method"],
                        args=_method["args"],
                        kwargs=_method["kwargs"]
                    )]

                elif node.first_token.string == "_allow_none":
                    args = json.loads(atok.get_text(node.value))
                    return [_Instruction(
                        path_=path_,
                        obj=obj,
                        method="set_property",
                        args=["allow_none", args]
                    )]

                else:
                    # lambda cells definition
                    return [_Instruction(
                        path_=path_,
                        obj=impl,
                        method="new_cells",
                        kwargs={
                            "name": atok.get_text(node.targets[0]),
                            "formula": atok.get_text(node.value)
                        }
                    )]

        result = []
        for i, stmt in enumerate(atok.tree.body):

            if (i == 0 and isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Str)):
                inst = _Instruction(
                    path_=path_,
                    obj=type(obj).doc,
                    method="fset",
                    args=(obj, stmt.value.s)
                )
                result.append(inst)
            else:
                result.extend(parse_stmt(stmt))

        return result

    def _decode_refs(self, data, namespace):
        """``data`` is {} components in json expression from the inner most"""

        if not _is_mxdata(data):
            return data

        module = data["__module"]
        type_ = data["__type"]
        encode = data["__encoding"]
        value = data["__value"]

        if encode == "None":
            return None
        if encode == "Sequence":
            return self._get_type(type_)(value)
        elif encode == "Mapping":
            type_ = self._get_type(type_)
            return type_({key: value for key, value in value})
        elif encode == "Interface":
            return _RefData(evalrepr=rel_to_abs(value, namespace))
        elif encode == "Module":
            return importlib.import_module(value)
        elif encode == "Value":
            return self._get_type(type_)(value)
        else:
            raise RuntimeError("must not happen")

    def _get_type(self, name):

        namelist = name.rsplit(".", 1)

        if len(namelist) == 1:
            return getattr(builtins, namelist[0])
        elif len(namelist) == 2:
            module, type_ = namelist
            module = importlib.import_module(module)
            return getattr(module, type_)
        else:
            raise RuntimeError("must not happen")


def _restore_ref(obj):
    """Restore ref from _RefData in nested container"""
    if isinstance(obj, _RefData):
        return mx.get_object(obj.evalrepr)

    elif isinstance(obj, str):
        return obj

    elif isinstance(obj, collections.Sequence):
        return type(obj)(_restore_ref(value) for value in obj)

    elif isinstance(obj, collections.Mapping):
        return type(obj)(
            (key, _restore_ref(val)) for key, val in obj.items())

    else:
        return obj


_RefData = namedtuple("_RefData", ["evalrepr"])

_MXDATA_ATTRS = ["__module", "__type", "__encoding", "__value"]


def _is_mxdata(data):
    return (len(data) == len(_MXDATA_ATTRS)
            and all(key in data for key in _MXDATA_ATTRS))


def abs_to_rel(target: str, namespace: str):
    """Convert absolute name relative to namespace

    number of dots: nslen - shared + 1
    number of names: tglen - shared

    >>> tg = "aaa.bbb.ddd"
    >>> ns = "aaa.bbb.ccc"
    >>> abs_to_rel(tg, ns)
    '..ddd'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True

    >>> tg = "aaa.bbb"
    >>> ns = "aaa.bbb.ccc"
    >>> abs_to_rel(tg, ns)
    '..'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True

    >>> tg = "aaa.bbb.ddd"
    >>> ns = "aaa.bbb"
    >>> abs_to_rel(tg, ns)
    '.ddd'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True

    >>> tg = "eee.fff"
    >>> ns = "aaa"
    >>> abs_to_rel(tg, ns)
    '..eee.fff'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True

    >>> tg = "aaa"
    >>> ns = "aaa.bbb.ccc.ddd"
    >>> abs_to_rel(tg, ns)
    '....'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True

    >>> tg = "ddd"
    >>> ns = "aaa.bbb.ccc"
    >>> abs_to_rel(tg, ns)
    '....ddd'
    >>> tg == rel_to_abs(abs_to_rel(tg, ns), ns)
    True
    """
    tg = target.split(".")
    ns = namespace.split(".")

    tglen = len(tg)
    nslen = len(ns)

    shared = 0
    while (
            shared < min(tglen, nslen)
            and tg[shared] == ns[shared]
    ):
        shared += 1

    dots = nslen - shared + 1
    names = tglen - shared

    return "." * dots + ".".join(tg[tglen - names:])


def rel_to_abs(target: str, namespace: str):
    """Convert name relative to namespace to absolute"""

    # shared = nslen - dots + 1

    ns = namespace.split(".")
    nslen = len(ns)

    dots = 0
    while dots < len(target) and target[dots] == ".":
        dots += 1

    shared = nslen - dots + 1
    tg = target[dots:].split(".") if dots < len(target) else []  # Avoid [""]
    abs = ns[:shared] + tg

    return ".".join(abs)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
