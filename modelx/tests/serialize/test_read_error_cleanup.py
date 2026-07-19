"""Failed model reads must not leave residue in the global IOManager.

During a read, IOSpecs and SharedIOs are registered in the process-global
IOManager before the __setattr__/set_ref batch makes them reachable from
the model's ValueRegistry, so the error path's model.close() cannot see
them. The readers journal every registration and roll the journal back
when the read fails (see IOManager.rollback_journal), and the tolerant
retry rolls back the aborted strict attempt's registrations so its stale
specs cannot veto the retried ones (see
tolerant_pickle.load_pickle_tolerantly).
"""

import warnings

import pytest

import modelx as mx
from modelx.core.system import mxsys
from modelx.serialize import serializer_6

pd = pytest.importorskip("pandas")

VERSIONS = [6, 7]


@pytest.fixture
def sample_df():
    return pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})


def _write_io_model(tmp_path, name, df, version, zipped=False):
    """Write a model with an absolute-path and a relative-path PandasData.

    The absolute-path spec is created first so it precedes the relative
    one in iospecs.pickle: an aborted strict unpickling pass then has
    already registered it, which is the trigger for the stale-twin bug
    covered by test_tolerant_retry_keeps_healthy_abs_ref."""
    m = mx.new_model(name)
    s = m.new_space("Space1")
    s.new_pandas(name="df_abs", path=str(tmp_path / "external" / "df_abs.csv"),
                 data=df, file_type="csv")
    s.new_pandas(name="df_rel", path="data/df_rel.csv",
                 data=df.copy(), file_type="csv")
    path = tmp_path / ("model.zip" if zipped else "model")
    write = mx.zip_model if zipped else mx.write_model
    write(m, str(path), version=version)
    m.close()
    return path


class _InjectedError(Exception):
    pass


@pytest.fixture
def fail_at(monkeypatch):
    """Make the instruction batch containing a given method raise."""
    def _install(method):
        orig = serializer_6.CompoundInstruction.execute_selected_methods

        def raising(self, methods, pop_executed=True):
            if method in methods:
                raise _InjectedError("injected failure")
            return orig(self, methods, pop_executed)

        monkeypatch.setattr(
            serializer_6.CompoundInstruction,
            "execute_selected_methods", raising)
    return _install


# "set_ref" fails before refs reach the ValueRegistry (rollback must
# remove everything); "_set_dynamic_inputs" fails after (model.close()
# removes the specs first and rollback must skip them); "add_bases"
# fails before read_pickledata (empty journal).
FAIL_METHODS = ["set_ref", "_set_dynamic_inputs", "add_bases"]


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize("fail_method", FAIL_METHODS)
def test_failed_read_leaves_no_io_residue(
        tmp_path, sample_df, version, fail_method, fail_at,
        close_new_models):
    """A failed read leaves the iomanager as it was before the read."""
    path = _write_io_model(tmp_path, "LeakTest", sample_df, version)
    baseline = set(mxsys.iomanager.ios)     # entries left by other tests
    fail_at(fail_method)

    with pytest.raises(_InjectedError):
        mx.read_model(str(path))

    assert set(mxsys.iomanager.ios) == baseline
    assert "LeakTest" not in mx.get_models()
    assert mxsys.serializing is None
    assert mxsys.iomanager.serializing is None
    assert mxsys.iomanager._journal is None


@pytest.mark.parametrize("version", VERSIONS)
def test_failed_read_zip_no_residue(
        tmp_path, sample_df, version, fail_at, close_new_models):
    """Same as above for a zipped model (temproot path)."""
    path = _write_io_model(
        tmp_path, "LeakTestZip", sample_df, version, zipped=True)
    baseline = set(mxsys.iomanager.ios)
    fail_at("set_ref")

    with pytest.raises(_InjectedError):
        mx.read_model(str(path))

    assert set(mxsys.iomanager.ios) == baseline
    assert mxsys.iomanager._journal is None


@pytest.mark.parametrize("version", VERSIONS)
def test_read_retry_after_failure(
        tmp_path, sample_df, version, monkeypatch, close_new_models):
    """Re-reading the same model after a failed read loads it intact."""
    path = _write_io_model(tmp_path, "RetryTest", sample_df, version)
    baseline = set(mxsys.iomanager.ios)

    orig = serializer_6.CompoundInstruction.execute_selected_methods

    def raising(self, methods, pop_executed=True):
        if "set_ref" in methods:
            raise _InjectedError("injected failure")
        return orig(self, methods, pop_executed)

    with monkeypatch.context() as mp:
        mp.setattr(serializer_6.CompoundInstruction,
                   "execute_selected_methods", raising)
        with pytest.raises(_InjectedError):
            mx.read_model(str(path))

    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        m = mx.read_model(str(path))

    assert mxsys.iomanager._journal is None
    pd.testing.assert_frame_equal(m.Space1.df_rel, sample_df)
    pd.testing.assert_frame_equal(m.Space1.df_abs, sample_df)
    assert len(m.iospecs) == 2

    m.close()
    assert set(mxsys.iomanager.ios) == baseline


