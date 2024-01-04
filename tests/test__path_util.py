import pytest
import os
import os.path as ospath
import sys

from hypothesis import assume, given
from hypothesis.strategies import composite, DrawFn, sampled_from
from hypothesis_fspaths import fspaths  # type: ignore [import]
from os import PathLike
from typing import Union

import venvfromfile._path_util as _path_util


Path = Union[
    str, bytes, bytearray, memoryview, PathLike
]
"""Type of a path."""


PATHSEP = ospath.sep
"""The path separation character."""

ROOT = ospath.normcase(ospath.abspath(PATHSEP))
"""The root directory appearing in the tests."""


@composite
def fspaths_decodable(draw: DrawFn) -> Path:
    """A hypothesis strategy that filters paths which are not easily
    decodable.

    Args:
        draw (DrawFn): The draw function.

    Returns:
        Path: A path.
    """
    e = sys.getfilesystemencoding()
    t = draw(fspaths(allow_pathlike=True))
    p = os.fspath(t)
    if isinstance(p, str):
        return t
    if isinstance(p, (bytearray, memoryview)):
        p = bytes(p)
    f = draw(sampled_from([None, bytearray, memoryview]))
    if f is not None:
        t = f(p)
    if isinstance(p, bytes):
        try:
            p.decode(e)
            return t
        except UnicodeDecodeError:
            pass
    assume(False)
    # Failsafe, in case assume does something unexpected
    raise AssertionError


class TestToStrPath:

    @pytest.mark.parametrize("provide_encoding", [True, False])
    @given(path=fspaths_decodable())
    def test_str_to_path(self, path: Path, provide_encoding):
        """Check that `str_to_path` converts paths to str."""
        kwargs = dict()
        if provide_encoding:
            kwargs["encoding"] = sys.getfilesystemencoding()

        def compare(result: str):
            nonlocal path
            if isinstance(path, str):
                assert result == path
                return True
            if isinstance(path, (bytearray, memoryview)):
                path = bytes(path)
            if isinstance(path, bytes):
                e = sys.getfilesystemencoding()
                assert result.encode(e) == path
                return True
            return False

        p = _path_util.to_str_path(path, **kwargs)
        assert isinstance(p, str)

        if compare(p):
            return
        path = os.fspath(path)
        if not compare(p):
            raise AssertionError(
                f"Unexpected path object {path!r} received."
            )


class TestNormFully:
    """Tests for the `norm_fully` function."""

    @pytest.mark.parametrize("a_slash", [True, False])
    @pytest.mark.parametrize("b_slash", [True, False])
    def test_examples(self, a_slash: bool, b_slash: bool):
        """Test hand-selected examples."""
        s = PATHSEP if (a_slash or b_slash) else ''
        assert f"{ROOT}a{s}b" == _path_util.norm_fully(
            f"{PATHSEP}a{PATHSEP if a_slash else ''}"
            f"{PATHSEP if b_slash else ''}b"
        )

    def test_non_root_path_raises(self):
        """Test that a non-absolute path leads to an exception."""
        with pytest.raises(ValueError):
            _path_util.norm_fully("abc/def")


class TestResolveRelPath:
    """Tests for the `resolve_rel_path` function."""

    @pytest.mark.parametrize("root", [True, False])
    @pytest.mark.parametrize("a_slash", [True, False])
    @pytest.mark.parametrize("b_slash", [True, False])
    def test_examples(self, root: bool, a_slash: bool, b_slash: bool):
        """Test hand-selected examples."""
        if root:
            a = "/a"
            compare = f"{PATHSEP}a{PATHSEP}b"
        else:
            a = 'a'
            compare = f"a{PATHSEP}b"
        if a_slash:
            a = a + "//"
        assert _path_util.resolve_rel_path(a, 'b') == compare
