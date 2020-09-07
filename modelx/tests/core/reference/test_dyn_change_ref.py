import modelx as mx


def test_dyn_change_ref():

    m = mx.new_model()
    s = mx.new_space('Parent')
    c = s.new_space('Child')

    s.a = 1
    c.b = 2
    s.parameters = ('i',)
    c.parameters = ('j',)

    assert s[1].a == 1
    assert s[1].Child[2].b == 2
    s.a = 3
    c.b = 4
    assert s[1].a == 3
    assert s[1].Child[2].b == 4

