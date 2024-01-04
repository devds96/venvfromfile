from dataclasses import asdict, dataclass, fields
from hypothesis import assume, given
from hypothesis.strategies import booleans, composite, DrawFn, integers, \
    just, one_of
from typing import Dict, Type, Union

from venvfromfile._dataclasses_portability import dataclass \
    as dataclass_portable


class Unset:
    """A class whose values mark an unset field."""

    INSTANCE: "Unset"

    def __repr__(self) -> str:
        return "Unset"

    def __str__(self) -> str:
        return repr(self)


Unset.INSTANCE = Unset()


bool_or_unset = Union[bool, Unset]
"""The type of a boolean or unset field."""


@dataclass(frozen=True)
class ArgumentSpec:

    init: bool_or_unset

    repr: bool_or_unset

    eq: bool_or_unset

    order: bool_or_unset

    unsafe_hash: bool_or_unset

    frozen: bool_or_unset

    match_args: bool_or_unset

    kw_only: bool_or_unset

    slots: bool_or_unset

    weakref_slot: bool_or_unset

    def is_valid(self) -> bool:
        """Check whether this is a valid instance, meaning that the
        combination of arguments is valid for the @dataclass decorator.

        Returns:
            bool: Whether the instance is valid
        """
        if self.weakref_slot is True and self.slots is not True:
            return False
        if self.order is True and self.eq is False:
            return False
        # kw_only=True and init=False is an allowed combination.
        return True

    def to_dict(self) -> Dict[str, object]:
        """Convert the instance to a dict.

        Returns:
            dict[str, object]: The mapping from the argument names to
                their values.
        """
        return {
            k: v for k, v in asdict(self).items() if not isinstance(v, Unset)
        }

    _STRATEGIES = {
        bool_or_unset: one_of(booleans(), just(Unset.INSTANCE))
    }
    """Strategies for resolving the values of the `ArgumentSpec` classes
    fields."""

    @composite
    @classmethod
    def instances(draw: DrawFn, cls: Type["ArgumentSpec"]) -> "ArgumentSpec":
        """A hypothesis strategy constructing valid instances of the
        `ArgumentSpec` class.
        """

        def get_value(t):
            return draw(cls._STRATEGIES[t])  # type: ignore [index]

        result = cls(**{
            f.name: get_value(f.type) for f in fields(cls)
        })
        assume(result.is_valid())
        return result


@given(args=ArgumentSpec.instances(), value=integers())
def test_dataclass_construction(args: ArgumentSpec, value: int):
    """Test that dataclasses can be correctly constructed using the
    decorator.
    """

    @dataclass_portable(**args.to_dict())  # type: ignore [call-overload]
    class A:
        i: int

    if args.init is False:
        # There is no constructor. Manually assign the value.
        instance = A()  # type: ignore [call-arg]
        if args.frozen is True:
            object.__setattr__(instance, 'i', value)
        else:
            instance.i = value
    else:
        if args.kw_only is True:
            instance = A(i=value)  # type: ignore
        else:
            instance = A(value)  # type: ignore

    assert instance.i == value
