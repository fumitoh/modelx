import re
import string

import openpyxl as opxl


def get_col_index(name):
    """Convert column name to index."""

    index = string.ascii_uppercase.index
    col = 0
    for c in name.upper():
        col = col * 26 + index(c) + 1
    return col


def is_range_address(range_addr):

    # RANGE_EXPR modified from openpyxl.utils.cells
    # see https://bitbucket.org/openpyxl/openpyxl

    RANGE_EXPR = """
    (?P<cells>
    [$]?(?P<min_col>[A-Za-z]{1,3})?
    [$]?(?P<min_row>\d+)?
    (:[$]?(?P<max_col>[A-Za-z]{1,3})?
    [$]?(?P<max_row>\d+)?)?
    )$
    """
    RANGE_EXPR_RE = re.compile(RANGE_EXPR, re.VERBOSE)

    match = RANGE_EXPR_RE.match(range_addr)

    if not match:
        return False
    else:
        cells = match.group("cells")

    if not cells:
        return False
    else:
        min_col = get_col_index(match.group("min_col"))
        min_row = int(match.group("min_row"))

        # if range_addr is for a single cell,
        # max_col and max_row are None.
        max_col = match.group("max_col")
        max_col = max_col and get_col_index(max_col)

        max_row = match.group("max_row")
        max_row = max_row and int(max_row)

        if max_col and max_row:
            return ((min_col <= max_col)
                    and (min_row <= max_row)
                    and (max_col <= 16384)
                    and (max_row <= 1048576))
        else:
            return ((min_col <= 16384)
                    and (min_row <= 1048576))


def read_range(filepath, range_expr, sheet=None, dict_generator=None):
    """Read values from an Excel range into a dictionary.

    `range_expr` ie either a range address string, such as "A1", "$C$3:$E$5",
    or a defined name string for a range, such as "NamedRange1".
    If a range address is provided, `sheet` argument must also be provided.
    If a named range is provided and `sheet` is not, book level defined name
    is searched. If `sheet` is also provided, sheet level defined name for the
    specified `sheet` is searched.
    If range_expr points to a single cell, its value is returned.

    `dictgenerator` is a generator function that yields keys and values of 
    the returned dictionary. the excel range, as a nested tuple of openpyxl's
    Cell objects, is passed to the generator function as its single argument.
    If not specified, default generator is used, which maps tuples of row and
    column indexes, both starting with 0, to their values.
    
    Args:
        filepath (str): Path to an Excel file.
        range_epxr (str): Range expression, such as "A1", "$G4:$K10", 
            or named range "NamedRange1"
        sheet (str): Sheet name (case ignored).
            None if book level defined range name is passed as `range_epxr`.
        dict_generator: A generator function taking a nested tuple of cells 
            as a single parameter.

    Returns:
        Nested list containing range values.
    """

    def default_generator(cells):
        for row_ind, row in enumerate(cells):
            for col_ind, cell in enumerate(row):
                yield (row_ind, col_ind), cell.value

    book = opxl.load_workbook(filepath, data_only=True)

    if is_range_address(range_expr):
        sheet_names = [name.upper() for name in book.sheetnames]
        index = sheet_names.index(sheet.upper())
        cells = book.worksheets[index][range_expr]
    else:
        cells = get_namedrange(book, range_expr, sheet)

    # In case of a single cell, return its value.
    if isinstance(cells, opxl.cell.Cell):
        return cells.value

    if dict_generator is None:
        dict_generator = default_generator

    gen = dict_generator(cells)
    return {keyval[0]: keyval[1] for keyval in gen}


def get_namedrange(book, rangename, sheetname=None):
    """Get range from a workbook.

    A workbook can contain multiple definitions for a single name,
    as a name can be defined for the entire book or for
    a particular sheet.

    If sheet is None, the book-wide def is searched,
    otherwise sheet-local def is looked up.

    Args:
        book: An openpyxl workbook object.
        rangename (str): Range expression, such as "A1", "$G4:$K10",
            named range "NamedRange1".
        sheetname (str, optional): None for book-wide name def,
            sheet name for sheet-local named range.

    Returns:
        Range object specified by the name.

    """

    def cond(namedef):

        if namedef.type.upper() == 'RANGE':
            if namedef.name.upper() == rangename.upper():

                if sheetname is None:
                    if not namedef.localSheetId:
                        return True

                else:   # sheet local name
                    sheet_id = [sht.upper() for sht
                                in book.sheetnames].index(sheetname.upper())

                    if namedef.localSheetId == sheet_id:
                        return True

        return False

    def get_destinations(name_def):
        """Workaround for the bug in DefinedName.destinations"""

        from openpyxl.formula import Tokenizer
        from openpyxl.utils.cell import SHEETRANGE_RE

        if name_def.type == "RANGE":
            tok = Tokenizer("=" + name_def.value)
            for part in tok.items:
                if part.subtype == "RANGE":
                    m = SHEETRANGE_RE.match(part.value)
                    if m.group('quoted'):
                        sheet_name = m.group('quoted')
                    else:
                        sheet_name = m.group('notquoted')

                    yield sheet_name, m.group('cells')

    namedef = next((item for item in book.get_named_ranges()
                    if cond(item)), None)

    if namedef is None:
        return None

    dests = get_destinations(namedef)
    xlranges = []

    sheetnames_upper = [name.upper() for name in book.sheetnames]

    for sht, addr in dests:
        if sheetname:
            sht = sheetname
        index = sheetnames_upper.index(sht.upper())
        xlranges.append(book.worksheets[index][addr])

    if len(xlranges) == 1:
        return xlranges[0]
    else:
        return xlranges

