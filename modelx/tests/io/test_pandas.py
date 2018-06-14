
import modelx as mx
import numpy as np
import pytest



@pytest.fixture
def testspace():

    model = mx.new_model()
    space = model.new_space()

    def f0():
        return 3

    def f1(x):
        return 2 * x

    def f2(x, y=1):
        return x + y

    f0, f1, f2 = mx.defcells(f0, f1, f2)

    return space

# -------------------------------------------------------------------------
# Test Conversion from Cells to DataFrame and Series

def test_cells_empty(testspace):

    for c in ['f0', 'f1', 'f2']:

        assert testspace.cells[c].to_series().empty
        assert testspace.cells[c].series.empty

        assert testspace.cells[c].to_frame().empty
        assert testspace.cells[c].frame.empty


@pytest.mark.parametrize('cells, args, length', [
    ['f0', ((),), 1],
    ['f1', (1, 2, 3), 3],
    ['f1', ((1, 2, 3),), 3],
    ['f2', ((1, 2), (3, 4), (5, 6)), 3],
    ['f2', (((1, 2), (3, 4), (5, 6))), 3]
])
def test_cells_to_frame_with_args(testspace, cells, args, length):
    assert len(testspace.cells[cells].to_frame(*args).index) == length
    assert len(testspace.cells[cells].to_frame()) == length
    assert len(testspace.cells[cells].frame) == length


@pytest.mark.parametrize('cells, args, length', [
    ['f0', ((),), 1],
    ['f1', (1, 2, 3), 3],
    ['f1', ((1, 2, 3),), 3],
    ['f2', ((1, 2), (3, 4), (5, 6)), 3],
    ['f2', (((1, 2), (3, 4), (5, 6)),), 3]
])
def test_cells_to_series_with_args(testspace, cells, args, length):
    assert len(testspace.cells[cells].to_series(*args).index) == length
    assert len(testspace.cells[cells].to_series()) == length
    assert len(testspace.cells[cells].series) == length

# -------------------------------------------------------------------------
# Test Conversion from Space to DataFrame


def test_space_to_frame_empty(testspace):
    assert testspace.to_frame().empty
    assert testspace.frame.empty


@pytest.mark.parametrize('args, idxlen, cols', [
    [((1, 2), (3, 4), (5, 6)), 7, {'f0', 'f1', 'f2'}],
    [(((1, 2), (3, 4), (5, 6)),), 7, {'f0', 'f1', 'f2'}]
])
def test_space_to_frame_args(testspace, args, idxlen, cols):
    assert testspace.to_frame().empty
    df = testspace.to_frame(*args)
    assert set(df.columns) == cols
    assert len(df.index) == idxlen
    if len(args) == 1:
        args = args[0]
    for arg in args:
        dfx = df.xs(arg[0], level='x')
        assert int(dfx.loc[dfx.index.isnull(), 'f1']) == testspace.f1(arg[0])
        assert df.loc[arg, 'f2'] == testspace.f2(*arg)


@pytest.mark.parametrize('args, idxlen, cols', [
    [(1, 2, 3), 7, {'f0', 'f1', 'f2'}],
    [((1, 2, 3),), 7, {'f0', 'f1', 'f2'}],
])
def test_space_to_frame_args_defaults(testspace, args, idxlen, cols):
    assert testspace.to_frame().empty
    df = testspace.to_frame(*args)
    assert set(df.columns) == cols
    assert len(df.index) == idxlen
    if isinstance(args[0], tuple):
        args = args[0]
    for arg in args:
        assert df.loc[(arg, 1), 'f2'] == testspace.f2(arg, 1)


# -------------------------------------------------------------------------
# Test Conversion from CellsView to DataFrame

@pytest.mark.parametrize('args, idxlen, cols', [
    [((1, 2), (3, 4), (5, 6)), 7, ['f0', 'f1', 'f2']],
    [(((1, 2), (3, 4), (5, 6)),), 7, ['f0', 'f1', 'f2']]
])
def test_cellsview_to_frame_args(testspace, args, idxlen, cols):
    assert testspace.cells[cols].to_frame().empty
    df = testspace.cells[cols].to_frame(*args)
    assert set(df.columns) == set(cols)
    assert len(df.index) == idxlen
    if len(args) == 1:
        args = args[0]
    for arg in args:
        dfx = df.xs(arg[0], level='x')
        assert int(dfx.loc[dfx.index.isnull(), 'f1']) == testspace.f1(arg[0])
        assert df.loc[arg, 'f2'] == testspace.f2(*arg)


@pytest.mark.parametrize('args, idxlen, cols', [
    [(1, 2, 3), 7, ['f0', 'f1', 'f2']],
    [((1, 2, 3),), 7, ['f0', 'f1', 'f2']],
])
def test_cellsview_to_frame_args_defaults(testspace, args, idxlen, cols):
    assert testspace.cells[cols].to_frame().empty
    df = testspace.cells[cols].to_frame(*args)
    assert set(df.columns) == set(cols)
    assert len(df.index) == idxlen
    if isinstance(args[0], tuple):
        args = args[0]
    for arg in args:
        assert df.loc[(arg, 1), 'f2'] == testspace.f2(arg, 1)