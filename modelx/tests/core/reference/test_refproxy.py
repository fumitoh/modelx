import modelx as mx


def test_baseattrs():

    s = mx.new_space()
    s.bar = 1
    attrs = mx.get_object(s.fullname + "." + "bar", as_proxy=True)._baseattrs

    assert attrs["name"] == "bar"
    assert attrs["fullname"] == s.fullname + "." + "bar"
    assert attrs["repr"] == "bar"
    assert attrs["namedid"] == s.name + ".bar"
