import pytest
from modelx.managers.component import ComponentManager, ComponentError
from modelx.managers.dummy import DummyModel, DummySpace, DummyCells, DummyRef

# mock_manager = manager.get_mock_manager()


@pytest.fixture
def sample_manager(request):
    manager = ComponentManager()
    model = DummyModel('model', manager)
    manager.set_root(model)
    if request.param == "manager":
        return manager
    else:
        return manager.get_mock_manager()


@pytest.mark.parametrize("sample_manager", ["manager", "mock_manager"], indirect=True)
def test_base_branch_operations(sample_manager):
    """Test basic component operations

    Model Structure:
        A -> B
        |
        +--c1
        +--r1

    Operations:
        - Create Space A and B
        - Add A -> B
        - Create c1 and r1 in A
        - Remove A -> B
        - Add A -> B

    """
    # A <- B
    mgr = sample_manager
    model = mgr.root

    A = mgr._create_branch(model, 'A', DummySpace)
    B = mgr._create_branch(model, 'B', DummySpace)

    assert list(model.get_branches()) == [A, B]

    mgr._add_base(B, A)
    c1 = mgr._create_leaf(A, 'c1', DummyCells)
    r1 = mgr._create_leaf(A, 'r1', DummyRef)

    assert list(A.get_leaves()) == [c1, r1]

    c1_B = B.get_child('c1')
    r1_B = B.get_child('r1')

    assert list(B.get_leaves()) == [c1_B, r1_B]

    assert c1_B.name == 'c1' and c1_B.base == c1
    assert r1_B.name == 'r1' and r1_B.base == r1

    mgr._remove_base(B, A)
    assert list(B.get_leaves()) == []

    mgr._add_base(B, A)
    assert list(B.get_leaves()) == [c1_B, r1_B]

    assert c1_B.name == 'c1' and c1_B.base == c1
    assert r1_B.name == 'r1' and r1_B.base == r1

    mgr._delete_leaf(A, 'c1')

    assert list(A.get_leaves()) == [r1]
    assert list(B.get_leaves()) == [r1_B]


@pytest.mark.parametrize("sample_manager", ["manager", "mock_manager"], indirect=True)
def test_replaced_derived_leaf_from_binary_base(sample_manager):
    """
    Model Structure:
        A1 -> B -> C -> D
        A2 ->
        |
        +--c1

    """
    mgr = sample_manager
    model = mgr.root

    A1 = mgr._create_branch(model, 'A1', DummySpace)
    A2 = mgr._create_branch(model, 'A2', DummySpace)
    B = mgr._create_branch(model, 'B', DummySpace)
    C = mgr._create_branch(model, 'C', DummySpace)
    D = mgr._create_branch(model, 'D', DummySpace)

    mgr._add_base(B, A1)
    mgr._add_base(B, A2)
    mgr._add_base(C, B)
    mgr._add_base(D, C)

    c_A1 = mgr._create_leaf(A1, 'c1', DummyCells)
    c_A2 = mgr._create_leaf(A2, 'c1', DummyCells)

    assert B.get_child('c1').base is c_A1
    assert C.get_child('c1').base is c_A1
    assert D.get_child('c1').base is c_A1

    mgr._remove_base(B, A1)
    assert B.get_child('c1').base is c_A2
    assert C.get_child('c1').base is c_A2
    assert D.get_child('c1').base is c_A2


@pytest.mark.parametrize("sample_manager, type_, name",
                         [("mock_manager", DummyCells, 'r1'),
                          ("mock_manager", DummyRef, 'c1'),
                          ("mock_manager", DummyCells, 'S1'),
                          ("mock_manager", DummyRef, 'S1'),
                          ("mock_manager", DummyCells, 'r2'),
                          ("mock_manager", DummyRef, 'c2'),
                          ("mock_manager", DummyCells, 'S2'),
                          ("mock_manager", DummyRef, 'S2'),
                          ], indirect=["sample_manager"])
def test_error_on_creating_conflicting_leaf_name_in_base(sample_manager, type_, name):
    """
    Model Structure:
        A -> B ---> C
            |       |
            +--S1   +--S2
            +--c1   +--c2
            +--r1   +--r2
    """
    mgr = sample_manager
    model = mgr.root

    A = mgr._create_branch(model, 'A', DummySpace)
    B = mgr._create_branch(model, 'B', DummySpace)
    C = mgr._create_branch(model, 'C', DummySpace)
    S1 = mgr._create_branch(B, 'S1', DummySpace)
    S2 = mgr._create_branch(C, 'S2', DummySpace)

    mgr._add_base(B, A)
    mgr._add_base(C, B)
    c1_B = mgr._create_leaf(B, 'c1', DummyCells)
    c2_C = mgr._create_leaf(C, 'c2', DummyCells)
    r1_B = mgr._create_leaf(B, 'r1', DummyRef)
    r2_C = mgr._create_leaf(C, 'r2', DummyRef)

    with pytest.raises(ComponentError):
        mgr._create_leaf(A, name, type_)