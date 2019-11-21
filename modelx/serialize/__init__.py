import pathlib
import importlib
import shutil
import json


_MX_TO_FORMAT = {
    (0, 0, 25): 1,
    (0, 0, 26): 2
}

HIGHEST_VERSION = list(_MX_TO_FORMAT.values())[-1]
DEFAULT_MAX_BACKUPS = 3

def _get_serializer(version):
    return importlib.import_module(
        ".serializer_%s" % version, "modelx.serialize")


def _increment_backups(base_path, max_backups=DEFAULT_MAX_BACKUPS, nth=0):

    postfix = "_BAK" + str(nth) if nth else ""
    backup_path = pathlib.Path(str(base_path) + postfix)
    if backup_path.exists():
        if nth == max_backups:
            shutil.rmtree(backup_path)
        else:
            _increment_backups(base_path, max_backups, nth + 1)
            next_backup = pathlib.Path(str(base_path) + "_BAK" + str(nth + 1))
            backup_path.rename(next_backup)


def _get_model_serializer(model_path):

    try:
        with open(model_path / "_system.json", "r", encoding="utf-8") as f:
            params = json.load(f)
    except FileNotFoundError:
        return _get_serializer(1)

    return _get_serializer(params["serializer_version"])


def write_model(system, model, model_path, backup=True, version=None):

    version = version or HIGHEST_VERSION
    max_backups = DEFAULT_MAX_BACKUPS if backup else 0

    path = pathlib.Path(model_path)
    _increment_backups(path, max_backups)
    path.mkdir()
    with open(path / "_system.json", "w", encoding="utf-8") as f:
        json.dump({"serializer_version": version}, f)


    serializer = _get_serializer(version)
    serializer.ModelWriter(system, model, path).write_model()


def read_model(model_path, name=None):
    kwargs = {"name": name} if name else {}
    path = pathlib.Path(model_path)
    return _get_model_serializer(path).ModelReader(path).read_model(**kwargs)
