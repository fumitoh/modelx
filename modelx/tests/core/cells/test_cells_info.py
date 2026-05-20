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


def test_info_header_uses_class_name_and_signature(testmodel):
    m = testmodel
    first = repr(m.Space1[1].foo.info).splitlines()[0]
    assert first == 'Cells: Model1.Space1[1].foo(t, i=0)'


def test_info_shows_is_derived(testmodel):
    m = testmodel
    text = repr(m.Space1.foo.info)
    lines = text.splitlines()
    # is_derived appears as the second item (right after the header)
    assert lines[1] == 'is_derived: False'

    # Build a derived cells via space inheritance
    derived = m.new_space('Derived', bases=m.Space1)
    text2 = repr(derived.foo.info)
    lines2 = text2.splitlines()
    assert lines2[1] == 'is_derived: True'


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


def test_info_shows_full_formula_source(testmodel):
    m = testmodel
    text = repr(m.Space1.foo.info)
    assert 'formula:' in text
    assert 'def foo(t, i=0):' in text
    assert 'if t == 0:' in text
    assert 'return i' in text
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
    # Abbreviation marker present
    assert text.splitlines()[-1].strip() == '...'


def test_info_omits_input_values_when_none(testmodel):
    m = testmodel
    m.Space1.foo(0)
    text = repr(m.Space1.foo.info)
    assert 'input values' not in text


def test_info_shows_input_values_when_present(testmodel):
    m = testmodel
    cells = m.Space1.foo
    cells[10] = 100
    cells[20] = 200
    text = repr(cells.info)
    assert 'input values: 2' in text
    assert '(10, 0): 100' in text
    assert '(20, 0): 200' in text


def test_info_separates_cached_from_input_counts(testmodel):
    m = testmodel
    cells = m.Space1.foo
    cells(0)
    cells(1)
    cells[10] = 100
    text = repr(cells.info)
    # Two computed entries (0,) and (1,), one input (10,)
    assert 'cached values: 2' in text
    assert 'input values: 1' in text


def test_info_with_scalar_cells():
    m = mx.new_model()
    try:
        s = m.new_space('S')
        s.new_cells('scalar', formula=lambda: 42)
        s.scalar()
        text = repr(s.scalar.info)
        first = text.splitlines()[0]
        assert first.endswith('S.scalar()')
        assert first.startswith('Cells: ')
        assert 'cached values: 1' in text
        # Scalar cells keep the empty-tuple key (no single argument to unwrap)
        assert '(): 42' in text
    finally:
        m._impl._check_sanity()
        m.close()


def test_info_unwraps_single_arg_keys():
    m = mx.new_model()
    try:
        s = m.new_space('S')
        s.new_cells('bar', formula=lambda x: x * 2)
        s.bar(3)
        s.bar(5)
        s.bar[10] = 100
        text = repr(s.bar.info)
        # Single-argument keys are shown without the (,) tuple form
        assert '3: 6' in text
        assert '5: 10' in text
        assert '10: 100' in text
        assert '(3,)' not in text
        assert '(5,)' not in text
        assert '(10,)' not in text
    finally:
        m._impl._check_sanity()
        m.close()
