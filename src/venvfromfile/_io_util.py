"""This module contains utility functions for handling IO operations."""

import errno as _errno
import io as _io
import logging as _logging
import os as _os

from typing import Iterable as _Iterable, Optional as _Optional


_logger = _logging.getLogger(__name__)
"""The logger for this module."""


def append_lines_on_new_line(
    file: _io.BufferedRandom,
    lines: _Iterable[str],
    *,
    linesep: _Optional[str] = None
):
    """Appends lines to a file and ensures that the first printed
    character is on a new line. An attempt is made to ensure that no
    redundant newline is appended to the file by checking the last
    character in the file for '\\n'. Finally, the file will end with
    `linesep` since this appended after every entry in `lines`. This
    function makes no assumptions about the position of the provided
    stream. There is no guarantee about the position of the stream
    after the function call completes.

    Args:
        file (PathLike): The path of the file.
        lines (Iterable[str]): The lines to append. Between each
            entry `linesep` will be written to the file.
        linesep (str, optional): The line separator to append between
            each entry of `lines`. Defaults to `os.linesep`.
    """
    # To the beginning of the file
    file.seek(0, _io.SEEK_SET)

    prepend_linesep = False  # Whether we need to write a linesep first

    # Check if the file is not empty
    if file.peek(1) != b'':
        try:
            file.seek(-2, _io.SEEK_END)
        except OSError as oe:  # pragma: no cover
            # This only seems to happen with streams which are from and
            # to disk and not with BytesIO for example.
            if oe.errno != _errno.EINVAL:
                raise
            # This means that going back two bytes would move the
            # cursor beyond the beginning of the file.
            _logger.debug("Expected exception: %s", oe, exc_info=oe)
            # There is only a single character in the file.
            file.seek(-1, _io.SEEK_END)
        # Check the last two bytes (or the single byte)
        last = file.read(2)
        # Handle \n, \n\r and \r\n line endings
        last_is_n = bytes([last[-1]]) == b'\n'
        last2_are_nr = last == b"\n\r"
        if not (last_is_n or last2_are_nr):
            prepend_linesep = True

    if linesep is None:  # pragma: no cover
        linesep = _os.linesep

    # Now we have a newline at the end. Write the lines.
    # We do not own the stream so we cannot close it, and only have to
    # detach in the end.
    # The newline='' prevents automatic translation of \n characters
    # to the operating system newlines. We want to ensure that only
    # linesep is written, even if it is an illegal newline character
    # combination.
    ofit = _io.TextIOWrapper(file, newline='')
    if prepend_linesep:
        ofit.write(linesep)
    for line in lines:
        ofit.write(line)
        ofit.write(linesep)
    # It's unclear if detach() flushes.
    ofit.flush()
    ofit.detach()
