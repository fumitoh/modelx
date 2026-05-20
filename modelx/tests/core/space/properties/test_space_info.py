import modelx as mx
import pytest


@pytest.fixture
def testmodel():
    m = mx.new_model('Model1')
    parent = m.new_space('Space1', formula=lambda i: None)
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
    assert first == '<SpaceInfo Model1.Space1>'


def test_info_header_for_item_space(testmodel):
    m = testmodel
    first = repr(m.Space1[1].info).splitlines()[0]
    assert first == '<SpaceInfo Model1.Space1[1]>'


def test_info_parameters_shown_when_present(testmodel):
    m = testmodel
    text = repr(m.Space1.info)
    assert "parameters: ('i',)" in text


def test_info_parameters_omitted_when_absent(testmodel):
    m = testmodel
    text = repr(m.Space1.Child.info)
    assert 'parameters:' not in text


def test_info_itemspaces_count_and_listing(testmodel):
    m = testmodel
    text = repr(m.Space1.info)
    assert 'itemspaces: 2' in text
    assert '1: <ItemSpace Model1.Space1[1]>' in text
    assert '2: <ItemSpace Model1.Space1[2]>' in text


def test_info_itemspaces_empty(testmodel):
    m = testmodel
    text = repr(m.Space1.Child.info)
    assert 'itemspaces: 0' in text


def test_info_abbreviates_many_itemspaces():
    m = mx.new_model()
    try:
        s = m.new_space('S', formula=lambda x: None)
        for i in range(10):
            s[i]
        text = repr(s.info)
        assert 'itemspaces: 10' in text
        assert '... (' in text and 'more)' in text
    finally:
        m._impl._check_sanity()
        m.close()
