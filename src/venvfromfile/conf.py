"""This module contains the dataclasses which define the structure of
the configuration files.
"""

__all__ = [
    "BaseVenvConfig", "VenvConfigExtraDef", "VenvConfig", "VenvConfigRoot"
]

import dataclasses as _dataclasses
import pydantic as _pydantic
import sys as _sys

# Note that the pydantic dataclass handles the extraneous slots=...
# for Python versions where it is not supported. The argument is just
# ignored. Is this documented somewhere?
from pydantic import field_validator as _field_validator
from pydantic.dataclasses import dataclass as _dataclass
from typing import Dict as _Dict, List as _List, Optional as _Optional, \
    Tuple as _Tuple, Union as _Union

from . import _exceptions
from . import _pyver

from ._pyver import PyVerComparison as _PyVerComparison


_config = _pydantic.ConfigDict(extra="forbid")
"""The pydantic configuration for the dataclasses."""


@_dataclass(frozen=True, config=_config)
class BaseVenvConfig:
    """Encapsulates the "base" parameters, which are the parameters for
    the regular builtin `venv.EnvBuilder`. The fields here are the
    arguments of the constructor of said class.
    """

    system_site_packages: bool = False
    """Whether the system (global) site-packages dir is should be
    available to created environments. Defaults to False."""

    clear: bool = False
    """Whether or not to clear the environment directory if it exists.
    Defaults to False."""

    symlinks: _Optional[bool] = None
    """Whether or not to use symlinks to create the environment, if
    possible. The default is False, if possible and True, otherwise.
    This is because some installations only support the creation of
    virtual environments using symlinks."""

    upgrade: bool = False
    """If True, upgrade an existing virtual environment. Defaults to
    False"""

    with_pip: bool = True
    """Whether or not to install pip in the virtual environment.
    Defaults to True."""

    prompt: _Optional[str] = None
    """Alternative terminal prefix for the environment."""

    upgrade_deps: bool = False
    """Whether or not to update the modules. Defaults to False. Not
    available prior to Python 3.9; setting this to True will result in
    an exception when constructing the virtual environment."""

    def get_base_param_dict(
        self, overrides: _Dict[str, object]
    ) -> _Dict[str, object]:
        """Create a dictionary from this `BaseVenvConfig` instance's
        fields.

        Args:
            overrides (dict[str, object]): A dict of keys and values to
                override the values in the returned dict.

        Returns:
            dict[str, object]: The dictionary of this `BaseVenvConfig`
                instance's fields. This will not contain fields of
                derived classes which `self` may also be an instance of.
                If a key also appears in `overrides` the value therein
                is given in the result insetead of the value on this
                instance.
        """
        fields = _dataclasses.fields(BaseVenvConfig)
        field_names = map(lambda f: f.name, fields)
        result = {
            name: overrides.get(name, getattr(self, name))
            for name in field_names
        }
        return result


@_dataclass(frozen=True, config=_config)
class VenvConfigExtraDef:
    """This class defines additional configuration options such as the
    directory name in which to install the virtual environment. Note
    that all relative paths are interpreted relative to the directory
    containing the config file.
    """

    directory: str
    """The directory in which to install the virtual environment."""

    min_version: _Optional[_PyVerComparison] = None
    """The minimum required Python version for this environment. The
    installation of the environment will be skipped, if an older Python
    version is used. If no comparison operator is specified, this value
    is inclusive."""

    max_version: _Optional[_PyVerComparison] = None
    """The maximum supported Python version for this environment. The
    installation of the environment will be skipped, if a newer Python
    version is used. If no comparison operator is specified, this value
    is exclusive."""

    wheel: bool = False
    """Whether or not to install the wheel package before installing
    the requirements. Defaults to False. Wheel will also be installed
    if no actual dependencies will be installed, for example if
    `install_requirements` is False."""

    install_requirements: bool = True
    """Whether or not to install requirements. Defaults to True."""

    requirement_files: _Optional[_List[str]] = None
    """The list of files from which to install requirements. If unset,
    only the file 'requirements.txt' next to the config file will be
    used, if present. If a file in this list is not present, a
    `FileNotFoundError` is raised when the requirements are
    installed (that is, provided that `install_requirements` is
    True)."""

    upgrade_pip: bool = True
    """Whether to upgrade pip before any requirements are installed.
    Has no effect if `with_pip` is False. Defaults to True."""

    pth_paths: _Optional[_Tuple[str, ...]] = None
    """A list of paths that are added to the site-packages dir in a
    .pth file. Relative paths will be stored as relative paths in the
    .pth file."""

    pth_file: _Optional[str] = None
    """The name of the .pth file. If the file already exists, the
    paths will be appended at the end of the file."""

    pth_newline: str = '\n'
    """The newline character for the .pth file."""

    pth_ignore_existing_duplicates: bool = False
    """Whether to ignore existing duplicate paths in the .pth file and
    write the corresponding paths anyway."""

    pth_lock_file_exclusive: bool = True
    """Whether to lock the .pth file for exclusive access. If it already
    exists, an error occurs. If this is set to False, it might happen
    that multiple processes write to the .pth file concurrently, which
    will corrupt the path information. If this can be ruled out, it will
    be ensured that the new paths are appended to the file correctly."""

    @_field_validator("min_version", mode="before")
    @staticmethod
    def _validate_min_version(
        value: _Union[str, _PyVerComparison]
    ) -> _PyVerComparison:
        """The validator that parses and validates the min_version."""
        if isinstance(value, _PyVerComparison):
            return value
        try:
            return _pyver.PyVerComparison.parse_min_version(value)
        except ValueError:
            raise
        except TypeError as e:
            raise ValueError(f"(from {type(e).__name__}) {str(e)}")

    @_field_validator("max_version", mode="before")
    @staticmethod
    def _validate_max_version(
        value: _Union[str, _PyVerComparison]
    ) -> _PyVerComparison:
        """The validator that parses and validates the max_version."""
        if isinstance(value, _PyVerComparison):
            return value
        try:
            return _pyver.PyVerComparison.parse_max_version(value)
        except ValueError:
            raise
        except TypeError as e:
            raise ValueError(f"(from {type(e).__name__}) {str(e)}")

    def get_pth_file_name(self) -> str:
        """Get the .pth file name to use. Defaults to "<directory>.pth".

        Returns:
            str: The name of the .pth file, including the file ending.
        """
        name = self.pth_file
        if name is not None:
            return name
        return f"{self.directory}.pth"


