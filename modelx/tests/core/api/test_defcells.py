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
