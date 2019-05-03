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

import json, types, collections, importlib, builtins, pathlib, shutil
import ast
from collections import namedtuple
import tokenize
from numbers import Number
import modelx as mx
from modelx.core.model import Model
from modelx.core.space import BaseSpace
from modelx.core.base import Interface
from modelx.core.cells import Cells
import asttokens


def export_model(model: Model, root_path):
    """Export model to directory.

    Create a directory with the name of ``model`` under ``root_path``,
    export model as source files.
    """

    root_path = pathlib.Path(root_path)

    def visit_spaces(model):
        """Generator yielding spaces in breadth-first order"""
        que = collections.deque([model])
        while que:
            space = que.pop()
            yield space
            for child in space.spaces.values():
                que.append(child)

    gen = visit_spaces(model)
    model = next(gen)
    created = []

    def create_path(path_, created):

        if path_ not in created:
            if path_.exists():
                shutil.rmtree(path_)
            path_.mkdir()
            created.append(path_)

    # Create _model.py
    path_ = root_path / model.fullname
    create_path(path_, created)

    with open(path_ / "_model.py", "w") as f:
        f.write("_refs = " + _RefViewEncoder(
            ensure_ascii=False, indent=4).encode(model.refs)
                )

    # Create Space.py
    for space in gen:
        space_path = "/".join(space.parent.fullname.split("."))

        path_ = root_path / space_path
        create_path(path_, created)
        _export_space(space, path_ / (space.name + ".py"))


def _export_space(space: BaseSpace, file):

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

    formulas = [format_formula(cells) for cells in space.cells.values()
                if cells._is_defined]

    with open(file, "w") as f:

        f.write(format_formula(space))
        f.write("\n\n")

        f.write(
            "_bases = " +
            _BaseEncoder(
                ensure_ascii=False, indent=4
            ).encode(space._direct_bases)
        )
        f.write("\n\n")

        for formula in formulas:
            f.write(formula)
            f.write("\n\n")

        f.write(
            "_refs = " +
            _RefViewEncoder(
                ensure_ascii=False, indent=4
            ).encode(space._self_refs)
        )


class _RefViewEncoder(json.JSONEncoder):
    """JSON encoder for converting refs"""
    def encode(self, refview):
        # Not adding meta data to refview itself
        # Exclude system names, which starts with "_"
        data = {key: _encode_refs(value) for key, value in refview.items()
                if key[0] != "_"}
        return super(_RefViewEncoder, self).encode(data)


class _BaseEncoder(json.JSONEncoder):
    """JSON encoder for storing list of base spaces"""
    def encode(self, data):
        data = [base.fullname for base in data]
        return super().encode(data)


def import_model(model_path):
    """Import model from source directory"""

    model_path = pathlib.Path(model_path)
    instructions = _parse_dir(model_path)
    model = mx.get_models()[model_path.name]

    def run_selected(instructions, methods):
        pos = 0
        while pos < len(instructions):
            c = instructions[pos]
            if c.method in methods:
                c.build()
                instructions.pop(pos)
            else:
                pos += 1

    run_selected(instructions, ["set_formula", "new_cells"])
    run_selected(instructions, ["add_bases"])
    run_selected(instructions, ["__setattr__"])

    return model


class _Instruction:

    def __init__(self, obj, method, args=(), kwargs=None, arghook=None):
        self.obj = obj
        self.method = method
        self.args = args
        if kwargs is None:
            kwargs = {}
        self.kwargs = kwargs
        self.arghook = arghook

    def build(self):
        if self.arghook:
            args, kwargs = self.arghook(self.args, self.kwargs)
        else:
            args, kwargs = self.args, self.kwargs

        getattr(self.obj, self.method)(*args, **kwargs)


_RefData = namedtuple("_RefData", ["evalrepr"])


def _parse_dir(path_: pathlib.Path, target=None):

    result = []
    if target is None:
        target = model = mx.new_model(path_.name)
        result.extend(_parse_source(path_ / "_model.py", model))

    for source in path_.glob("[!_]*.py"):
        name = source.name[:-3]
        space = target.new_space(name=name)
        result.extend(_parse_source(source, space))

    for subdir in path_.iterdir():
        if subdir.is_dir():
            next_target = target.spaces[subdir.name]
            result.extend(_parse_dir(subdir, target=next_target))

    return result


