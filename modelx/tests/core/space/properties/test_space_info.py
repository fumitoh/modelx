import modelx as mx
import pytest


@pytest.fixture
def testmodel():
    m = mx.new_model('Model1')
    parent = m.new_space('Space1', formula=lambda i, j=0: None)
    parent.new_space('Child')
    parent[1]
    parent[2]
    yield m
    m._impl._check_sanity()
    m.close()


def test_info_type_name(testmodel):
    m = testmodel
    info = m.Space1.info
    assert type(info).__name__ == 'SpaceInfo'


def test_info_header_for_user_space(testmodel):
    m = testmodel
    first = repr(m.Space1.info).splitlines()[0]
    assert first == 'UserSpace: Model1.Space1'


def test_info_header_for_item_space(testmodel):
    m = testmodel
    first = repr(m.Space1[1].info).splitlines()[0]
    assert first == 'ItemSpace: Model1.Space1[1, 0]'


def test_info_shows_bases(testmodel):
    m = testmodel
    # The base UserSpace has no bases
    lines = repr(m.Space1.Child.info).splitlines()
    assert lines[1] == 'bases: []'

    # A derived space lists base spaces using their dotted fullnames
    derived = m.new_space('Derived', bases=m.Space1)
    lines2 = repr(derived.info).splitlines()
    assert lines2[1] == 'bases: [Model1.Space1]'
    # Plain dotted names, no <UserSpace ...> wrappers
    assert '<UserSpace' not in lines2[1]


def test_info_parameters_format(testmodel):
    m = testmodel
    text = repr(m.Space1.info)
    # Signature string without outer parens, with defaults preserved
    assert 'parameters: i, j=0' in text


def test_info_parameters_omitted_when_no_formula(testmodel):
    m = testmodel
    text = repr(m.Space1.Child.info)
    assert 'parameters:' not in text


def test_info_itemspaces_count(testmodel):
    m = testmodel
    text = repr(m.Space1.info)
    assert 'itemspaces: 2' in text


def test_info_itemspaces_listing_keys_only(testmodel):
    m = testmodel
    lines = repr(m.Space1.info).splitlines()
    # The last line is the bracketed key list
    last = lines[-1].strip()
    assert last.startswith('[') and last.endswith(']')
    # Only keys are shown - no ItemSpace repr leaks in
    assert 'ItemSpace' not in last
    assert '(1, 0)' in last
    assert '(2, 0)' in last


def test_info_itemspaces_empty_no_list(testmodel):
    m = testmodel
    text = repr(m.Space1.Child.info)
    assert 'itemspaces: 0' in text
    # No list line when empty
    for line in text.splitlines():
        assert not line.strip().startswith('[')


def test_info_abbreviates_many_itemspaces():
    m = mx.new_model()
    try:
        s = m.new_space('S', formula=lambda x: None)
        for i in range(10):
            s[i]
        lines = repr(s.info).splitlines()
        last = lines[-1].strip()
        assert last.startswith('[') and last.endswith(']')
        assert last.endswith(', ...]')
    finally:
        m._impl._check_sanity()
        m.close()
