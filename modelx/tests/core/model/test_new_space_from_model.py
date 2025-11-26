import pytest
import modelx as mx
import pandas as pd


@pytest.fixture
def create_delete_model():
    """Fixture that tracks and closes all models created during a test."""
    created_models = []
    
    def _create_model(name):
        m = mx.new_model(name)
        created_models.append(m)
        return m
    
    yield _create_model
    
    # Cleanup: close all models in reverse order
    for m in reversed(created_models):
        m.close()


def test_new_space_from_model_defaults(create_delete_model):
    m1 = create_delete_model('M1')
    m1.x = 42
    S = m1.new_space('S')
    C = S.new_cells('C', formula=lambda: x + 1)

    m2 = create_delete_model('M2')
    T = m2.new_space_from_model(m1)  # default refs_strategy='copy'

    assert hasattr(T, 'S')
    assert T.S.C() == 43
    # refs copied only into container, not m2
    assert 'x' not in m2.refs

def test_new_space_from_model_with_prefix(create_delete_model):
    m1 = create_delete_model('M1')
    m1.x = 1
    S = m1.new_space('S')
    C = S.new_cells('C', formula=lambda: x + 1)

    m2 = create_delete_model('M2')
    T = m2.new_space_from_model(m1, refs_prefix='m1_')

    assert 'm1_x' in T.refs
    # The formula uses 'x' name; since we prefixed, ensure the symbol resolves within T via its own refs
    # We expect failure if not properly seeded; but copy_space copies own refs of each space too.
    assert T.S.C() == 2

def test_new_space_from_model_ignore_refs(create_delete_model):
    m1 = create_delete_model('M1')
    m1.k = 10
    S = m1.new_space('S')
    C = S.new_cells('C', formula=lambda: k)

    m2 = create_delete_model('M2')
    m2.k = 99
    T = m2.new_space_from_model(m1, refs_strategy='ignore')

    assert T.S.C() == 99

def test_new_space_from_model_cross_references(create_delete_model):
    m1 = create_delete_model('X1')
    S1 = m1.new_space('S1')
    S2 = m1.new_space('S2')

    # Two cells referencing each other through explicit space names (no cycles)
    S1.S2 = S2
    S2.S1 = S1
    S1.new_cells('a', formula=lambda: S2.b())
    S2.new_cells('b', formula=lambda: 40 + 2)

    m2 = create_delete_model('X2')
    T = m2.new_space_from_model(m1)
    assert T.S1.a() == 42
    assert T.S2.b() == 42

def test_new_space_from_model_with_pandas_refs(create_delete_model, tmp_path):
    m1 = create_delete_model('P1')
    S = m1.new_space('Data')

    df = pd.DataFrame({'k':[1,2,3],'v':[10,20,30]})
    # Save via pandas io to a csv so it's attached through IO manager
    csv_path = tmp_path / 'data.csv'
    # Use space-level new_pandas to attach IO
    S.new_pandas('table', str(csv_path), df, file_type='csv', sheet=None)

    # Also add a cell that uses this reference
    S.new_cells('total', formula=lambda: int(table['v'].sum()))

    m2 = create_delete_model('P2')
    T = m2.new_space_from_model(m1)  # copy strategy should preserve refs binding
    assert T.Data.total() == 60

def test_new_space_from_model_dynamic_spaces(create_delete_model):
    m1 = create_delete_model('DYN1')
    Root = m1.new_space('Root')

    # Make a dynamic space family Root.Item[i] that sums i with a global ref k
    m1.k = 5
    Item = Root.new_space('Item', formula=lambda i: {})
    Item.new_cells('val', formula=lambda i: i + k)

    m2 = create_delete_model('DYN2')
    T = m2.new_space_from_model(m1)
    # Instantiate a couple of items and ensure refs are available
    assert T.Root.Item[10].val(10) == 15
    assert T.Root.Item[2].val(2) == 7
