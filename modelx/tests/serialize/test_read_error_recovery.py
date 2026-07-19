"""Failed model reads must not disturb pre-existing models.

``read_model`` for serializer versions 4-7 builds the new model in the
live system, renaming it to its saved name during parsing and thereby
displacing a same-named existing model to ``<name>_BAK<n>``.  When the
read fails partway, besides closing the half-built model, the reader
must rename the displaced model back and make the previously current
model current again (see modelx/serialize/reader_state.py).

The corruption used here truncates a space file mid-statement: the root
``__init__.py`` (holding ``_name``) parses fine, so the load aborts
after the displacing rename has already happened - the worst case.
"""

import pathlib
import shutil
import tokenize
import warnings

import pytest

import modelx as mx
from modelx.tests.testdata.serializer_compat import fixturemodel

DATADIR = pathlib.Path(fixturemodel.__file__).parent

VERSIONS = [4, 5, 6, 7]

PARSE_ERRORS = (SyntaxError, tokenize.TokenError)


def _copy_and_corrupt(version, tmp_path):
    src = DATADIR / ("model_v%s" % version)
    dst = tmp_path / src.name
    shutil.copytree(str(src), str(dst))
    spacefile = dst / "Base" / "__init__.py"
    spacefile.write_text(spacefile.read_text() + "\nbroken = (\n")
    return dst


@pytest.mark.parametrize("version", VERSIONS)
def test_failed_read_restores_displaced_model(
        version, tmp_path, close_new_models):
    """The displaced same-named model gets its original name back."""
    existing = mx.new_model("SerializerCompat")
    names_before = set(mx.get_models())
    path = _copy_and_corrupt(version, tmp_path)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(PARSE_ERRORS):
            mx.read_model(str(path))

    # The read did rename the existing model away before failing
    assert any("renamed to" in str(w.message) for w in caught)

    assert mx.get_models().get("SerializerCompat") is existing
    assert set(mx.get_models()) == names_before
    assert mx.cur_model() is existing


@pytest.mark.parametrize("version", VERSIONS)
def test_failed_read_restores_current_model(
        version, tmp_path, close_new_models):
    """The previously current model is current again after a failed read."""
    prior = mx.new_model("PriorModel")
    names_before = set(mx.get_models())
    path = _copy_and_corrupt(version, tmp_path)

    with pytest.raises(PARSE_ERRORS):
        mx.read_model(str(path))

    assert mx.cur_model() is prior
    assert set(mx.get_models()) == names_before


@pytest.mark.parametrize("version", VERSIONS)
def test_failed_read_without_prior_models(
        version, tmp_path, close_new_models):
    """A failed read leaves whatever was there before untouched."""
    names_before = set(mx.get_models())
    cur_before = mx.cur_model()
    path = _copy_and_corrupt(version, tmp_path)

    with pytest.raises(PARSE_ERRORS):
        mx.read_model(str(path))

    assert set(mx.get_models()) == names_before
    assert mx.cur_model() is cur_before


@pytest.mark.parametrize("version", VERSIONS)
def test_successful_read_still_displaces(version, tmp_path, close_new_models):
    """On success the displaced model intentionally keeps its backup name."""
    existing = mx.new_model("SerializerCompat")

    with pytest.warns(UserWarning, match="renamed to"):
        m = mx.read_model(str(DATADIR / ("model_v%s" % version)))

    assert mx.get_models().get("SerializerCompat") is m
    assert existing.name.startswith("SerializerCompat_BAK")
    assert mx.cur_model() is m
    fixturemodel.check_fixture_model(m)
