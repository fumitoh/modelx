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


def write_model(model, model_path, backup=True, version=None):
    """Write model to files.

    Write ``model`` to text files in a folder(directory) tree at ``model_path``.

    Model attributes, such as its name and refs, are output in the file
    named *_model.py*, directly under `model_path`.
    For each space in the model, a text file is created with the same name
    as the space with ".py" extension. The tree structure of the spaces
    is represented by the tree of folders, i.e. child spaces
    of a space is stored in a folder named the space.

    Generated text files are Python pseudo-scripts, i.e. they are
    syntactically correct but semantically not-correct Python scripts,
    that can only be interpreted through :py:func:`~read_model` function.

    Dynamic spaces and cells values are not stored.

    For spaces and cells created
    by :py:meth:`~modelx.core.space.UserSpace.new_space_from_excel` and
    :py:meth:`~modelx.core.space.UserSpace.new_cells_from_excel`,
    the source Excel files are copied into the same directory where
    the text files for the spaces the methods are associated with are located.
    Then when the model is read by :py:func:`~read_model` function,
    the methods are invoked to create the spaces or cells.

    Method :py:meth:`~modelx.core.model.Model.write` performs the same operation.

    .. versionadded:: 0.0.22

    Warning:
        The order of members of each type (Space, Cells, Ref)
        is not preserved by :func:`write_model` and :func:`read_model`.

    Args:
        model: Model object to write.
        model_path(str): Folder path where the model will be output.
        backup(bool, optional): Whether to backup the directory/folder
            if it already exists. Defaults to ``True``.
        version(int, optional): Format version to write model.
            Defaults to the most recent version.

    """
    version = version or HIGHEST_VERSION
    max_backups = DEFAULT_MAX_BACKUPS if backup else 0

    path = pathlib.Path(model_path)
    _increment_backups(path, max_backups)
    path.mkdir()
    with open(path / "_system.json", "w", encoding="utf-8") as f:
        json.dump({"serializer_version": version}, f)


    serializer = _get_serializer(version)
    serializer.ModelWriter(model, path).write_model()


def read_model(model_path, name=None):
    """Read model from files.

    Read model form a folder(directory) tree ``model_path``.
    The model must be saved by :py:func:`~write_model` function or
    :py:meth:`~modelx.core.model.Model.write` method.

    .. versionadded:: 0.0.22

    Args:
        model_path(str): A folder(directory) path where model is stored.
        name(str, optional): Model name to overwrite the saved name.

    Returns:
        A Model object constructed from the files.

    """
    kwargs = {"name": name} if name else {}
    path = pathlib.Path(model_path)
    return _get_model_serializer(path).ModelReader(path).read_model(**kwargs)
