import pytest
import sys
import itertools
import more_itertools

from dataclasses import dataclass
from hypothesis import assume, given
from hypothesis.strategies import booleans, composite, DrawFn, floats, \
    integers, lists, one_of, sampled_from, text
from string import ascii_letters
from typing import Iterable, List, Optional, Sequence, Tuple, Type, \
    TypeVar, Union

import venvfromfile._pyver as _pyver

from venvfromfile._pyver import VersionInfo


RELEASE_LEVELS = ("alpha", "beta", "candidate", "final")
"""The valid release levels."""


@dataclass(frozen=True)
class VerInfo:
    """Wraps a version info tuple."""

    version: VersionInfo
    """The action version info tuple."""

    def to_str(self, rl_quote: Optional[str] = None):
        """Convert the version info to its str representation."""
        ver = self.version
        length = len(ver)
        it = iter(ver)
        ltxt = [str(next(it))]
        if length >= 2:
            ltxt.append(f".{next(it)}")
        if length >= 3:
            ltxt.append(f".{next(it)}")
        if length >= 4:
            rl: Union[str, int]
            rl = next(it)
            if rl_quote is not None:
                rl = f"{rl_quote}{rl}{rl_quote}"
            ltxt.append(f"-{rl}")
        if length >= 5:
            ltxt.append(f"-{next(it)}")
        return ''.join(ltxt)

    @composite
    @classmethod
    def instances(
        draw: DrawFn,
        cls: Type["VerInfo"],
        *,
        length: Optional[Union[int, Sequence[int]]] = None
    ) -> "VerInfo":
        """A hypothesis strategy to generate Python version number tuples
        and their str representation.
        """
        pos_ints = integers(min_value=0)
        if length is None:
            length = draw(integers(1, 5))
        elif isinstance(length, Sequence):
            length = draw(sampled_from(length))
        elif not (1 <= length <= 5):
            raise ValueError(f"Invalid length {length!r}.")
        res: List[Union[str, int]] = [draw(pos_ints)]
        if length >= 2:
            res.append(draw(pos_ints))
        if length >= 3:
            res.append(draw(pos_ints))
        if length >= 4:
            res.append(draw(sampled_from(RELEASE_LEVELS)))
        if length >= 5:
            res.append(draw(pos_ints))
        return cls(tuple(res))  # type: ignore [arg-type]


@composite
def non_release_str(draw: DrawFn) -> str:
    """A hypothesis strategy returning str values which are not the
    allowed release level str values.
    """
    s = draw(text(ascii_letters))
    assume(s not in RELEASE_LEVELS)
    return s


@composite
def non_str(draw: DrawFn) -> object:
    """A hypothesis strategy returning several different objects except
    for str instances.
    """
    return draw(one_of(
        floats(),
        integers(),
        booleans(),
        sampled_from([dict, float, int, object, object(), str])
    ))


@composite
def invalid_release_version_info_str(draw: DrawFn) -> str:
    """A hypothesis strategy to generate version info strings with
    invalid release levels.
    """
    rl = draw(non_release_str())
    v: List[Union[str, int]] = draw(
        lists(integers(0), min_size=4, max_size=5)
    )
    v.insert(3, rl)
    vit = tuple(v)
    return _pyver.format_version_info(vit)  # type: ignore [arg-type]


@composite
def whitespace_or_empty(draw: DrawFn) -> str:
    """A hypothesis strategy generating whitespace and empty strings."""
    return draw(text(" \t\n\r\f\v"))


@dataclass(frozen=True)
class PyVerComp:
    """A `PyVerComparison` with the corresponding str."""

    comp: _pyver.PyVerComparison
    """The comparison."""

    as_str: str
    """The str representation."""

    def get_other_operators(self) -> Iterable[_pyver.ComparisonOperator]:
        """Get an iterable over the other comparison operators.

        Returns:
            Iterable[ComparisonOperator]: All comparison operators
                except for `comp.operator`.
        """
        return itertools.filterfalse(
            self.comp.operator.__eq__,
            _pyver.PyVerComparison.OPERATORS
        )

    @composite
    @classmethod
    def instances(draw: DrawFn, cls: Type["PyVerComp"]) -> "PyVerComp":
        """A hypothesis strategy generaing `PyVerComparison` instances
        and their str representations as `PyVerComp` instances.
        """
        ver_inf = draw(VerInfo.instances())
        quote = draw(sampled_from(("\"", "'", None)))
        ver_inf_str = ver_inf.to_str(quote)
        operator = draw(sampled_from(_pyver.PyVerComparison.OPERATORS))
        return cls(
            _pyver.PyVerComparison(operator, ver_inf.version),
            operator + ver_inf_str
        )