def _parse_source(path_, obj):

    with open(path_, "r") as f:
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

            return _Instruction(
                obj=obj,
                method=method,
                kwargs={"formula": funcdef}
            )

        if isinstance(node, ast.Assign):

            if node.first_token.string == "_formula":
                # lambda formula definition
                method = "set_formula"
                val = atok.get_text(node.value)
                if val == "None":
                    val = None
                kwargs = {"formula": val}
                return _Instruction(obj=obj, method=method, kwargs=kwargs)

            elif node.first_token.string == "_refs":
                refs = json.loads(
                    atok.get_text(node.value),
                    object_hook=_decode_refs
                )

                def refhook(args, kwargs):
                    if args:
                        key, val = args
                        val = _restore_ref(val)
                        args = (key, val)
                    return args, kwargs

                result = []
                for key, val in refs.items():
                    result.append(_Instruction(
                        obj=obj,
                        method="__setattr__",
                        args=(key, val),
                        arghook=refhook
                    ))
                return result

            elif node.first_token.string == "_bases":

                bases = [
                    _RefData(base) for base in
                    ast.literal_eval(atok.get_text(node.value))
                ]

                def basehook(args, kwargs):
                    if args:
                        args = _restore_ref(args)

                    return args, kwargs

                return _Instruction(
                    obj=obj,
                    method="add_bases",
                    args=bases,
                    arghook=basehook)

            else:
                # lambda cells definition
                return _Instruction(
                    obj=obj,
                    method="new_cells",
                    kwargs={
                        "name": atok.get_text(node.targets[0]),
                        "formula": atok.get_text(node.value)
                    }
                )

    result = []
    for stmt in atok.tree.body:
        stmt = parse_stmt(stmt)
        if isinstance(stmt, _Instruction):
            result.append(stmt)
        elif isinstance(stmt, collections.Sequence):
            result.extend(stmt)
        else:
            raise RuntimeError("must not happen")

    return result


def _encode_refs(obj):

    default_types = [str, Number, bool]

    if any(isinstance(obj, type_) for type_ in default_types):
        return obj

    klass = type(obj)
    builtins_name = type(int).__module__
    if klass.__module__ is not None and klass.__module__ != builtins_name:
        module = klass.__module__
    else:
        module = ""

    result = {
        "__module": module,
        "__type": klass.__qualname__
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
            "__value": obj._evalrepr,
        })

    elif isinstance(obj, collections.Sequence):
        result.update({
            "__encoding": "Sequence",
            "__value": [_encode_refs(item) for item in obj],
        })
    elif isinstance(obj, collections.Mapping):
        result.update({
            "__encoding": "Mapping",
            "__value": [
                (_encode_refs(key), _encode_refs(value))
                for key, value in obj.items()
            ],
        })
    else:
        raise TypeError("Type %s not supported by JSON" % str(klass))

    return result


def _decode_refs(data):
    """``data`` is {} components in json expression from the inner most"""

    metadata = ["__module", "__type", "__encoding", "__value"]

    def is_meta(data):
        return (len(data) == len(metadata)
                and all(key in data for key in metadata))

    if not is_meta(data):
        return data

    module = data["__module"]
    type_ = data["__type"]
    encode = data["__encoding"]
    value = data["__value"]

    if encode == "None":
        return None
    if encode == "Sequence":
        return _get_type(type_)(value)
    elif encode == "Mapping":
        type_ = _get_type(type_)
        return type_({key: value for key, value in value})
    elif encode == "Interface":
        return _RefData(evalrepr=value)
    elif encode == "Module":
        return importlib.import_module(value)
    elif encode == "Value":
        return _get_type(type_)(value)
    else:
        raise RuntimeError("must not happen")


def _get_type(name):

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
        return type(obj)((key, _restore_ref(val)) for key, val in obj.items())

    else:
        return obj


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
