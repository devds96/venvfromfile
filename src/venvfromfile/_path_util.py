"""This module contains utility functions to handle paths."""

import functools as _functools
import os as _os
import os.path as _ospath
import sys as _sys

from os import PathLike as _PathLike
from typing import Optional as _Optional, Union as _Union


def to_str_path(
    path: _Union[str, bytes, bytearray, memoryview, _PathLike],
    *,
    encoding: _Optional[str] = None
) -> str:
    """Convert a path of several types to a str path.

    Args:
        path (str | bytes | PathLike[str] | PathLike[bytes]): The path
            to convert.
        encoding (str, optional): The encoding to use for byte-like
            paths. Defaults to the file system encoding as provided by
            `sys.getfilesystemencoding()`.

    Returns:
        str: The provided path as a `str`.
    """
    if isinstance(path, (bytearray, memoryview)):
        path = bytes(path)
    path = _os.fspath(path)
    if isinstance(path, bytes):
        if encoding is None:
            encoding = _sys.getfilesystemencoding()
        # It might be necessary to implement more elaborate decoding.
        path = path.decode(encoding)
    return path  # type: ignore [return-value]


_norm_funcs = (
    _ospath.realpath,
    _ospath.normpath,
    _ospath.normcase
)
"""The functions to apply in this order to fully normalize a path."""


def norm_fully(path: str) -> str:
    """Fully norm an absolute path. Resolve symlinks and normalize the
    path, removing slashes etc. Finally, normalize the case.

    Args:
        path (str): The path to normalize.

    Returns:
        str: The normalized path.
    """
    if not _ospath.isabs(path):
        raise ValueError(f"The provided pat {path!r} was not absolute.")
    return _functools.reduce(
        lambda p, f: f(p),  # type: ignore [operator]
        _norm_funcs,
        path
    )


def resolve_rel_path(base: str, path: str) -> str:
    """Resolve a relative path given the base.

    Args:
        base (str): The base path. `path` is interpreted as being
            relative to this path.
        path (str): The path to resolved.

    Returns:
        str: The resolved path.
    """
    full_path = _ospath.join(base, path)
    full_path = _ospath.normpath(full_path)
    return full_path
