import modelx as mx
from modelx.core.base import Interface, null_impl


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

    # assert src.doc == trg.doc # TODO: Make doc identical after serialization
    if src.formula:
        assert src.formula.source == trg.formula.source

    compare_views(src.cells, trg.cells, compare_each=compare_cells)
    compare_views(src.refs, trg.refs, compare_each=compare_ref)
    if compare_subspace:
        compare_views(src.spaces, trg.spaces, compare_each=compare_space)


def compare_ref(src, trg):

    if isinstance(src, Interface):
        if src._is_valid():
            assert src.fullname.split(".")[1:] == trg.fullname.split(".")[1:]
        else:
            assert type(src) == type(trg)
            assert src._impl is trg._impl is null_impl
    else:
        assert src == trg


def compare_cells(src, trg):

    assert src.doc == trg.doc
    assert src.formula.source == trg.formula.source


class ConfigureExecutor:
    
    def __init__(self, maxdepth=None, use_formula_error=False):
        self.maxdepth = maxdepth
        self.use_formula_error = use_formula_error
        if maxdepth is not None:
            self.maxdepth_saved = mx.get_recursion()

    def __enter__(self):
        if self.maxdepth is not None:
            mx.set_recursion(self.maxdepth)
        
        self.saved = mx.use_formula_error()
        mx.use_formula_error(self.use_formula_error)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.maxdepth is not None:
            mx.set_recursion(self.maxdepth_saved)
        
        mx.use_formula_error(self.saved)
