
import modelx as mx

def test_embed_defaults():
    m1 = mx.new_model('M1')
    m1.x = 42
    S = m1.new_space('S')
    C = S.new_cells('C', formula=lambda: x + 1)

    m2 = mx.new_model('M2')
    T = m2.new_space_from_model(m1)  # default refs_strategy='copy'

    assert hasattr(T, 'S')
    assert T.S.C() == 43
    # refs copied only into container, not m2
    assert 'x' not in m2.refs

def test_embed_with_prefix():
    m1 = mx.new_model('M1')
    m1.x = 1
    S = m1.new_space('S')
    C = S.new_cells('C', formula=lambda: x + 1)

    m2 = mx.new_model('M2')
    T = m2.new_space_from_model(m1, refs_prefix='m1_')

    assert 'm1_x' in T.refs
    # The formula uses 'x' name; since we prefixed, ensure the symbol resolves within T via its own refs
    # We expect failure if not properly seeded; but copy_space copies own refs of each space too.
    assert T.S.C() == 2

def test_embed_ignore_refs():
    m1 = mx.new_model('M1')
    m1.k = 10
    S = m1.new_space('S')
    C = S.new_cells('C', formula=lambda: k)

    m2 = mx.new_model('M2')
    m2.k = 99
    T = m2.new_space_from_model(m1, refs_strategy='ignore')

    assert T.S.C() == 99
