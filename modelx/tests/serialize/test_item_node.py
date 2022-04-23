
import pytest
import modelx as mx


@pytest.fixture
def model_for_item_node_test(tmp_path):

    m = mx.new_model('model_for_item_node_test')
    space = m.new_space('Space1')
    space.parameters = ('i',)

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

    space.C3 = Cells3.node(2)
    space.CL = [Cells3.node(2), Cells1.node()]

    space[1].Cells1()
    space[2]

    m.S1 = space.node(1)
    m.SL = [space.node(1), space.node(2), space[1].Cells3.node(2)]

    space.actions = m.generate_actions([space.Cells3.node(2)], step_size=2)

    m.write(tmp_path / 'model')
    m.close()

    yield mx.read_model(tmp_path / 'model')
    mx.get_models()['model_for_item_node_test'].close()


def test_cells_node(model_for_item_node_test):

    m = model_for_item_node_test
    s = m.Space1

    assert s.C3 == s.Cells3.node(2)
    assert s.CL == [s.Cells3.node(2), s.Cells1.node()]
    assert m.S1 == s.node(1)
    assert m.SL == [s.node(1), s.node(2), s[1].Cells3.node(2)]


def test_actions(model_for_item_node_test):

    m = model_for_item_node_test
    s = m.Space1
    m.execute_actions(s.actions)
    assert not dict(s.Cells1)
    assert not dict(s.Cells2)
    assert dict(s.Cells3)
    assert s.Cells3.is_input(2)



