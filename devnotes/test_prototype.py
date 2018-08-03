import pytest
from prototype import *

@pytest.mark.parametrize("new_member",
                         ['item', 'space'])
def test_add_remove_base_lv2ly2(new_member):
    """
    Pattern #1: 2 levels, 2 layers

    C:Item, Space

        A   B
            |
            C

    A.add_base(B) # Automatic child addition

        A <-B
        |   |
        C*  C

    A.remove_base(B) # Automatic child removal

        A   B
            |
            C
    """
    model = MiniModel()
    A = model.new_space('A')
    B = model.new_space('B')
    C = B.new_member(new_member, 'C')

    for _ in range(2):
        A.add_base(B)
        assert 'C' in A.children
        A.remove_base(B)
        assert 'C' in B.children
        assert 'C' not in A.children


@pytest.mark.parametrize("new_member",
                         ['item', 'space'])
def test_new_del_basemember_lv2ly2(new_member):
    """
        A <-B

    A.add_base(B) # Automatic child addition (repetetive)

        A <-B
        |   |
        C*  C

    B.del_[item, space](C) # Automatic child deletion

        A <-B
    """
    model = MiniModel()
    A = model.new_space('A')
    B = model.new_space('B')
    A.add_base(B)

    for _ in range(2):
        C = B.new_member(new_member, 'C')
        assert 'C' in B.children
        assert 'C' in A.children
        B.del_member(new_member, 'C')
        assert 'C' not in B.children
        assert 'C' not in A.children


@pytest.mark.parametrize("new_descents", [True, False])
def test_add_remove_base_lv4ly2(new_descents):
    """
    A <--B
    |    |
    C(*) C
    |    |
    D(*) D
    |    |
    E*   E
    """
    model = MiniModel()
    B = model.new_space('B')
    E = B.new_space('C').new_space('D').new_space('E')
    A = model.new_space('A')
    if new_descents:
        D = A.new_space('C').new_space('D')
    A.add_base(B)
    assert 'E' in A.spaces['C'].spaces['D'].spaces
    A.remove_base(B)
    if new_descents:
        assert 'E' not in A.spaces['C'].spaces['D'].spaces
    else:
        assert 'C' not in A.spaces


@pytest.mark.parametrize("new_descents", [True, False])
def test_new_del_basemember_lv4ly2(new_descents):
    """
    A <--B
    |    |
    C(*) C
    |    |
    D(*) D
    |    |
    E*   E
    """
    model = MiniModel()
    B = model.new_space('B')
    E = B.new_space('C').new_space('D').new_space('E')
    A = model.new_space('A')
    if new_descents:
        D = A.new_space('C').new_space('D')
    A.add_base(B)
    assert 'E' in A.spaces['C'].spaces['D'].spaces
    B.spaces['C'].spaces['D'].del_member('space', 'E')
    assert 'E' not in A.spaces['C'].spaces['D'].spaces


@pytest.mark.parametrize("new_member", ['item', 'space'])
def test_add_remove_base(new_member):
    """
        A   B   C
                |
                D
                |
                E

    B.add_base(C) # Automatic child addition (repetetive)

        A   B <-C
            |   |
            D*  D
            |   |
            E*  E

    A.add_base(B) # Automatic child addition (repetetive)

        A <-B <-C
        |   |   |
        D*  D*  D
        |   |   |
        E*  E*  E
    """
    model = MiniModel()
    A = model.new_space('A')
    B = model.new_space('B')
    C = model.new_space('C')
    C.new_space('D').new_member(new_member, 'E')

    for _ in repr(2):

        B.add_base(C)
        assert 'D' in B.spaces
        assert 'E' in getattr(B.spaces['D'], new_member + 's')

        A.add_base(B)
        assert 'D' in A.spaces
        assert 'E' in getattr(A.spaces['D'], new_member + 's')

        A.remove_base(B)
        B.remove_base(C)
        assert not 'D' in A.spaces
        assert not 'D' in B.spaces


@pytest.mark.parametrize("new_member",
                         ['item', 'space'])
