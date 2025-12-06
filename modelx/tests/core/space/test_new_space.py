import modelx as mx


def test_new_space_when_parent_has_itemspace():

    # https://github.com/fumitoh/modelx/issues/203

    m = mx.new_model()
    space = m.new_space()
    space.parameters = ('x', )
    space[1]    # create an itemspace

    assert 1 in space.itemspaces
    space.new_space('SpaceA')

    assert not space.itemspaces     # must be empty
    assert 'SpaceA' in dir(space)   # must have SpaceA in its namespace




