import modelx as mx


def test_new_cells_on_base_when_a_sub_has_it():
    """
        Base---Sub1---foo
         +-foo  |
                +-Sub2

        https://github.com/fumitoh/modelx/issues/138
    """
    m = mx.new_model()
    base = m.new_space('Base')
    sub1 = m.new_space('Sub1', bases=base)
    sub2 = m.new_space('Sub2', bases=base)

    sub1.new_cells('foo')
    base.new_cells('foo')
    assert 'foo' in sub2