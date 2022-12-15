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

    m._impl._check_sanity()
    m.close()


def test_dyn_add_base_ref_after():
    # https://github.com/fumitoh/modelx/issues/37

    m = mx.new_model()
    s = m.new_space("SpaceA", formula=lambda t: None)
    a1 = m.SpaceA(1)
    m.SpaceA.x = 1
    assert a1 is m.SpaceA(1)

    m._impl._check_sanity()
    m.close()