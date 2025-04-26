import pathlib
import pytest
from modelx.serialize import deserializer
from modelx.serialize.serializer_6 import SourceStructure
from modelx.serialize.ziputil import read_str_utf8
import asttokens


def get_statmetns_atok(path):
    txt = pathlib.Path(path).read_text(encoding='utf-8')
    atok = asttokens.ASTTokens(txt, parse=True)
    return list(atok.get_text(stmt) for stmt in atok.tree.body)


@pytest.mark.parametrize("libs", ["libraries", "projects"])
def test_compare_statements_agains_asttokens_using_lifelib(libs):
    import lifelib

    lib_dir = pathlib.Path(lifelib.__file__).parent / libs
    file_count = 0

    for path_ in lib_dir.rglob('__init__.py'):
        print(path_)
        srcstruct = SourceStructure(read_str_utf8(path_))
        file_count += 1
        for t, a in zip(deserializer.get_statement_tokens(path_), get_statmetns_atok(path_)):
            assert t.str_ == a
            assert srcstruct.get_section(t.lineno[0]) == t.section

    assert file_count > 30