@composite
def invalid_comparison_operator(draw: DrawFn) -> str:
    """A hypothesis strategy generating text that does not contain
    comparison operators.
    """
    txt = draw(text(min_size=1))
    assume(all(x not in txt for x in _pyver.PyVerComparison.OPERATORS))
    return txt


@composite
def pyver_comparison_invalid_operator(draw: DrawFn) -> str:
    """A hypothesis strategy generaing `PyVerComparison` str
    representations with invalid comparison operators.
    """
    ver_inf = draw(VerInfo.instances())
    quote = draw(sampled_from(("\"", "'", None)))
    ver_inf_str = ver_inf.to_str(quote)
    op = draw(invalid_comparison_operator())
    return op + ver_inf_str


T = TypeVar('T')


def all_partition_entries(sq: Iterable[T]) -> Iterable[Sequence[T]]:
    """Generate all possible partitions of an íterable and iterate
    through all partition entries.

    Args:
        sq (Iterable[T]): The iterable to partition.

    Returns:
        Iterable[Sequence[T]]: The partition entries.
    """
    ps = more_itertools.partitions(sq)
    return itertools.chain.from_iterable(ps)


class TestFormatVersionInfo:
    """Tests for the `format_version_info` function."""

    @given(case=VerInfo.instances())
    def test_format_version_info(self, case: VerInfo):
        """Check that version informations are formatted correctly."""
        assert _pyver.format_version_info(case.version) == case.to_str()


class TestParsePyversion:
    """Tests for the `parse_pyversion` function."""

    @pytest.mark.parametrize("rl_quote", ("\"", "'", None))
    @given(case=VerInfo.instances())
    def test_parse_pyversion(self, case: VerInfo, rl_quote: Optional[str]):
        """Check that version informations are formatted correctly."""
        assert case.version == _pyver.parse_pyversion(case.to_str(rl_quote))

    @given(value=non_str())
    def test_not_str_raises(self, value):
        """Check that an exception is raised if an object that is passed
        is not a str.
        """
        with pytest.raises(ValueError, match="'ver_str' is not a str."):
            _pyver.parse_pyversion(value)

    @given(
        case=VerInfo.instances(length=5),
        extra=lists(integers(0), min_size=1)
    )
    def test_too_many_dashes(self, case: VerInfo, extra: Tuple[int, ...]):
        """Check that an exception is raised when too many dashes
        appear.
        """
        txt = f"{case.to_str()}-{'-'.join(map(str, extra))}"
        with pytest.raises(ValueError, match=r"Too many \'\-\'.*"):
            _pyver.parse_pyversion(txt)

    @given(case=VerInfo.instances(length=(4, 5)))
    def test_too_many_dots(self, case: VerInfo):
        """Check that an exception is raised when too many dots
        appear.
        """
        txt = case.to_str().replace('-', '.')
        with pytest.raises(ValueError, match=r"Too many \'\.\'.*"):
            _pyver.parse_pyversion(txt)

    @given(case=invalid_release_version_info_str())
    def test_invalid_release(self, case: str):
        """Check that invalid release version str values lead to
        exceptions.
        """
        with pytest.raises(ValueError, match="Invalid release level.*"):
            _pyver.parse_pyversion(case)

    @given(character=text(ascii_letters))
    def test_non_int_raises(self, character: str):
        """Test that non-int characters where the integers are expected
        lead to an exception.
        """
        msg = f"Invalid version number {character!r}.*"
        with pytest.raises(ValueError, match=msg):
            _pyver.parse_pyversion(f"{character}.11.4")
        with pytest.raises(ValueError, match=msg):
            _pyver.parse_pyversion(f"3.{character}.4")
        with pytest.raises(ValueError, match=msg):
            _pyver.parse_pyversion(f"3.11.{character}")
        with pytest.raises(ValueError, match=msg):
            _pyver.parse_pyversion(f"3.11.4-alpha-{character}")

    def test_negative_version_raises(self):
        """Test that negative numbers in the version str lead to an
        exception.
        """
        m = "Negative version number '-1'.*"
        with pytest.raises(ValueError, match=m):
            _pyver.parse_pyversion("-1.11.4")
        with pytest.raises(ValueError, match=m):
            _pyver.parse_pyversion("3.-1.4")
        m2 = "Unexpected '-' at beginning of micro version."
        with pytest.raises(ValueError, match=m2):
            _pyver.parse_pyversion("3.11.-1")


