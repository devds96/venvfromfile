"""This module can be run to create a virtual environment (venv) from a
config file.
"""

__all__ = [
    "EnvBuilder", "EnvContext",
    "BaseVenvConfig", "VenvConfig", "VenvConfigExtraDef", "VenvConfigRoot",
    "PyVersionError", "UnsupportedArgument", "UseSymlinksException"
]

__author__ = "devds96"
__email__ = "src.devds96@gmail.com"
__license__ = "MIT"
__version__ = "0.1.0"

import logging as _logging
import os.path as _ospath
import pydantic_yaml as _pydantic_yaml
import sys as _sys

if _sys.version_info >= (3, 8):
    from typing import Literal as _Literal
else:
    from typing_extensions import Literal as _Literal  # type: ignore [assignment] # noqa: E501

from typing import List as _List, Optional as _Optional, \
    overload as _overload, Sequence as _Sequence, Tuple as _Tuple, \
    Union as _Union

from . import _pyver

from .builder import EnvBuilder, EnvContext
from .conf import BaseVenvConfig, VenvConfig, VenvConfigExtraDef, \
    VenvConfigRoot
from ._exceptions import PyVersionError, UnsupportedArgument, \
    UseSymlinksException


_logger = _logging.getLogger(__name__)
"""The logger for this module."""


def load_conf_from_file(path: str) -> VenvConfigRoot:
    """Load the configuration root from a file.

    Args:
        path (str): The file to load.

    Returns:
        VenvConfigRoot: The loaded config root.
    """
    res = _pydantic_yaml.parse_yaml_file_as(  # type: ignore [type-var]
        VenvConfigRoot, path
    )
    _logger.debug("The deserialized config root is %s", res)
    return res


def build_conf(conf_path: str, conf: VenvConfig) -> EnvBuilder:
    """Build the config specified by a file.

    Args:
        conf_path (str): The path to the config file.
        conf (VenvConfig): The configuration.

    Returns:
        builder.EnvBuilder: The builder after the construction
            completes.
    """
    _logger.info(f"Building environment {conf.directory!r}.")
    _logger.debug(f"Building from config {conf!r}.")
    b = EnvBuilder(conf_path, conf)
    b.create(conf.directory)
    return b


@_overload
def main(
    conf_file_paths: _Sequence[str],
    *,
    ret_builders: _Optional[_Literal[False]] = None
) -> int:
    pass


@_overload
def main(
    conf_file_paths: _Sequence[str],
    *,
    ret_builders: _Literal[True]
) -> _Tuple[int, _Sequence[EnvBuilder]]:
    pass


def main(
    conf_file_paths: _Sequence[str],
    *,
    ret_builders: _Optional[bool] = None
) -> _Union[int, _Tuple[int, _Sequence[EnvBuilder]]]:
    """The main entry point for the construction of virtual environments
    based on configuration data.

    Args:
        conf_file_paths (_Sequence[str]): The paths to the configuration
            files.
        ret_builders (Optional[bool], optional): Whether or not to
            return the used `EnvBuilder` instances. Defaults to False.

    Raises:
        TypeError: If `conf_file_paths` is a str instance instead of a
            Sequence[str].

    Returns:
        int | tuple[int, Sequence[EnvBuilder]]]: The return code (0) or
            the return code followed by a Sequence[EnvBuilder]
            representing the used environment builders.
    """

    if isinstance(conf_file_paths, str):
        # This prevents typos.
        raise TypeError(
            "'conf_file_paths' was of type str. Expected Sequence[str]."
        )

    builders: _List[EnvBuilder] = list()

    for sf in conf_file_paths:
        if not _ospath.isabs(sf):
            sf = _ospath.abspath(sf)
        _logger.info(f"Loading configuration file {sf!r}.")
        conf = load_conf_from_file(sf)
        try:
            conf.ensure_pyversion_compatible()
        except PyVersionError as pve:
            _logger.warning(pve)
            _logger.warning("Skipping this config file.")
            continue

        cv = _sys.version_info

        for i, venv_config in enumerate(conf.venv_configs):
            dir_name = venv_config.directory
            if not venv_config.is_pyversion_compatible():
                cver = _pyver.format_version_info(
                    cv  # type: ignore [arg-type]
                )
                _logger.info(
                    f"The environment at index {i} with directory "
                    f"{dir_name!r} is incompatible with the "
                    "current Python version "
                    f"({cver}) and will be skipped."
                )
                continue
            b = build_conf(sf, venv_config)
            builders.append(b)

    num_ok = len(builders)
    if num_ok > 0:
        s = "s have" if num_ok > 1 else " has"
        _logger.info(
            f"{num_ok} compatible virtual environment{s} been set up."
        )
    else:
        _logger.warning("No virtual environments have been set up.")

    if ret_builders is True:
        return 0, tuple(builders)
    return 0
