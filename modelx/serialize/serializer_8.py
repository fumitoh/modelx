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

"""Serializer version 8.

Declares IO specs as literal tuples in a central text file instead of
pickling the spec objects, on top of serializer 7. ``_data/data.pickle``
(user data values) is the only pickle left in a saved model; the
``_data/iospecs.pickle`` file of versions 4-7 is gone.

The iospecs file
----------------
Every ``BaseIOSpec`` of the model (``model.iospecs``, regardless of ref
visibility) is declared in ``_data/iospecs.py``, one
:func:`ast.literal_eval`-able tuple per line, sorted by key::

    # modelx: iospecs
    # (key, class, path, io_args, spec_args)
    (1, 'PandasData', 'files/data.csv', {'file_type': 'csv'}, {'sheet': None, 'is_series': False, 'name': None, 'index_nlevels': 1, 'columns_nlevels': 1})

- ``key`` is the writer-assigned spec id — the same ``assign_id(spec)``
  int that keys the ``iospecs.pickle`` dict in versions 6/7 and that the
  ``("DataValue", key)`` / ``("BaseIOSpec", key)`` persistent-id stubs
  inside ``data.pickle`` refer to. Keys are opaque tokens to readers.
- ``class`` names the spec type. It is resolved through the module-level
  name registry (``_SPEC_CLASS_MODULES``), never by import path, so the
  file format is decoupled from the modelx module layout.
- ``path`` is the IO path as a posix string, following the
  ``BaseSharedIO`` persistent-id convention: relative paths are relative
  to the model folder, absolute paths are stored as-is.
- ``io_args`` is ``io.persistent_args`` (e.g. ``{'file_type': 'csv'}``
  for ``PandasIO``), passed to ``IOManager.get_or_create_io``.
- ``spec_args`` holds the spec parameters (see below).

Blank lines and lines starting with ``#`` are ignored. A line that
cannot be parsed or restored fails individually: the reader warns,
records the key as lost (references to it and persistent-id stubs in
``data.pickle`` degrade to None), and continues with the next line.

Spec parameters per class
-------------------------
Parameters must be literal-representable — compositions of str, int,
float, bool, None, tuple, list and dict (exact types). Numpy scalars
(a common pandas Series name) are coerced to their plain Python
equivalents via ``.item()``; anything else fails the save with a clean
``TypeError`` before any output is written (``ModelWriter
.validate_model``, run by ``modelx.serialize.write_model`` ahead of the
backup rotation). This is a permanent contract for future spec types.
Fields are emitted in a fixed order per class so the file is canonical.
Everything recomputable from the IO file is recomputed on load rather
than persisted:

- ``PandasData`` — ``{'sheet', 'is_series', 'name', 'index_nlevels',
  'columns_nlevels'}``. Instead of the pandas-API ``read_args`` dict of
  versions 4-7, the shape metadata needed to parse the file before the
  data exists (a one-column DataFrame and a Series produce identical
  CSV) is persisted in a version-independent form, and ``read_args`` is
  recomputed from it on load the way ``PandasData._init_spec`` does
  (``engine`` from the path suffix, ``sheet_name`` from ``sheet``).
  ``name`` is the pandas Series name (None for DataFrames), not the ref
  name. The v4-era ``is_hidden`` flag is dropped: v8 files carry no such
  field and a formerly hidden spec reloads as an ordinary one.
- ``ExcelRange`` — ``{'range', 'sheet', 'keyids'}``, the user-supplied
  constructor arguments (``keyids`` as a tuple or None).
- ``ModuleData`` — ``{}``; the path alone identifies the module source.

Reference sites
---------------
A ref site emits exactly ``("IOSpec", key)`` — the ``value_id`` element
of the version-6/7 shape is dropped, and the decoder returns the spec's
``.value`` straight from the restored spec, so the value no longer
enters ``data.pickle`` through the ref path. The reference is followed
by a trailing comment carrying the user-facing spec parameters for
readability, e.g.::

    pdref = ("IOSpec", 2)  # PandasData path='files/data.csv' file_type='csv' sheet='SheetA'

The comment is writer-generated documentation only: it is never parsed
on read, and is regenerated deterministically on every save from the
spec state, with a fixed field order per class (fields whose value is
None are omitted):

- ``PandasData`` — ``path``, ``file_type``, ``sheet``
- ``ExcelRange`` — ``path``, ``range``, ``sheet``, ``keyids``
- ``ModuleData`` — ``path``

The pickle layer is reused unchanged: ``data.pickle`` keeps the
version-7 persistent-id shapes, written by ``DeterministicModelPickler``
and resolved by ``ModelUnpickler`` against the specs restored from the
literal file.
"""
import sys
import json
import ast
import pathlib
import tempfile
import shutil
import importlib
import tokenize
import warnings
import modelx as mx
from modelx.core.model import Model
from . import ziputil
from .deserializer import get_statement_tokens
from .custom_pickle import ModelUnpickler, DeterministicModelPickler
from . import serializer_6
from . import serializer_7


