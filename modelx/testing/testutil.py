from modelx.core.base import Interface


def compare_model(src, trg):

    compare_views(src.spaces, trg.spaces, compare_each=compare_space)
    compare_views(src.refs, trg.refs, compare_each=compare_ref)


def compare_views(src, trg, compare_each):

    assert len(src) == len(trg)

    # Oder of items not tested
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

    compare_views(src.cells, trg.cells, compare_each=compare_cells)
    compare_views(src.refs, trg.refs, compare_each=compare_ref)
    if compare_subspace:
        compare_views(src.spaces, trg.spaces, compare_each=compare_space)


def compare_ref(src, trg):

    if isinstance(src, Interface):
        pass
    else:
        assert src == trg


def compare_cells(src, trg):
    if src.name == "IntAccumCF":
        if trg.parent.name == "OuterProj":
            print(src.formula.source)
            print(trg.formula.source)

    assert src.formula.source == trg.formula.source
