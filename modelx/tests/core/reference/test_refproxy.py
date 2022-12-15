import modelx as mx


def test_baseattrs():

    m = mx.new_model()
    s = m.new_space()
    s.bar = 1
    attrs = mx.get_object(s.fullname + "." + "bar", as_proxy=True)._baseattrs

    assert attrs["name"] == "bar"
    assert attrs["fullname"] == s.fullname + "." + "bar"
    assert attrs["repr"] == "bar"
    assert attrs["namedid"] == s.name + ".bar"

    m._impl._check_sanity()
    m.close()