"""This module contains utility functions for collections and
iterables.
"""

from typing import Callable as _Callable, Iterable as _Iterable, \
    Sequence as _Sequence, TypeVar as _TypeVar


_T = _TypeVar("_T")
_S = _TypeVar("_S")


def filter_existing(
    source: _Iterable[_S],
    target: _Iterable[_T],
    *,
    conv: _Callable[[_S], _T] = lambda x: x
) -> _Sequence[_S]:
    """Remove entries from an iterable if they appear in the target
    iterable. This will only iterate the target iterable once.

    Args:
        source (Iterable[S]): The iterable from which to remove existing
            entries.
        target (Iterable[T]): The target against which to check.
        conv (Callable[[S], T], optional): A callable converting entries
            of the source iterable to the same type as the target
            iterable. Defaults to the identity.

    Returns:
        Sequence[T]: The sequence of elements of `source` that do not
            appear in `target`.
    """
    sl = source
    for wp in target:
        sl = [p for p in sl if conv(p) != wp]
        if len(sl) == 0:
            return ()
    return tuple(sl)
