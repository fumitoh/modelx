
import modelx as mx
import pandas as pd

def test_embed_cross_references():
    m1 = mx.new_model('X1')
    S1 = m1.new_space('S1')
    S2 = m1.new_space('S2')

    # Two cells referencing each other through explicit space names (no cycles)
    S1.S2 = S2
    S2.S1 = S1
    S1.new_cells('a', formula=lambda: S2.b())
    S2.new_cells('b', formula=lambda: 40 + 2)

    m2 = mx.new_model('X2')
    T = m2.new_space_from_model(m1)
    assert T.S1.a() == 42
    assert T.S2.b() == 42

def test_embed_with_pandas_refs(tmp_path):
    m1 = mx.new_model('P1')
    S = m1.new_space('Data')

    df = pd.DataFrame({'k':[1,2,3],'v':[10,20,30]})
    # Save via pandas io to a csv so it's attached through IO manager
    csv_path = tmp_path / 'data.csv'
    # Use space-level new_pandas to attach IO
    S.new_pandas('table', str(csv_path), df, file_type='csv', sheet=None)

    # Also add a cell that uses this reference
    S.new_cells('total', formula=lambda: int(table['v'].sum()))

    m2 = mx.new_model('P2')
    T = m2.new_space_from_model(m1)  # copy strategy should preserve refs binding
    assert T.Data.total() == 60

def test_embed_dynamic_spaces():
    m1 = mx.new_model('DYN1')
    Root = m1.new_space('Root')

    # Make a dynamic space family Root.Item[i] that sums i with a global ref k
    m1.k = 5
    Item = Root.new_space('Item', formula=lambda i: {})
    Item.new_cells('val', formula=lambda i: i + k)

    m2 = mx.new_model('DYN2')
    T = m2.new_space_from_model(m1)
    # Instantiate a couple of items and ensure refs are available
    assert T.Root.Item[10].val(10) == 15
    assert T.Root.Item[2].val(2) == 7
