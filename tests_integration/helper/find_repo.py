import functools as _functools
import io as _io
import itertools as _itertools
import os.path as ospath
import subprocess as _subprocess

import venvfromfile._path_util as _path_util

from . import temporary_helper as _temporary_helper


# We do not want to read the file all at once, which is what
# readlines on a text file does (returns a list[str]).
def _readlines_lazy(file: _io.TextIOWrapper):
    """Generator to read a file line by line.

    Args:
        file (TextIOWrapper): The file to read.

    Yields:
        str: The read lines, with leading and trailing newline
            characters \\n and \\r removed.
    """
    # Even "emtpy" lines end with a newline character (which is also
    # returned from readline) and are therefore not empty.
    while True:
        line = file.readline()
        if len(line) <= 0:
            break
        yield line.strip("\n\r")


def nth_parent(path: str, n: int) -> str:
    """Get the nth parent directory of a directory.

    Args:
        path (str): The path to traverse upwards.
        n (int): The number of the parent to return. 0 returns the
            directory itself. 1 returns the parent directory.

    Returns:
        str: The parent path. If n is too large, so that the directory
            would lie beyond the root directory, the root directory
            is returned instead.
    """
    if n < 0:
        raise ValueError("n was negative.")
    if n == 0:
        return path
    return _functools.reduce(
        lambda p, f: f(p),
        _itertools.repeat(ospath.dirname, n),
        path
    )


def _get_repo_path() -> str:
    """Find the path of the git repo containing this file.

    Raises:
        AssertionError: If the path cannot be found.

    Returns:
        str: The path to the repo containing this file.
    """
    this_file = ospath.normcase(ospath.normpath(__file__))
    path = nth_parent(this_file, 3)

    def handle_failed_process(
        command: str, cpe: _subprocess.CalledProcessError
    ):
        raise AssertionError(
            f"Could not determine the path to the git repo. {command!r} "
            f"failed with exit code {cpe.returncode}. "
            f"Candidate for directory: {path!r}"
        ) from cpe

    # Check if it is a git repo
    try:
        _subprocess.check_output(
            ["git", "status"], cwd=path
        )
    except _subprocess.CalledProcessError as cpe:
        handle_failed_process("git status", cpe)

    get_full_path = _functools.partial(_path_util.resolve_rel_path, path)

    # Check if this file is in the git repo
    with _temporary_helper.temp_file("w+") as tmpfile:
        try:
            _subprocess.check_call(
                ["git", "ls-files"], cwd=path, universal_newlines=True,
                stdout=tmpfile
            )
        except _subprocess.CalledProcessError as cpe:
            handle_failed_process("git ls-files", cpe)
        tmpfile.seek(0, _io.SEEK_SET)
        lines_as_files = map(get_full_path, _readlines_lazy(tmpfile))
        if any(map(this_file.__eq__, lines_as_files)):
            return path

    raise AssertionError(
        f"Unable to find the correct git repo. Candidate: "
        f"{path!r}"
    )


REPO_LOCATION = _get_repo_path()
"""The location of the git repo containing this file."""