IOSPECS_FILE = "_data/iospecs.py"

IOSPECS_HEADER = """\
# modelx: iospecs
# (key, class, path, io_args, spec_args)
"""

# --------------------------------------------------------------------------
# Spec class registry and per-class parameter schemas

_SPEC_CLASS_MODULES = {
    "PandasData": "modelx.io.pandasio",
    "ExcelRange": "modelx.io.excelio",
    "ModuleData": "modelx.io.moduleio",
}


def _get_spec_class(name):
    # Lazy imports: pandas/openpyxl must not be required to read or
    # write models that do not use them.
    if name not in _SPEC_CLASS_MODULES:
        raise ValueError("unknown IO spec type: %r" % name)
    return getattr(importlib.import_module(_SPEC_CLASS_MODULES[name]), name)


def _coerce_scalar(value):
    """Normalize numpy scalars to the plain Python scalars the literal
    contract requires.

    A pandas Series name is often a numpy scalar in ordinary usage
    (e.g. a column selected from a DataFrame with numpy-typed column
    labels), and such names round-trip as their plain Python
    equivalents.
    """
    if type(value) in (str, int, float, bool, type(None)):
        return value
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            return value
    return value


def _encode_pandas_params(spec):
    import pandas as pd
    data = spec.value
    is_series = isinstance(data, pd.Series)
    # Shape metadata is derived from the live value the same way
    # _init_spec derives read_args from it, so a stale read_args dict
    # (the value mutated in place) cannot poison the saved model.
    return {
        "sheet": spec.sheet,
        "is_series": is_series,
        "name": _coerce_scalar(data.name) if is_series else None,
        "index_nlevels": data.index.nlevels,
        "columns_nlevels": 1 if is_series else data.columns.nlevels,
    }


def _decode_pandas_state(io_, spec_args):
    # Rebuild read_args the way PandasData._init_spec does, from the
    # persisted shape metadata instead of the not-yet-loaded value.
    sheet = spec_args["sheet"]
    is_series = spec_args["is_series"]
    read_args = {}
    if not is_series and spec_args["columns_nlevels"] > 1:
        read_args["header"] = list(range(spec_args["columns_nlevels"]))
    if spec_args["index_nlevels"] > 1:
        read_args["index_col"] = list(range(spec_args["index_nlevels"]))
    else:
        read_args["index_col"] = 0
    if io_.file_type == "excel":
        suffix = io_.path.suffix
        if len(suffix[1:]) > 3 and suffix[1:4] == "xls":
            read_args["engine"] = "openpyxl"
        if sheet:
            read_args["sheet_name"] = sheet
    return {
        "read_args": read_args,
        "squeeze": is_series,
        "name": spec_args["name"],
        "sheet": sheet,
    }


def _encode_excel_range_params(spec):
    return {
        "range": spec.range,
        "sheet": spec.sheet,
        "keyids": spec.keyids,
    }


def _decode_excel_range_state(io_, spec_args):
    keyids = spec_args["keyids"]
    return {
        "range": spec_args["range"],
        "sheet": spec_args["sheet"],
        "keyids": tuple(keyids) if keyids else None,
    }


