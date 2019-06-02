from modelx.core.base import Interface


def compare_model(src, trg):

    assert src.doc == trg.doc
    assert src.name[:len(trg.name)] == trg.name  # Exclude _BAKn

    compare_views(src.spaces, trg.spaces, compare_each=compare_space)
    compare_views(src.refs, trg.refs, compare_each=compare_ref)


def compare_views(src, trg, compare_each):

    assert len(src) == len(trg)

    # Order of items not tested
    assert set(src) == set(trg)
    for name_src, val_src in src.items():
        compare_each(val_src, trg[name_src])

    # Replace above with below when order preservation is implemented.

    # for (name_src, val_src), (name_trg, val_trg) in zip(
    #     src.items(), trg.items()
    # ):
    #     assert name_src == name_trg
    #     compare_each(val_src, val_trg)


def compare_space(src, trg, compare_subspace=True):

    assert src.doc == trg.doc
    if src.formula:
        assert src.formula.source == trg.formula.source

    compare_views(src.cells, trg.cells, compare_each=compare_cells)
    compare_views(src.refs, trg.refs, compare_each=compare_ref)
    if compare_subspace:
        compare_views(src.spaces, trg.spaces, compare_each=compare_space)


def compare_ref(src, trg):

    if isinstance(src, Interface):
        assert src.fullname.split(".")[1:] == trg.fullname.split(".")[1:]
    else:
        assert src == trg


def compare_cells(src, trg):

    assert src.doc == trg.doc
    assert src.formula.source == trg.formula.source