@_dataclass(frozen=True, config=_config, slots=True)
class VenvConfig(BaseVenvConfig, VenvConfigExtraDef):
    """This class represents entries in the root config. Each entry
    represents a virtual environment that should be built.
    """

    def is_pyversion_compatible(self):
        """Checks if this venv config is compatible with the current
        Python version.

        Returns:
            bool: True, if this config is compatible with the Python
                version and False otherwise.
        """
        miv = self.min_version
        mi_ok = (miv is None) or miv.applies_to_current_pyversion()
        mav = self.max_version
        ma_ok = (mav is None) or mav.applies_to_current_pyversion()
        return mi_ok and ma_ok

    def get_extra_attributes(
        self, overrides: _Dict[str, object]
    ) -> _Dict[str, object]:
        """Create a dictionary from the underyling
        `VenvConfigExtraDef` instance's fields.

        Args:
            overrides (dict[str, object]): A dict of keys and values to
                override the values in the returned dict.

        Returns:
            dict[str, object]: The dictionary of this
                `VenvConfigExtraDef` instance's fields. This will not
                contain fields of derived classes which `self` may also
                be an instance of. If a key also appears in `overrides`
                the value therein is given in the result insetead of the
                value on this instance.
        """
        fields = _dataclasses.fields(VenvConfigExtraDef)
        field_names = map(lambda f: f.name, fields)
        return {
            name: overrides.get(name, getattr(self, name))
            for name in field_names
        }


@_dataclass(frozen=True, config=_config, slots=True)
class VenvConfigRoot:
    """Root class for the configuration."""

    min_version: _Optional[_PyVerComparison] = None
    """The minimum required Python version. If no comparison operator is
    specified, this value is inclusive."""

    max_version: _Optional[_PyVerComparison] = None
    """The maximum supported Python version. If no comparison operator
    is specified, this value is exclusive."""

    venv_configs: _Tuple[VenvConfig, ...] = ()
    """The configurations."""

    @_field_validator("min_version", mode="before")
    @staticmethod
    def _validate_min_version(
        value: _Union[str, _PyVerComparison]
    ) -> _PyVerComparison:
        """The validator that parses and validates the min_version."""
        if isinstance(value, _PyVerComparison):
            return value
        try:
            return _pyver.PyVerComparison.parse_min_version(value)
        except ValueError:
            raise
        except (TypeError,) as e:
            raise ValueError(f"(from {type(e).__name__}) {str(e)}")

    @_field_validator("max_version", mode="before")
    @staticmethod
    def _validate_max_version(
        value: _Union[str, _PyVerComparison]
    ) -> _PyVerComparison:
        """The validator that parses and validates the max_version."""
        if isinstance(value, _PyVerComparison):
            return value
        try:
            return _pyver.PyVerComparison.parse_max_version(value)
        except ValueError:
            raise
        except (TypeError,) as e:
            raise ValueError(f"(from {type(e).__name__}) {str(e)}")

    def ensure_pyversion_compatible(self):
        """Ensure that the virtual environment is compatible with the
        current Python version.

        Raises:
            ValueError: If the version is incompatible.
        """
        current_version = _sys.version_info

        miv = self.min_version
        if (miv is not None) and not miv.applies_to_current_pyversion():
            cv = _pyver.format_version_info(current_version)
            raise _exceptions.PyVersionError(
                "The minimum required Python version for this "
                f"configuration file is {miv}; the current version is {cv}."
            )

        mav = self.max_version
        if (mav is not None) and not mav.applies_to_current_pyversion():
            cv = _pyver.format_version_info(current_version)
            raise _exceptions.PyVersionError(
                "The maximum supported Python version for this "
                f"configuration file is {mav}; the current version is {cv}."
            )
