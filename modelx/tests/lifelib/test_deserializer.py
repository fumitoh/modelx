import pathlib
import tokenize
from modelx.serialize import deserializer
from modelx.serialize.serializer_6 import SourceStructure
from modelx.serialize.ziputil import read_str_utf8
import asttokens


def get_statmetns_atok(path):
    txt = pathlib.Path(path).read_text(encoding='utf-8')
    atok = asttokens.ASTTokens(txt, parse=True)
    return list(atok.get_text(stmt) for stmt in atok.tree.body)


def test_compare_statements_agains_asttokens_using_lifelib():
    import lifelib

    lib_dir = pathlib.Path(lifelib.__file__).parent / 'libraries'
    file_count = 0

    for path_ in lib_dir.rglob('__init__.py'):
        print(path_)
        srcstruct = SourceStructure(read_str_utf8(path_))
        file_count += 1
        statements = deserializer.get_statement_tokens(path_)
        ast_statements = get_statmetns_atok(path_)
        assert len(statements) == len(ast_statements)
        for t, a in zip(statements, ast_statements):
            # ASTTokens ends at the last code token. The deserializer also
            # captures trailing comments, including serializer-7 IOSpec metadata.
            if t[-1].type == tokenize.COMMENT:
                t = deserializer.StatementTokens(t[:-1], t.section)
            assert t.str_ == a
            assert srcstruct.get_section(t.lineno[0]) == t.section

    assert file_count > 30