def _encode_module_params(spec):
    return {}


def _decode_module_state(io_, spec_args):
    return {}


_PARAM_ENCODERS = {
    "PandasData": _encode_pandas_params,
    "ExcelRange": _encode_excel_range_params,
    "ModuleData": _encode_module_params,
}

_STATE_DECODERS = {
    "PandasData": _decode_pandas_state,
    "ExcelRange": _decode_excel_range_state,
    "ModuleData": _decode_module_state,
}

_COMMENT_FIELDS = {
    "PandasData": lambda spec: [
        ("path", spec.io.path.as_posix()),
        ("file_type", spec.io.file_type),
        ("sheet", spec.sheet)],
    "ExcelRange": lambda spec: [
        ("path", spec.io.path.as_posix()),
        ("range", spec.range),
        ("sheet", spec.sheet),
        ("keyids", spec.keyids)],
    "ModuleData": lambda spec: [
        ("path", spec.io.path.as_posix())],
}


def _check_spec_supported(spec):
    clsname = type(spec).__name__
    if clsname not in _PARAM_ENCODERS:
        raise TypeError(
            "serializer version 8 does not support "
            "IO spec type '%s'" % clsname)
    return clsname


def _spec_comment(spec):
    clsname = _check_spec_supported(spec)
    parts = ["%s=%r" % (name, value)
             for name, value in _COMMENT_FIELDS[clsname](spec)
             if value is not None]
    return " ".join([clsname] + parts)


def _check_literal(value, spec):
    """Verify ``value`` round-trips through repr / ast.literal_eval.

    Checks exact types, not isinstance: numpy scalars subclass Python
    scalars (or repr as constructor calls) and would not parse back.
    """
    t = type(value)
    if t in (str, int, bool, type(None)):
        return
    if t is float:
        # repr of nan/inf ('nan', 'inf') is not a literal
        if value != value or value in (float("inf"), float("-inf")):
            raise TypeError(
                "cannot serialize non-finite float %r of %r" % (value, spec))
        return
    if t in (tuple, list):
        for item in value:
            _check_literal(item, spec)
        return
    if t is dict:
        for key, item in value.items():
            _check_literal(key, spec)
            _check_literal(item, spec)
        return
    raise TypeError(
        "parameter %r of %r is not literal-representable" % (value, spec))


def _spec_entry(key, spec):
    clsname = _check_spec_supported(spec)
    entry = (
        key,
        clsname,
        spec.io.path.as_posix(),
        dict(spec.io.persistent_args),
        _PARAM_ENCODERS[clsname](spec),
    )
    _check_literal(entry, spec)
    return entry


def _encode_iospecs(iospecs):
    lines = [IOSPECS_HEADER]
    for key, spec in iospecs.items():
        lines.append(repr(_spec_entry(key, spec)) + "\n")
    return "".join(lines)


# --------------------------------------------------------------------------
# Model Writing


class IOSpecEncoder(serializer_6.IOSpecEncoder):

    def encode(self):
        spec = self.writer.iospec_by_value[id(self.target.value)]
        return "(\"IOSpec\", %s)  # %s" % (
            self.writer.assign_id(spec), _spec_comment(spec))

    def instruct(self):
        # Unlike versions 6/7, the value does not enter pickledata
        # through the ref site: the decoder returns spec.value directly.
        return None


class EncoderSelector(serializer_6.BaseSelector):

    classes = [
        serializer_6.InterfaceRefEncoder,
        serializer_6.LiteralEncoder,
        IOSpecEncoder,
        serializer_6.ModuleEncoder,
        serializer_6.PickleEncoder
    ]