def test_new_del_basemember_lv3ly3(new_member):

    """
        A <-B <-C

        A <-B <-C
        |   |   |
        D*  D*  D        

    A.add_base(B) # Automatic child addition (repetetive)

        A <-B <-C
        |   |   |
        D*  D*  D
        |   |   |
        E*  E*  E

    B.del_[item, space](C) # Automatic child deletion

        A <-B <-C
        |   |   |
        D*  D*  D

        A <-B <-C
    """
    model = MiniModel()
    A = model.new_space('A')
    B = model.new_space('B')
    C = model.new_space('C')
    A.add_base(B)
    B.add_base(C)

    for _ in range(2):
        D = C.new_space('D')
        assert 'D' in B.children
        assert 'D' in A.children
        E = D.new_member(new_member, 'E')
        assert 'E' in getattr(B.spaces['D'], new_member + 's')
        assert 'E' in getattr(A.spaces['D'], new_member + 's')
        D.del_member(new_member, 'E')
        assert 'E' not in getattr(B.spaces['D'], new_member + 's')
        assert 'E' not in getattr(A.spaces['D'], new_member + 's')
        C.del_space('D')
        assert 'D' not in B.spaces
        assert 'D' not in A.spaces


@pytest.mark.parametrize("new_member",
                         ['item', 'space'])
def test_new_del_basemember_lv32ly3(new_member):
    """
       G <-F   C <-A
       |   |   |   |
       D*  D <-B   B
       |   |   |   |
       E*  E*  E*  E
    """
    model = MiniModel()
    A = model.new_space('A')
    AB = A.new_space('B')
    C = model.new_space('C')
    CB = C.new_space('B')
    F = model.new_space('F')
    D = F.new_space('D')
    D.add_base(CB)
    C.add_base(A)
    G = model.new_space('G')
    G.add_base(F)

    for _ in range(2):
        AB.new_member(new_member, 'E')
        assert 'E' in getattr(CB, new_member + 's')
        assert 'E' in getattr(D, new_member + 's')
        assert 'E' in getattr(G.spaces['D'], new_member + 's')
        AB.del_member(new_member, 'E')
        assert 'E' not in getattr(CB, new_member + 's')
        assert 'E' not in getattr(D, new_member + 's')
        assert 'E' not in getattr(G.spaces['D'], new_member + 's')


def test_base_parent_child():
    """
        C <-----+
          <-B   |
             \  A
              \ |
                D
    """
    model = MiniModel()
    A = model.new_space('A')
    D = A.new_space('D')
    B = model.new_space('B')
    C = model.new_space('C')
    C.add_base(B)
    C.add_base(A)
    B.add_base(D)
    assert C.bases == [B, D, A]


def test_sub_parent_child():
    """
        A <-B <-C
        |       |
        D <-----+
    """
    model = MiniModel()
    A = model.new_space('A')
    D = A.new_space('D')
    B = model.new_space('B')
    C = model.new_space('C')
    A.add_base(B)
    B.add_base(C)
    D.add_base(C)
    assert D.bases == [C]


def test_pararell_inheritance():
    """
        A <-B
        |   |
        C <-D
    """
    model = MiniModel()
    A = model.new_space('A')
    B = model.new_space('B')
    C = A.new_space('C')
    D = B.new_space('D')
    A.add_base(B)
    C.add_base(D)
    assert 'C' in A.spaces
    assert 'D' in A.spaces

def test_circler_error():
    """
        A <-B
        |   |
        C ->D
    """
    model = MiniModel()
    A = model.new_space('A')
    B = model.new_space('B')
    C = A.new_space('C')
    D = B.new_space('D')

    D.add_base(C)

    with pytest.raises(ValueError):
        A.add_base(B)


def test_circler_nonerror():
    """
            C
            |-+
        A <-D |
        |     |
        B --->E

    """

    model = MiniModel()
    A = model.new_space('A')
    B = A.new_space('B')
    C = model.new_space('C')
    D = C.new_space('D')
    E = C.new_space('E')

    A.add_base(D)
    E.add_base(B)

    assert A.bases == [D]
    assert E.bases == [B]