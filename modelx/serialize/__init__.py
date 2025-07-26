import os
import stat
import errno
import pathlib
import importlib
import shutil
import json
import sys
import zipfile
import modelx
from . import ziputil


_MX_TO_FORMAT = {
    (0, 0, 25): 1,
    (0, 1, 0): 2,
    (0, 2, 0): 3,
    (0, 9, 0): 4,
    (0, 18, 0): 5,
    (0, 22, 0): 6
}

HIGHEST_VERSION = list(_MX_TO_FORMAT.values())[-1]
DEFAULT_MAX_BACKUPS = 3


def _get_serializer(version):
    return importlib.import_module(
        ".serializer_%s" % version, "modelx.serialize")


def _handle_remove_readonly(func, path, exc):
    # Workaround for WindowsError: [Error 5] Access is denied
    # https://github.com/fumitoh/modelx/issues/181
    # Modified from: https://stackoverflow.com/a/1214935/2400267

    if sys.version_info >= (3, 12):
        excvalue = exc
    else:
        excvalue = exc[1]
    if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
        func(path)
    else:
        raise


def _increment_backups(
        model, base_path: pathlib.Path,
        max_backups=DEFAULT_MAX_BACKUPS, nth=0):

    postfix = "_BAK" + str(nth) if nth else ""
    backup_path = pathlib.Path(str(base_path) + postfix)
    if backup_path.exists():
        if nth == max_backups:
            if backup_path.is_dir():
                kwargs = {}
                if sys.platform == "win32":
                    if sys.version_info >= (3, 12):
                        kwargs["onexc"] = _handle_remove_readonly
                    else:
                        kwargs["onerror"] = _handle_remove_readonly

                shutil.rmtree(backup_path, **kwargs)
            elif backup_path.is_file():
                backup_path.unlink()
            else:
                raise ValueError("cannot remove '%s'" % str(backup_path))
        else:
            _increment_backups(model, base_path, max_backups, nth + 1)
            next_backup = pathlib.Path(str(base_path) + "_BAK" + str(nth + 1))
            backup_path.rename(next_backup)


def _get_model_metadata(model_path):

    try:
        params = ziputil.read_file(
            json.load,
            model_path / "_system.json",
            "t"
        )
    except FileNotFoundError:
        return None
    except KeyError:
        return None

    return params


def write_model(system, model, model_path,
                is_zip, backup=True, log_input=False,
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=None,
                version=None):

    version = version or HIGHEST_VERSION
    max_backups = DEFAULT_MAX_BACKUPS if backup else 0

    root = pathlib.Path(model_path)
    _increment_backups(model, root, max_backups)

    serializer = _get_serializer(version)
    serializer.ModelWriter(system, model, root,
                           is_zip=is_zip,
                           log_input=log_input,
                           compression=compression,
                           compresslevel=compresslevel
                           ).write_model()

    if model.path != root:
        model.path = root
    return model


def read_model(system, model_path, name=None):

    kwargs = {"name": name} if name else {}
    path = pathlib.Path(model_path)
    params = _get_model_metadata(path)

    if params:
        serializer = _get_serializer(params["serializer_version"])
        if "modelx_version" in params:
            kwargs["modelx_version"] = tuple(params["modelx_version"])
    else:
        serializer = _get_serializer(1)

    model = serializer.ModelReader(system, path).read_model(**kwargs)
    model.path = path
    return model
