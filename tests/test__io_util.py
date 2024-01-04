import pytest
import io
import itertools

from hypothesis import given
from hypothesis.strategies import lists, text
from string import ascii_letters
from typing import Iterable, List, Tuple, TypeVar

import venvfromfile._io_util as _io_util


T = TypeVar('T')


def product_2_no_repetition(source: Iterable[T]) -> Iterable[Tuple[T, T]]:
    """Compute the second order product of an interable without
    repetitions.

    Args:
        source (Iterable[T]): The iterable for which to compute the
            product.

    Yields:
        tuple[T, T]: The elements of the product without repetition.
    """
    p = itertools.combinations(source, 2)
    nested = map(lambda t: (t, t[::-1]), p)
    result = itertools.chain.from_iterable(nested)
    return result


LINESEPS = ('\n', "\n\r", "\r\n")
"""Possible newline separators."""


class TestAppendLinesOnNewLine:
    """Tests for the `io_util.append_lines_on_new_line` function."""

    @pytest.mark.parametrize("linesep", LINESEPS)
    @given(lines=lists(text(ascii_letters)))
    def test_empty_file_no_lines(
        self,
        lines: List[str],
        linesep: str
    ):
        """Test the case where the file being written to is empty at the
        beginning.
        """
        text = linesep.join(lines)
        if len(lines) > 0:
            text += linesep
        with io.BytesIO(b'') as file_raw:
            file = io.BufferedRandom(file_raw)  # type: ignore [arg-type]
            _io_util.append_lines_on_new_line(file, lines, linesep=linesep)
            file_raw.seek(0, io.SEEK_SET)
            assert file_raw.read() == text.encode()

    @pytest.mark.parametrize("append_linesep", [True, False])
    @pytest.mark.parametrize("linesep", LINESEPS)
    @given(
        lines=lists(text(ascii_letters)),
        content=text(ascii_letters, min_size=1)
    )
    def test_text(
        self,
        lines: List[str],
        content: str,
        linesep: str,
        append_linesep: bool
    ):
        """Test the case where the file being written to contains a
        single line of text at beginning.
        """
        if append_linesep:
            content = content + linesep
        content_bytes = content.encode()
        num_lines = len(lines)
        if num_lines == 0:
            c = ''
        elif num_lines == 1:
            c = lines[0] + linesep
        else:
            c = linesep.join(lines) + linesep
        if append_linesep:
            content_w_linesep = content
        else:
            content_w_linesep = content + linesep
        text = content_w_linesep + c
        with io.BytesIO(content_bytes) as file_raw:
            file = io.BufferedRandom(file_raw)  # type: ignore [arg-type]
            _io_util.append_lines_on_new_line(file, lines, linesep=linesep)
            file_raw.seek(0, io.SEEK_SET)
            assert file_raw.read() == text.encode()

    @pytest.mark.parametrize("linesep", LINESEPS)
    @given(lines=lists(text(ascii_letters)))
    def test_only_linesep(
        self,
        lines: List[str],
        linesep: str,
    ):
        """Test the case where the file being written to contains a
        single linesep at beginning.
        """
        num_lines = len(lines)
        if num_lines == 0:
            c = ''
        elif num_lines == 1:
            c = lines[0] + linesep
        else:
            c = linesep.join(lines) + linesep
        text = linesep + c
        with io.BytesIO(linesep.encode()) as file_raw:
            file = io.BufferedRandom(file_raw)  # type: ignore [arg-type]
            _io_util.append_lines_on_new_line(file, lines, linesep=linesep)
            file_raw.seek(0, io.SEEK_SET)
            assert file_raw.read() == text.encode()

    @pytest.mark.parametrize(
        "separators", tuple(product_2_no_repetition(LINESEPS))
    )
    @given(
        lines=lists(text(ascii_letters)),
        content=text(ascii_letters, min_size=1)
    )
    def test_text_different_linesep(
        self,
        lines: List[str],
        content: str,
        separators: Tuple[str, str]
    ):
        """Test the case where the file being written to contains a
        single line of text at beginning, but the line separator in the
        file does not match the separator of the operating system
        (`os.linesep`).
        """
        linesep, linesep_target = separators

        content = content + linesep_target
        content_bytes = content.encode()
        num_lines = len(lines)
        if num_lines == 0:
            c = ''
        elif num_lines == 1:
            c = lines[0] + linesep
        else:
            c = linesep.join(lines) + linesep
        content_w_linesep = content
        text = content_w_linesep + c
        with io.BytesIO(content_bytes) as file_raw:
            file = io.BufferedRandom(file_raw)  # type: ignore [arg-type]
            _io_util.append_lines_on_new_line(file, lines, linesep=linesep)
            file_raw.seek(0, io.SEEK_SET)
            assert file_raw.read() == text.encode()
