"""This module handles things related to the Python version running the
package.
"""

import functools as _functools
import itertools as _itertools
import operator as _operator
import re as _re
import sys as _sys

from typing import ClassVar as _ClassVar, Optional as _Optional, \
    Sequence as _Sequence, Tuple as _Tuple, Union as _Union

if _sys.version_info >= (3, 8):  # pragma: no cover
    import typing as _typing
    from typing import final as _final, Literal as _Literal
else:  # pragma: no cover
    from typing_extensions import final as _final  # type: ignore [assignment] # noqa: E501
    from typing_extensions import Literal as _Literal  # type: ignore [assignment] # noqa: E501

if _sys.version_info >= (3, 10):  # pragma: no cover
    from typing import TypeGuard as _TypeGuard
else:  # pragma: no cover
    from typing_extensions import TypeGuard as _TypeGuard  # type: ignore [assignment] # noqa: E501,F811


from ._dataclasses_portability import dataclass as _dataclass


ReleaseLevel = _Literal[
    "alpha", "beta", "candidate", "final"  # noqa: F821
]
"""The possible release level values."""


VersionInfo = _Union[
    _Tuple[int],
    _Tuple[int, int],
    _Tuple[int, int, int],
    _Tuple[int, int, int, ReleaseLevel],
    _Tuple[int, int, int, ReleaseLevel, int]
]
"""The type of a version info."""


def format_version_info(vit: VersionInfo) -> str:
    """Format a given Python version info as a `str`. The format
    corresponds to
    "{major}.{minor}.{micro}-{releaselevel}-{serial}".

    Args:
        vit (tuple[int | str, ...]): The version info tuple.

    Returns:
        str: The formatted version info.
    """
    seps = _itertools.chain(['.', '.', '-', '-'])
    vit_iter = iter(map(str, vit))
    first = next(vit_iter)
    return _functools.reduce(
        "{0}{1[0]}{1[1]}".format, zip(seps, vit_iter), first
    )


_RELEASE_LEVELS = (
    _typing.get_args(ReleaseLevel)
) if _sys.version_info >= (3, 8) else (
    ReleaseLevel.__args__  # type: ignore [attr-defined]
)
"""The release levels."""


def parse_pyversion(ver_str: str) -> VersionInfo:
    """Parse a Python version string.

    Args:
        ver_str (str): The version string to parse.

    Raises:
        ValueError: If the string is malformed.

    Returns:
        VersionInfo: The parsed version info.
    """
    if not isinstance(ver_str, str):
        raise ValueError("'ver_str' is not a str.")

    splt = ver_str.split('.')
    l_splt = len(splt)
    if len(splt) == 3:
        final_str = splt[2]
        if final_str.startswith("-"):
            raise ValueError(
                "Unexpected '-' at beginning of micro version."
            )
        rest = final_str.split('-')
        if len(rest) > 3:
            raise ValueError("Too many '-' in version info str.")
        splt = splt[:2] + rest
    elif l_splt > 3:
        raise ValueError("Too many '.' in version info str.")

    def handle_release(r: str) -> str:
        rs = r.strip("'\"")
        if rs not in _RELEASE_LEVELS:
            raise ValueError(
                f"Invalid release level {r!r} in version info str."
            )
        return rs

    def handle_int(v: str) -> int:
        try:
            res = int(v)
        except ValueError:
            raise ValueError(
                f"Invalid version number {v!r} in version info str."
            )
        if res < 0:
            raise ValueError(
                f"Negative version number {v!r} in version info str."
            )
        return res

    ops = (handle_int,) * 3 + (handle_release, handle_int)
    result = tuple(map(lambda fs: fs[0](fs[1]), zip(ops, splt)))
    return result  # type: ignore [return-value]


ComparisonOperator = _Literal['>', '<', ">=", "<="]  # noqa: F722
"""Represents a comparison operator as a str."""