@pytest.mark.parametrize("version", VERSIONS)
def test_failed_read_keeps_other_models_ios(
        tmp_path, sample_df, version, fail_at, close_new_models):
    """Rollback removes only the failed read's registrations."""
    live = mx.new_model("LiveModel")
    live.new_space("S").new_pandas(
        name="df_live", path=str(tmp_path / "live" / "df_live.csv"),
        data=sample_df, file_type="csv")

    path = _write_io_model(tmp_path, "LeakTest2", sample_df, version)
    baseline = set(mxsys.iomanager.ios)     # includes LiveModel's io
    fail_at("set_ref")

    with pytest.raises(_InjectedError):
        mx.read_model(str(path))

    assert set(mxsys.iomanager.ios) == baseline
    assert len(live.iospecs) == 1
    pd.testing.assert_frame_equal(live.S.df_live, sample_df)


def test_rollback_keeps_other_groups(sample_df, close_new_models):
    """A spec created on another model while a journal is active (e.g. by
    module code executed during unpickling) survives a rollback scoped
    to the reading model."""
    live = mx.new_model("JournalLive")
    reading = mx.new_model("JournalReading")
    manager = mxsys.iomanager
    baseline = set(manager.ios)

    manager.begin_journal()
    try:
        mark = manager.journal_mark()
        live.new_space("S").new_pandas(
            name="df_live", path="data/df_live.csv",
            data=sample_df, file_type="csv")
        manager.rollback_journal(mark, io_group=reading)
    finally:
        manager.end_journal()

    assert len(live.iospecs) == 1
    pd.testing.assert_frame_equal(live.S.df_live, sample_df)

    live.close()
    reading.close()
    assert set(manager.ios) == baseline


@pytest.mark.parametrize("version", VERSIONS)
def test_failed_read_keeps_shared_abs_io(
        tmp_path, sample_df, version, fail_at, close_new_models):
    """Rolling back a spec journaled on a pre-owned absolute-path io
    keeps the io and the other model's spec."""
    pytest.importorskip("openpyxl")
    xlsx = str(tmp_path / "shared" / "shared.xlsx")

    ma = mx.new_model("ShareA")
    ma.new_space("S").new_pandas(
        name="df_a", path=xlsx, data=sample_df, file_type="excel",
        sheet="SA")
    mb = mx.new_model("ShareB")
    mb.new_space("S").new_pandas(
        name="df_b", path=xlsx, data=sample_df.copy(), file_type="excel",
        sheet="SB")

    path_a = tmp_path / "model_a"
    path_b = tmp_path / "model_b"
    mx.write_model(ma, str(path_a), version=version)
    mx.write_model(mb, str(path_b), version=version)
    ma.close()
    mb.close()

    ma2 = mx.read_model(str(path_a))    # owns the shared abs io now
    baseline = set(mxsys.iomanager.ios)
    fail_at("set_ref")

    with pytest.raises(_InjectedError):
        mx.read_model(str(path_b))

    assert set(mxsys.iomanager.ios) == baseline
    assert len(ma2.iospecs) == 1
    # check_dtype=False: the excel round-trip may narrow float columns
    pd.testing.assert_frame_equal(ma2.S.df_a, sample_df, check_dtype=False)


@pytest.mark.parametrize("version", VERSIONS)
def test_tolerant_pass_abort_leaves_no_residue(
        tmp_path, sample_df, version, close_new_models):
    """When the tolerant retry itself dies (stream truncated past what
    the wrapped opcode handlers tolerate), its registrations are rolled
    back so the model stays readable once the file is repaired."""
    path = _write_io_model(tmp_path, "AbortTest", sample_df, version)
    baseline = set(mxsys.iomanager.ios)
    iofile = path / "_data" / "iospecs.pickle"
    pristine = iofile.read_bytes()
    iofile.write_bytes(pristine[:-1])   # drop STOP: EOF after the specs
                                        # have been registered

    with pytest.warns(UserWarning, match="could not be read"):
        m = mx.read_model(str(path))
    assert m.Space1.df_abs is None
    assert m.Space1.df_rel is None
    m.close()
    assert set(mxsys.iomanager.ios) == baseline

    iofile.write_bytes(pristine)
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        m2 = mx.read_model(str(path))
    pd.testing.assert_frame_equal(m2.Space1.df_abs, sample_df)
    pd.testing.assert_frame_equal(m2.Space1.df_rel, sample_df)


@pytest.mark.parametrize("version", VERSIONS)
def test_tolerant_retry_keeps_healthy_abs_ref(
        tmp_path, sample_df, version, close_new_models):
    """A strict-pass abort must not null refs whose specs are healthy.

    Deleting the file behind the relative-path spec aborts the strict
    iospecs pass; the absolute-path spec registered by that aborted pass
    used to survive as a stale twin that vetoed its retried self, so the
    healthy df_abs ref came back None."""
    path = _write_io_model(tmp_path, "AbsKeepTest", sample_df, version)
    baseline = set(mxsys.iomanager.ios)
    (path / "data" / "df_rel.csv").unlink()

    with pytest.warns(UserWarning, match="could not be restored"):
        m = mx.read_model(str(path))

    assert m.Space1.df_rel is None
    pd.testing.assert_frame_equal(m.Space1.df_abs, sample_df)
    assert len(m.iospecs) == 1

    m.close()
    assert set(mxsys.iomanager.ios) == baseline
