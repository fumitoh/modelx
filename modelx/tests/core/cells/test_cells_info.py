import modelx as mx
import pytest


@pytest.fixture
def testmodel():
    m = mx.new_model('Model1')
    s = m.new_space('Space1', formula=lambda i: None)

    def foo(t, i=0):
        if t == 0:
            return i
        return foo(t - 1, i) + 1

    s.new_cells('foo', formula=foo)

    yield m
    m._impl._check_sanity()
    m.close()


def test_info_type_name(testmodel):
    m = testmodel
    info = m.Space1.foo.info
    assert type(info).__name__ == 'CellsInfo'


def test_info_header_includes_signature_with_defaults(testmodel):
    m = testmodel
    # Trigger one ItemSpace creation so that the [1] form is reachable
    text = repr(m.Space1[1].foo.info)
    first = text.splitlines()[0]
    assert first.startswith('<CellsInfo ')
    assert 'Model1.Space1[1].foo(t, i=0)' in first


def test_info_shows_is_cached_and_allow_none(testmodel):
    m = testmodel
    cells = m.Space1.foo
    text = repr(cells.info)
    assert 'is_cached: True' in text
    assert 'allow_none: None' in text

    cells.is_cached = False
    cells.allow_none = True
    text2 = repr(cells.info)
    assert 'is_cached: False' in text2
    assert 'allow_none: True' in text2


def test_info_shows_formula_source(testmodel):
    m = testmodel
    text = repr(m.Space1.foo.info)
    assert 'formula:' in text
    assert 'def foo(t, i=0):' in text
    assert 'return foo(t - 1, i) + 1' in text


def test_info_cached_value_count_and_listing(testmodel):
    m = testmodel
    m.Space1[1].foo(2)
    text = repr(m.Space1[1].foo.info)
    assert 'cached values: 3' in text
    assert '(0, 0): 0' in text
    assert '(1, 0): 1' in text
    assert '(2, 0): 2' in text


def test_info_abbreviates_many_cached_values(testmodel):
    m = testmodel
    cells = m.Space1[1].foo
    for t in range(10):
        cells(t)
    text = repr(cells.info)
    assert 'cached values: 10' in text
    assert '... (' in text and 'more)' in text


def test_info_with_scalar_cells():
    m = mx.new_model()
    try:
        s = m.new_space('S')
        s.new_cells('scalar', formula=lambda: 42)
        s.scalar()
        text = repr(s.scalar.info)
        assert 'scalar()' in text
        assert 'cached values: 1' in text
        assert '(): 42' in text
    finally:
        m._impl._check_sanity()
        m.close()
