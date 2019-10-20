from textwrap import dedent


def test_clear_with_arg(sample_space):
    sample_space.fibo[5]

    sample_space.fibo.clear(3)
    assert set(sample_space.fibo) == {0, 1, 2}


def test_clear_value_with_kwarg(sample_space):
    sample_space.fibo[5]

    sample_space.fibo.clear(x=3)
    assert set(sample_space.fibo) == {0, 1, 2}


def test_clear_no_args(sample_space):
    sample_space.fibo[5]

    assert set(sample_space.fibo) == {0, 1, 2, 3, 4, 5}

    sample_space.fibo.clear()
    assert set(sample_space.fibo) == set()


def test_clear_other(sample_space):

    space = sample_space

    f1 = dedent(
        """\
        def source(x):
            if x == 1:
                return 1
            else:
                return source(x - 1) + 1"""
    )

    f2 = dedent(
        """\
        def dependant(x):
            return 2 * source(x)"""
    )

    space.new_cells(formula=f1)
    space.new_cells(formula=f2)

    space.dependant(2)
    assert set(space.dependant) == {2}
    assert set(space.source) == {1, 2}

    space.source.clear(1)
    assert set(space.source) == set()
    assert set(space.dependant) == set()

