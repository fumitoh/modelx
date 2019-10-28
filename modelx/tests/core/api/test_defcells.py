import modelx as mx


def test_defcells_cur_model_none():

    if mx.cur_model():
        mx.cur_model().close()
        assert not mx.cur_model()
        assert not mx.cur_space()

    @mx.defcells
    def foo():
        return True

    assert mx.cur_space().foo is foo


def test_defcells_update_formula():

    def existing_cells(x):
        return existing_cells(x-1) if x > 0 else 0

    cells = mx.new_model().new_space().new_cells(formula=existing_cells)
    assert cells[10] == 0

    @mx.defcells
    def existing_cells(x):
        return existing_cells(x-1) if x > 0 else 1

    assert existing_cells[10] == 1
    assert existing_cells is cells
