import modelx as mx


def test_clear_all():
    """Fix error during clear_all raised from ReferenceGraph
    https://github.com/fumitoh/modelx/issues/127
    """
    m = mx.new_model()
    s1 = m.new_space("Space1")
    s2 = s1.new_space("Space2")

    @mx.defcells(space=s1)
    def cells1(t):
        return Space2.x

    @mx.defcells(space=s1)
    def cells2(t):
        return cells1(t) + Space2.x

    s2.x = 1

    cells1(10)
    cells2(10)
    m.clear_all()
    m.close()