@_final
@_dataclass(frozen=True, slots=True)
class PyVerComparison:
    """A Python version combined with a comparison operator."""

    operator: ComparisonOperator
    """The comparison operator."""

    version: VersionInfo
    """The Python version."""

    def __str__(self) -> str:
        return f"{self.operator}{format_version_info(self.version)}"

    OPERATORS: _ClassVar[_Tuple[ComparisonOperator]] = (
        _typing.get_args(ComparisonOperator)
    ) if _sys.version_info >= (3, 8) else (
        ComparisonOperator.__args__  # type: ignore [attr-defined]
    )
    """The comparison operators."""

    _OPERATOR_MAP: _ClassVar = {
        '>': _operator.gt,
        ">=": _operator.ge,
        '<': _operator.lt,
        "<=": _operator.le
    }
    """Maps the operator str values to the actual operator functions."""

    def applies_to_current_pyversion(self) -> bool:
        """Check if the comparison described by this instance applies to
        the current Python version.

        Returns:
            bool: Whether the comparison applies.
        """
        op_func = self._OPERATOR_MAP[self.operator]
        return op_func(_sys.version_info, self.version)

    _WHITESPACE_RE = _re.compile(r"\s+", _re.UNICODE)
    """A regex to match whitespace."""

    @classmethod
    def _is_operator_str(cls, s: str) -> _TypeGuard[ComparisonOperator]:
        """Check if the provided `str` is a `ComparisonOperator`.

        Args:
            s (str): The str to check.

        Returns:
            TypeGuard[ComparisonOperator]: Whether `s` is a valid
                `ComparisonOperator`.
        """
        return s in cls.OPERATORS

    @classmethod
    def parse(
        cls,
        text: str,
        *,
        coerce_ops: _Optional[_Sequence[ComparisonOperator]] = None
    ) -> "PyVerComparison":
        """Parse a `PyVerComparison` from a str.

        Args:
            text (str): The text to parse.
            coerce_ops (Optional[Sequence[ComparisonOperator]],
                optional): The allowed operators. If a different
                comparison operator is found, a `ValueError` is raised.
                Defaults to None, which does not check if the operator
                is of a specific kind.

        Raises:
            ValueError: If the provided text can not be parsed.

        Returns:
            PyVerComparison: The parsed `PyVerComparison` instance.
        """
        text = cls._WHITESPACE_RE.sub('', text)
        if text == '':
            raise ValueError("The provided str was empty or whitespace.")

        if (len(text) > 2) and (text[1] == '='):
            operator = text[:2]
            rest = text[2:]
        else:
            operator = text[0]
            rest = text[1:]

        if not cls._is_operator_str(operator):
            raise ValueError(f"Invalid comparison operator {operator!r}.")
        if (coerce_ops is not None) and (operator not in coerce_ops):
            raise ValueError(
                f"Invalid comparison operator {operator!r}, expected "
                f"one of {', '.join(map(repr, coerce_ops))}."
            )

        version = parse_pyversion(rest)
        return PyVerComparison(operator, version)

    @classmethod
    def _parse_mm_version(
        cls,
        text: str,
        ops: _Sequence[ComparisonOperator],
        default: ComparisonOperator
    ) -> "PyVerComparison":
        """Parse a min or max version and return a version comparison
        object.

        Args:
            text (str): The text to parse.
            ops (Sequence[ComparisonOperator]): The allowed operators.
            default (ComparisonOperator): The default operator.

        Returns:
            PyVerComparison: The version comparison object.
        """
        if not isinstance(text, str):
            raise TypeError(
                "The provided text was not a str, but "
                f"{type(text).__name__!r}."
            )
        if text.startswith(tuple(cls.OPERATORS)):
            return cls.parse(text, coerce_ops=ops)
        version = parse_pyversion(text)
        return cls(default, version)

    @classmethod
    def parse_min_version(cls, text: str) -> "PyVerComparison":
        """Parse a min version and return a version comparison object.
        Only '>' and ">=" are allowed as operators and ">=" is the
        default.

        Args:
            text (str): The text to parse.

        Returns:
            PyVerComparison: The version comparison object.
        """
        return cls._parse_mm_version(text, ('>', ">="), ">=")

    @classmethod
    def parse_max_version(cls, text: str) -> "PyVerComparison":
        """Parse a max version and return a version comparison object.
        Only '<' and "<=" are allowed as operators and '<' is the
        default.

        Args:
            text (str): The text to parse.

        Returns:
            PyVerComparison: The version comparison object.
        """
        return cls._parse_mm_version(text, ('<', "<="), '<')