class TestPyVerComparison:
    """Tests for the `PyVerComparison` class."""

    @given(case=PyVerComp.instances())
    def test_parse_and___str__(self, case: PyVerComp):
        """Test that the parse and __str__ methods are (almost) inverse
        functions of each other.
        """
        parsed = _pyver.PyVerComparison.parse(case.as_str)
        assert parsed.version == case.comp.version
        assert parsed.operator == case.comp.operator
        assert str(parsed) == case.as_str.replace("'", '').replace("\"", '')

    @given(txt=whitespace_or_empty())
    def test_parse_empty_str_or_only_whitespace_raises(self, txt: str):
        """Test that an empty str leads to an exception."""
        with pytest.raises(ValueError, match=r".*empty or whitespace\..*"):
            _pyver.PyVerComparison.parse(txt)

    def test_applies_to_current(self):
        """Test the `applies_to_current_pyversion` member function."""
        ver_str = _pyver.format_version_info(sys.version_info)

        lt = _pyver.PyVerComparison.parse(f"<{ver_str}")
        assert not lt.applies_to_current_pyversion()
        gt = _pyver.PyVerComparison.parse(f">{ver_str}")
        assert not gt.applies_to_current_pyversion()

        le = _pyver.PyVerComparison.parse(f"<={ver_str}")
        assert le.applies_to_current_pyversion()
        ge = _pyver.PyVerComparison.parse(f">={ver_str}")
        assert ge.applies_to_current_pyversion()

    @given(case=pyver_comparison_invalid_operator())
    def test_invalid_comparison_operator(self, case: str):
        """Test that invalid comparison operators lead to an
        exception.
        """
        msg = "Invalid comparison operator.*"
        with pytest.raises(ValueError, match=msg):
            _pyver.PyVerComparison.parse(case)

    @given(case=PyVerComp.instances())
    def test_test_coerce_ops_valid(self, case: PyVerComp):
        """Test the `coerce_ops` argument with valid inputs."""
        result = _pyver.PyVerComparison.parse(
            case.as_str, coerce_ops=[case.comp.operator]
        )
        assert result == case.comp

    @given(case=PyVerComp.instances())
    def test_test_coerce_ops_invalid_raises(self, case: PyVerComp):
        """Test the `coerce_ops` argument with invalid inputs."""
        msg = "Invalid comparison operator.*"
        for p in all_partition_entries(case.get_other_operators()):
            with pytest.raises(ValueError, match=msg):
                _pyver.PyVerComparison.parse(case.as_str, coerce_ops=p)

    class TestParseMinVersion:
        """Tests for the `parse_min_version` function."""

        @pytest.mark.parametrize("op", ('>', ">=", None))
        @given(case=VerInfo.instances())
        def test_valid_cases(self, case: VerInfo, op: Union[str, None]):
            """Test valid cases for the `parse_min_version` function."""
            txt = case.to_str()
            ver_text = (op + txt) if op is not None else txt
            p = _pyver.PyVerComparison.parse_min_version(ver_text)
            if op is not None:
                assert p.operator == op
            else:
                assert p.operator == ">="
            assert p.version == case.version

        @pytest.mark.parametrize("op", ('<', "<="))
        @given(case=VerInfo.instances())
        def test_invalid_operator_raises(self, case: VerInfo, op: str):
            """Test valid cases for the `parse_min_version` function."""
            ver_text = op + case.to_str()
            with pytest.raises(ValueError, match="Invalid comparison.*"):
                _pyver.PyVerComparison.parse_min_version(ver_text)

        @given(value=non_str())
        def test_non_str_raises(self, value: object):
            """Test that a non-str value passed as the text leads to an
            exception.
            """
            with pytest.raises(TypeError, match=".*was not a str.*"):
                _pyver.PyVerComparison.parse_min_version(
                    value  # type: ignore [arg-type]
                )

    class TestParseMaxVersion:
        """Tests for the `parse_max_version` function."""

        @pytest.mark.parametrize("op", ('<', "<=", None))
        @given(case=VerInfo.instances())
        def test_valid_cases(self, case: VerInfo, op: Union[str, None]):
            """Test valid cases for the `parse_max_version` function."""
            txt = case.to_str()
            ver_text = f"{op}{txt}" if op is not None else txt
            p = _pyver.PyVerComparison.parse_max_version(ver_text)
            if op is not None:
                assert p.operator == op
            else:
                assert p.operator == "<"
            assert p.version == case.version

        @pytest.mark.parametrize("op", ('>', ">="))
        @given(case=VerInfo.instances())
        def test_invalid_operator_raises(self, case: VerInfo, op: str):
            """Test valid cases for the `parse_min_version` function."""
            ver_text = op + case.to_str()
            with pytest.raises(ValueError, match="Invalid comparison.*"):
                _pyver.PyVerComparison.parse_max_version(ver_text)

        @given(value=non_str())
        def test_non_str_raises(self, value: object):
            """Test that a non-str value passed as the text leads to an
            exception.
            """
            with pytest.raises(TypeError, match=".*was not a str.*"):
                _pyver.PyVerComparison.parse_max_version(
                    value  # type: ignore [arg-type]
                )