class RefViewEncoder(serializer_6.RefViewEncoder):

    def __init__(self, writer, target, parent, name=None, srcpath=None):
        serializer_6.BaseEncoder.__init__(
            self, writer, target, parent, name, srcpath,
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


class ModelEncoder(serializer_7.ModelEncoder):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refview_encoder = RefViewEncoder(
            self.writer,
            self.model.refs,
            parent=self.model,
            srcpath=self.srcpath
        )


class SpaceEncoder(serializer_7.SpaceEncoder):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refview_encoder = RefViewEncoder(
            self.writer,
            self.space._own_refs,
            parent=self.space,
            srcpath=self.srcpath
        )


class ModelWriter(serializer_7.ModelWriter):

    version = 8

    def validate_model(self):
        """Fail unwritable models before any output is touched.

        Called by :func:`modelx.serialize.write_model` before the
        backup rotation and before any file is written: every IO spec
        must be declarable in the version-8 literal format (supported
        class, literal-representable parameters), so a model that
        cannot be saved fails cleanly instead of leaving a partial
        tree over a rotated-away previous save. Must not call
        ``assign_id``: ids are assigned in traversal order during the
        write proper, and assigning them here in ``model.iospecs``
        order would change the emitted ids.
        """
        for spec in self.model.iospecs:
            _spec_entry(0, spec)

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
            self._write_macros()
            self.write_pickledata()
            self._reorder_io_specs()
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
            # Assign ids to any spec the traversal did not reach, then
            # key the dict in id order: model.iospecs order is
            # ref-registration order, which a save -> load round trip
            # does not preserve.
            iospecs = dict(sorted(
                (self.assign_id(sp), sp) for sp in self.model.iospecs))
            ziputil.write_str_utf8(
                _encode_iospecs(iospecs),
                self.temp_root / IOSPECS_FILE,
                compression=self.compression,
                compresslevel=self.compresslevel
            )
        if self.pickledata:
            file = self.temp_root / "_data/data.pickle"
            ziputil.write_file_utf8(
                lambda f: DeterministicModelPickler(
                    f, writer=self).dump(self.pickledata),
                file, mode="b",
                compression=self.compression,
                compresslevel=self.compresslevel
            )


# --------------------------------------------------------------------------
# Model Reading


class RefAssignParser(serializer_6.RefAssignParser):

    def set_instruction(self):

        # Ref sites may carry a trailing readability comment, which
        # get_statement_tokens keeps in the statement's token list.
        stmt = self.stmt
        while stmt and stmt[-1].type in (tokenize.COMMENT, tokenize.NL):
            stmt.pop()

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
                or not isinstance(decoder, serializer_6.TupleDecoder)
                or decoder.size() < 3):
            setter = serializer_6.Instruction.from_method(
                obj=self.obj,
                method="__setattr__",
                args=(name, value),
                arghook=arghook
            )
        else:
            refmode = decoder.value[2]
            setter = serializer_6.Instruction.from_method(
                obj=self.obj,
                method="set_ref",
                args=(name, value),
                arghook=arghook,
                kwargs={'refmode': refmode}
            )
        self.instructions.append(setter)
        return setter


class ParserSelector(serializer_6.BaseSelector):
    classes = [
        serializer_7.DocstringParser,
        serializer_6.ImportFromParser,
        serializer_6.RenameParser,
        serializer_6.LambdaAssignParser,
        serializer_6.LambdaDocstringParser,
        serializer_6.ParentAttrAssignParser,
        serializer_6.CellsAttrAssignParser,
        RefAssignParser,
        serializer_6.SpaceFuncDefParser,
        serializer_6.CellsFuncDefParser
    ]


class IOSpecDecoder(serializer_6.TupleDecoder):
    DECTYPE = "IOSpec"

    def decode(self):
        return self.value[1]

    def restore(self):
        iospecs = self.reader.iospecs
        spec = (iospecs.get(self.decode())
                if isinstance(iospecs, dict) else None)
        if spec is None:
            self._warn_lost_ref()
            return None
        return spec.value


class DecoderSelector(serializer_6.BaseSelector):
    classes = [
        serializer_6.InterfaceDecoder,
        IOSpecDecoder,
        serializer_6.ModuleDecoder,
        serializer_6.PickleDecoder,
        serializer_6.LiteralDecoder
    ]


