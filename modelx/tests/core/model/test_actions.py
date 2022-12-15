import modelx as mx


def test_action():
    # Sample from https://modelx.io/blog/2022/03/26/running-model-while-saving-memory/

    m = mx.new_model()
    s = m.new_space()

    @mx.defcells
    def Cells1():
        return 1

    @mx.defcells
    def Cells2(x):
        if x > 0:
            return Cells2(x-1)
        else:
            return Cells1()

    @mx.defcells
    def Cells3(x):
        return Cells1() + Cells2(x)

    expected = [
        ['calc', [s.Cells1.node(), s.Cells2.node(x=0)]],
        ['paste', [s.Cells2.node(x=0), s.Cells1.node()]],
        ['clear', []],
        ['calc', [s.Cells2.node(x=1), s.Cells2.node(x=2)]],
        ['paste', [s.Cells2.node(x=2)]],
        ['clear', [s.Cells2.node(x=1), s.Cells2.node(x=0)]],
        ['calc', [s.Cells3.node(x=2)]],
        ['paste', [s.Cells3.node(x=2)]],
        ['clear', [s.Cells1.node(), s.Cells2.node(x=2)]]]

    actions = m.generate_actions([s.Cells3.node(2)], step_size=2)
    assert expected == actions
    m.execute_actions(actions)

    assert not dict(s.Cells1)
    assert not dict(s.Cells2)
    assert dict(s.Cells3)
    assert s.Cells3.is_input(2)

    m._impl._check_sanity()
    m.close()

    
    




