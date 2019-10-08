from modelx.core.util import is_valid_name, AutoNamer, ReorderableDict

import pytest


@pytest.mark.parametrize("name", ["Cells123", "Space_123"])
def test_is_valid_name_valid(name):
    assert is_valid_name(name)


@pytest.mark.parametrize(
    "name",
    ["123foo", "_foo", "foo bar", "*foo", "__foo__", "foo.bar", "boo/bar"],
)
def test_is_valid_name_invalid(name):
    assert not is_valid_name(name)


@pytest.fixture
def simplenamer():
    autonamer = AutoNamer("Cells")

    for i in range(10):
        autonamer.get_next([])

    return autonamer


def test_get_next(simplenamer):
    assert simplenamer.get_next([]) == "Cells11"


def test_get_next_skip_existing(simplenamer):
    existing_names = ["Cells11", "Cells12", "Cells13"]

    assert simplenamer.get_next(existing_names) == "Cells14"


def test_get_next_with_prefix():
    existing_names = ["model_BAK1", "model_BAK2", "model_BAK3"]

    autonamer = AutoNamer("_BAK")

    assert autonamer.get_next(existing_names, "model") == "model_BAK4"


@pytest.fixture
def reorderable_dict():
    dict_from = dict(zip("01234", range(5)))
    return ReorderableDict(dict_from)


class TestReorderableDict:

    def test_move_forward(self, reorderable_dict):
        reorderable_dict.move(2, 1, 2)
        expected = dict(zip("02314", (0, 2, 3, 1, 4)))
        assert reorderable_dict == expected

    def test_move_backward(self, reorderable_dict):
        reorderable_dict.move(1, 2, 2)
        expected = dict(zip("03124", (0, 3, 1, 2, 4)))
        assert reorderable_dict == expected

    @pytest.mark.parametrize(["length"], [[3], [5]])
    def test_move_maxlen(self, reorderable_dict, length):
        reorderable_dict.move(2, 1, length)
        expected = dict(zip("02341", (0, 2, 3, 4, 1)))
        assert reorderable_dict == expected

    @pytest.mark.parametrize(["index_from", "index_to", "length"],
                             [[2, 3, 3], [5, 3, 1]])
    def test_move_error(self, reorderable_dict, index_from, index_to, length):
        """Check error with invalid arguments"""
        with pytest.raises(IndexError):
            reorderable_dict.move(index_from, index_to, length)
