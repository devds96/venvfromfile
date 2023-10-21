__all__ = ["temp_dir", "temp_file"]

import functools as _functools
import os as _os
import os.path as _ospath
import sys
import tempfile as _tempfile

from contextlib import contextmanager as _contextmanager


def _ensure_tempdir_base() -> str:
    """Ensures that the temporary directory base exists.

    Returns:
        str: The path to the temporary directory.
    """
    tmp_location = _ospath.join(_ospath.dirname(__file__), "..", ".tmp")
    tmp_location = _ospath.normpath(tmp_location)
    _os.makedirs(tmp_location, exist_ok=True)
    return tmp_location


TMP_LOCATION = _ensure_tempdir_base()
"""The directory for temporary files and directories."""


@_contextmanager
def temp_dir():
    """Construct a temporary directory in the .tmp dir.

    Yields:
        str: The path to the temporary directory.
    """
    make = _functools.partial(
        _tempfile.TemporaryDirectory,
        dir=TMP_LOCATION
    )
    if sys.version_info >= (3, 10):
        make = _functools.partial(make, ignore_cleanup_errors=True)
    with make() as tdir:
        yield tdir


@_contextmanager
def temp_file(mode: str):
    """Construct a temporary file in the .tmp dir.

    Args:
        mode (str): The mode of the file to create.

    Yields:
        IO: The temporary file.
    """
    with _tempfile.TemporaryFile(mode, dir=TMP_LOCATION) as tfi:
        yield tfi
