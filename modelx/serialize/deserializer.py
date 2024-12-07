import tokenize
import pathlib
from collections import namedtuple

from modelx.serialize.ziputil import FileForTokenizer

Section = namedtuple("Section", ["id", "symbol"])
SECTION_DIVIDER = "# " + "-" * 75
SECTIONS = {
    "DEFAULT": Section("DEFAULT", ""),
    "CELLSDEFS": Section("CELLSDEFS", "# Cells"),
    "REFDEFS": Section("REFDEFS", "# References")
}


class SourceStructure:

    def __init__(self, source: str):
        self.source = source
        self.sections = None
        self.construct()

    def construct(self):
        self.sections = {}
        sec = "DEFAULT"
        is_divider_read = False
        for i, line in enumerate(self.source.split("\n")):
            if is_divider_read:
                sec = next(
                    (sec.id for sec in SECTIONS.values()
                     if line.strip() == sec.symbol),
                    "DEFAULT")
                is_divider_read = False
                self.sections[i] = sec
            else:
                if line.strip() == SECTION_DIVIDER:
                    is_divider_read = True

    def get_section(self, lineno):
        sections = list(self.sections.keys())
        secno = next((i for i in reversed(sections) if lineno > i), 0)
        return self.sections[secno] if secno else "DEFAULT"


class StatementTokens(list):

    def __init__(self, tokens, section):
        super().__init__(tokens)
        self.section = section
        self._cached_str = None

    @property
    def lineno(self):
        return (self[0].start[0], self[-1].start[0])

    @property
    def str_(self):
        if self._cached_str is not None:
            return self._cached_str

        result = ""
        prev_line = 0
        last_line = self[-1].end[0]
        for t in self[:-1]:
            if prev_line < t.start[0]:
                if t.end[0] < last_line:
                    result += t.line
                else:
                    break

            prev_line = t.end[0]

        t = self[-1]

        # Get the length of the last new line.
        trim_len = len(t.line.splitlines(keepends=True)[-1]) - t.end[1]
        if trim_len > 0:
            result += t.line[:-trim_len]
        else:
            result += t.line

        self._cached_str = result
        return result


class ReadLine:

    Sections = list(SECTIONS.keys())

    def __init__(self, file):
        self.file = file
        self.cur_sec_idx = 0
        self.prev_sec_idx = 0
        self.is_separator_line = False

    def __call__(self):
        line = self.file.readline()
        if line.strip() == SECTION_DIVIDER:
            self.is_separator_line = True
        elif self.is_separator_line:
            while True:
                self.prev_sec_idx = self.cur_sec_idx
                self.cur_sec_idx += 1
                if line.strip() == SECTIONS[self.Sections[self.cur_sec_idx]].symbol:
                    break
            self.is_separator_line = False
        return line

    @property
    def cur_sec(self):
        return self.Sections[self.cur_sec_idx]

    @property
    def prev_sec(self):
        return self.Sections[self.prev_sec_idx]

def get_statement_tokens(path):

    result = []
    indent_level = 0
    cur_stmt = StatementTokens([], ReadLine.Sections[0])

    path = path if isinstance(path, pathlib.PurePath) else pathlib.Path(path)

    with FileForTokenizer(path) as f:
        readline = ReadLine(f)

        for token in tokenize.generate_tokens(readline):

            token_type, token_str, (start_line, start_col), _, _ = token

            if token_type == tokenize.INDENT:
                if indent_level == 0:
                    # assert not current_stmt
                    popped = result.pop()
                    popped.extend(cur_stmt)
                    popped.section = readline.cur_sec
                    cur_stmt = popped
                indent_level += 1
                # current_stmt.append(token)
            elif token_type == tokenize.DEDENT:
                indent_level -= 1
                if indent_level == 0:
                    # DEDENT comes after NL and COMMENT
                    # Remove last NL and COMMENT before DEDENT
                    while cur_stmt[-1].type in (tokenize.NL, tokenize.COMMENT):
                        tk = cur_stmt.pop()
                        if tk.line.strip() == SECTION_DIVIDER:
                            cur_stmt.section = readline.prev_sec
                    result.append(cur_stmt)
                    cur_stmt = StatementTokens([], readline.cur_sec)
            elif token_type == tokenize.NEWLINE:
                if indent_level == 0:
                    while cur_stmt[0].type in (tokenize.NL, tokenize.COMMENT):
                        cur_stmt.pop(0)

                    result.append(cur_stmt)
                    cur_stmt = StatementTokens([], readline.cur_sec)
            elif token_type in (tokenize.ENDMARKER,):
                pass
            else:
                cur_stmt.append(token)
                cur_stmt.section = readline.cur_sec

    return result


def get_statements(path):
    return list(tokens.str_ for tokens in get_statement_tokens(path))


def get_tokens(path):
    result = []
    with open(path) as f:
        for token in tokenize.generate_tokens(f.readline):
            result.append(token)
    return result


if __name__ == "__main__":
    stmts = get_statement_tokens('__init__.py')
    for stmt in stmts:
        print(stmt.section, stmt[0].start[0], stmt[0].line.rstrip())