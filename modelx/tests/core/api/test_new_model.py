import modelx as mx


def test_new_model_autorename():
    name = "ModelForBackupTest"
    m = mx.new_model(name)
    m2 = mx.new_model(name)
    l = len(name)
    assert m.name[l:l+4] == "_BAK"
    m3 = mx.new_model(name)
    assert m.name[l:l+4] == "_BAK"
    assert m2.name[l:l+4] == "_BAK"
    m.close()
    m2.close()
    m3.close()
