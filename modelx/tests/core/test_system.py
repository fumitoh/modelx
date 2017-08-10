from modelx.core.api import *


def test_defcells_withname():

    create_model().create_space()

    @defcells(name="bar")
    def foo(x):
        if x == 0:
            return 123
        else:
            return bar(x - 1)

    assert foo[10] == 123


def test_defcells_withspace():

    @defcells(space=get_currentspace())
    def foo(x):
        if x == 0:
            return 123
        else:
            return foo(x - 1)

    assert foo[10] == 123


def test_create_cells_from_module():
    # import modelx.tests.core.data.sample as sample
    from .data import sample

    cells = create_cells_from_module(sample)
    assert set(sample.funcs) == set(cells.keys())


def test_create_cells_from_module_name():
    # import modelx.tests.core.data.sample as sample
    from .data import sample

    # module_name = 'modelx.tests.core.data.sample'
    names = __name__.split('.')
    names = names[:-1] + ['data', 'sample']
    module_name = '.'.join(names)

    cells = create_cells_from_module(module_name)
    assert set(sample.funcs) == set(cells.keys())