class ModelReader(serializer_7.ModelReader):

    version = ModelWriter.version

    def parse_source(self, path_, obj):

        for stmt in get_statement_tokens(path_):
            parser = ParserSelector.select(stmt)(
                stmt, self, obj, srcpath=path_
            )
            parser.set_instruction()

    def read_pickledata(self):

        def custom_load(file):
            unpickler = ModelUnpickler(file, self)
            return unpickler.load()

        file = self.path / IOSPECS_FILE
        if ziputil.exists(file):
            self._read_iospec_literals(file)

        file = self.path / "_data/data.pickle"
        if ziputil.exists(file):
            try:
                self.pickledata = ziputil.read_file_utf8(
                    custom_load, file, "b")
            except Exception:
                from .tolerant_pickle import load_pickle_tolerantly
                self.pickledata = load_pickle_tolerantly(
                    self, file, kind="model")

        if self.unpickle_errors:
            from .tolerant_pickle import finalize_tolerant_read
            finalize_tolerant_read(self)

    def _read_iospec_literals(self, file):
        manager = self.system.iomanager
        # Rollback point mirroring IOSpecUnpickler.__init__: a read
        # aborting after this must be able to discard the ios/specs
        # registered here.
        self.io_journal_mark = manager.journal_mark()
        self.iospecs = {}
        try:
            lines = ziputil.read_file_utf8(
                lambda f: f.readlines(), file, "t")
        except Exception as exc:
            # Parity with the unreadable-iospecs.pickle behavior of
            # versions 4-7: lose the specs, keep loading the model.
            self.unpickle_errors.append(exc)
            warnings.warn(
                "'%s' could not be read (%r); "
                "all IO specs stored in it are lost"
                % (file.as_posix(), exc))
            return
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                entry = ast.literal_eval(stripped)
                key, clsname, pathstr, io_args, spec_args = entry
            except Exception as exc:
                self.unpickle_errors.append(exc)
                warnings.warn(
                    "A line in '%s' could not be parsed (%r); "
                    "references to the IO spec it declares could not "
                    "be restored" % (file.as_posix(), exc))
                continue
            if not isinstance(key, int) or key in self.iospecs:
                # A malformed key must not escape the per-line
                # tolerance, and a duplicate line must not clobber (or
                # re-register a twin of) an already-restored spec.
                exc = ValueError(
                    "invalid or duplicate IO spec key: %r" % (key,))
                self.unpickle_errors.append(exc)
                warnings.warn(
                    "A line in '%s' was skipped (%r)"
                    % (file.as_posix(), exc))
                continue
            try:
                spec = self._restore_iospec(
                    clsname, pathstr, io_args, spec_args)
            except Exception as exc:
                self.unpickle_errors.append(exc)
                # Recorded as lost: ref sites restore to None and
                # ModelUnpickler._find_iospec degrades too
                self.iospecs[key] = None
                warnings.warn(
                    "IO spec (key: %s) in '%s' could not be restored "
                    "(%r); references to it are set to None"
                    % (key, file.as_posix(), exc))
                continue
            self.iospecs[key] = spec

    def _restore_iospec(self, clsname, pathstr, io_args, spec_args):
        manager = self.system.iomanager
        cls = _get_spec_class(clsname)
        path = pathlib.Path(pathstr)

        if not path.is_absolute():
            src = self.path.joinpath(path)
            if self.temproot:
                dst = self.temproot.joinpath(path)
                if not dst.exists():
                    ziputil.copy_file(src, dst, None, None)
                loadpath = dst
            else:
                loadpath = src
        else:
            loadpath = path

        io_ = manager.get_or_create_io(
            io_group=self.model, path=path, cls=cls.io_class,
            load_from=loadpath, **io_args)

        state = _STATE_DECODERS[clsname](io_, spec_args)
        state["manager"] = manager
        state["_io"] = io_
        spec = cls.__new__(cls)
        # serializing is True during a read, so __setstate__ runs
        # _on_unserialize (which loads the value from the IO file) and
        # registers the spec through IOManager.add_spec, exactly as
        # when the spec came from iospecs.pickle in versions 5-7.
        spec.__setstate__(state)
        return spec
