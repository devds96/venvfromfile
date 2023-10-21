from hypothesis import given
from hypothesis.strategies import lists, text
from string import ascii_letters
from typing import List as _List

import venvfromfile._collection_util as _collection_util


class TestFilterExisting:
    """Tests for the `collection_util.filter_existing` function."""

    @given(source=lists(text(ascii_letters)))
    def test_empty_target(self, source: _List[str]):
        """Test that if the target is empty, the source is returned
        unchanged.
        """
        result = _collection_util.filter_existing(tuple(source), ())
        assert all(map(lambda rs: rs[0] == rs[1], zip(result, source)))

    @given(target=lists(text(ascii_letters)))
    def test_empty_source(self, target: _List[str]):
        """Test that if the source is empty, an empty iterable will be
        returned.
        """
        result = _collection_util.filter_existing((), tuple(target))
        assert not any(True for _ in result)

    @given(st=lists(text(ascii_letters)))
    def test_same_iterable(self, st: _List[str]):
        """Test that if the and the target coincide, an emtpy iterable
        is returned.
        """
        result = _collection_util.filter_existing(tuple(st), tuple(st))
        assert not any(True for _ in result)

    def test_simple_example(self):
        """Test a simple, manually constructed example."""
        S = (1, 2, 3, 5)
        T = (2, 3, 4)
        result = _collection_util.filter_existing(S, T)
        assert result == (1, 5)

    def test_simple_example_conv(self):
        """Test a simple, manually constructed example involving the
        conv argument."""
        S = (1, 2, 3, 5)
        T = map(str, (2, 3, 4))
        result = _collection_util.filter_existing(S, T, conv=str)
        assert result == (1, 5)
