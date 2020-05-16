

def test_set_formula(itemspacetest):

    _, s = itemspacetest

    assert s.itemspaces
    s.formula = lambda i, j, k: None

    assert not s.itemspaces
    for i in range(10):
        assert s[i, i, i].foo(i) == i

    assert len(s.itemspaces) == 10


def test_del_formula(itemspacetest):

    _, s = itemspacetest

    assert s.itemspaces
    del s.formula
    assert not s.formula
    assert not s.itemspaces

