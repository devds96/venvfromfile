"""This module serves as a portability helper for the builtin dataclass
decorator.
"""

import dataclasses as _dataclasses
import functools as _functools
import sys as _sys

from typing import Callable as _Callable, Optional as _Optional, \
    overload as _overload, Type as _Type, TypeVar as _TypeVar

if _sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import dataclass_transform as _dataclass_transform
else:  # pragma: no cover
    from typing import dataclass_transform as _dataclass_transform


_T = _TypeVar('_T')


@_dataclass_transform()
@_overload
def dataclass(
    cls: None = None,
    *,
    init: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = False,
    unsafe_hash: bool = False,
    frozen: bool = False,
    # 3.10
    match_args: bool = True,
    kw_only: bool = False,
    slots: bool = False,
    # 3.11
    weakref_slot: bool = False
) -> _Callable[[_Type[_T]], _Type[_T]]:
    pass


@_dataclass_transform()
@_overload
def dataclass(
    cls: _Type[_T],
    *,
    init: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = False,
    unsafe_hash: bool = False,
    frozen: bool = False,
    # 3.10
    match_args: bool = True,
    kw_only: bool = False,
    slots: bool = False,
    # 3.11
    weakref_slot: bool = False
) -> _Type[_T]:
    pass


@_dataclass_transform()
def dataclass(
    cls: _Optional[_Type] = None,
    *,
    init: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = False,
    unsafe_hash: bool = False,
    frozen: bool = False,
    # 3.10
    match_args: bool = True,
    kw_only: bool = False,
    slots: bool = False,
    # 3.11
    weakref_slot: bool = False
):
    """A portability helper for the standard library's @dataclass
    decorator.

    The following args are only available in Python 3.10 and above:
    "match_args", "kw_only", "slots".
    The following args are only available in Python 3.11 and above:
    "weakref_slot".

    If an argument is not available in the current Python version, it
    will be ignored.
    """
    base = _functools.partial(
        _dataclasses.dataclass,
        init=init, repr=repr, eq=eq, order=order, unsafe_hash=unsafe_hash,
        frozen=frozen
    )

    if _sys.version_info >= (3, 10):  # pragma: no cover
        base = _functools.partial(
            base, match_args=match_args, kw_only=kw_only, slots=slots
        )

    if _sys.version_info >= (3, 11):  # pragma: no cover
        base = _functools.partial(
            base, weakref_slot=weakref_slot
        )

    return base(cls)
