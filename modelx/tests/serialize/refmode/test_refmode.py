import pandas as pd
import pytest

import modelx as mx
from modelx.tests.testdata.testpkg import testmod


def test_serialize_refmode(tmp_path):
    """
        m---A---RefDynCells --(abs)-->B[1, 2].foo
          |   +-RefSpace --(rel)-->B
          |   +-RefCells --(auto)-->B.foo
          |
          +-B[x, y]---foo
    """
    m = mx.new_model()
    A = mx.new_space('A')
    B = mx.new_space('B')
    B.parameters = ('x', 'y')

    @mx.defcells
    def foo(x):
        return x

    A.absref(RefDynCells=B[1, 2].foo)
    A.relref(RefSpace=B)
    A.RefCells = B.foo

    m.write(tmp_path / 'refpickle')
    m2 = mx.read_model(tmp_path / 'refpickle')

    assert m2.A.RefSpace is m2.B
    assert m2.A.RefDynCells is m2.B[1, 2].foo
    assert m2.A.RefCells is m2.B.foo

    assert m2.A._get_object('RefSpace', as_proxy=True).refmode == "relative"
    assert m2.A._get_object('RefDynCells', as_proxy=True).refmode == "absolute"
    assert m2.A._get_object('RefCells', as_proxy=True).refmode == "auto"


# UserSpace.set_ref refuses a refmode outside ReferenceProxy._refmodes from
# 0.34 (F2), but not while a model is read: the readers call set_ref with
# what the model file holds.

@pytest.mark.parametrize("version", [6, 7])
def test_read_iospec_refs_of_a_space(tmp_path, close_new_models, version):
    """Serializer versions 4-7 write a Reference whose value is an IOSpec's
    as a 3-tuple, ("IOSpec", value id, spec id), and their readers pass its
    third element to set_ref as the refmode: an int.  Six lifelib models
    hold such References (BasicTermASL_ME, BasicTerm_SC, ifrs17sim,
    nestedlife, solvency2, BasicTerm_ME_for_Cluster), and with set_ref's
    check applied to the reader none of them read."""
    m = mx.new_model("IOSpecRefs")
    s = m.new_space("S")
    s.new_pandas("df", "files/df.csv", pd.DataFrame({"a": [1, 2]}),
                 file_type="csv")
    s.new_module("mod", "files/mod", testmod)
    s.new_cells("total", formula="lambda: df['a'].sum()")
    mx.write_model(m, tmp_path / "model", version=version)
    m.close()

    m2 = mx.read_model(tmp_path / "model")
    assert list(m2.S.df["a"]) == [1, 2]
    assert m2.S.mod.modfibo(10) == 55
    assert m2.S.total() == 3
    m2._impl._check_sanity()


@pytest.mark.parametrize("version", [6, 8])
@pytest.mark.parametrize("mode", ["sideways", "None", "42"])
def test_read_a_mode_set_ref_took_before_034(
        tmp_path, close_new_models, version, mode):
    """modelx 0.33 stored any refmode that set_ref was given and wrote it,
    as a str, into the Reference's tuple, ("Interface", (".", "foo"), mode),
    and its read_model reads it back.  Such a model still reads.  The file
    is written by this version with "auto" and then edited, as 0.33 would
    have written it."""
    m = mx.new_model("SavedMode")
    s = m.new_space("S")
    s.new_cells("foo", formula="lambda: 1")
    s.new_cells("usei", formula="lambda: ri()")
    s.set_ref("ri", s.foo, "auto")
    mx.write_model(m, tmp_path / "model", version=version)
    m.close()

    path = tmp_path / "model" / "S" / "__init__.py"
    src = path.read_text(encoding="utf-8")
    line = 'ri = ("Interface", (".", "foo"), "auto")'
    assert src.count(line) == 1
    path.write_text(src.replace(line, line.replace('"auto"', '"%s"' % mode)),
                    encoding="utf-8")

    m2 = mx.read_model(tmp_path / "model")
    assert m2.S.ri is m2.S.foo
    assert m2.S.usei() == 1
    m2._impl._check_sanity()
