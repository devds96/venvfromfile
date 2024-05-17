"""This module contains the builder class which constructs the virtual
environments. This class is a subclass of the builtin `venv.EnvBuilder`.
"""

__all__ = ["EnvContext", "EnvBuilder"]

import ast as _ast
import dataclasses as _dataclasses
import functools as _functools
import io as _io
import logging as _logging
import os.path as _ospath
import subprocess as _subprocess
import sys as _sys
import venv as _venv

from os import PathLike as _PathLike
from types import SimpleNamespace as _SimpleNamespace
from typing import ClassVar as _ClassVar, Dict as _Dict, \
    Iterable as _Iterable, List as _List, Sequence as _Sequence, \
    Tuple as _Tuple, Union as _Union

from . import _collection_util
from . import conf as _conf
from . import _exceptions
from . import _io_util
from . import _path_util

from ._dataclasses_portability import dataclass as _dataclass


_logger = _logging.getLogger(__name__)
"""The logger of this module."""


@_dataclass(eq=False, order=False, frozen=True, slots=True)
class EnvContext:
    """Represents a context describing a created virtual environment.
    https://docs.python.org/3/library/venv.html#venv.EnvBuilder.ensure_directories
    """

    _PIP_INSTALL: _ClassVar = ("-m", "pip", "install")
    """The command for 'pip install' as it would be supplied to the
    Python executable."""

    _FIND_SITE_CMD = (
        "-c",
        "import site; print(site.getsitepackages())"
    )
    """The command to execute to obtain the site dir path from the
    Python executable."""

    env_exe: str
    """The name of the Python interpreter in the virtual environment."""

    def python_m_pip_install(self, pkg_or_args: _Union[str, _Iterable[str]]):
        """Invoke a "pip install" command.

        Args:
            pkg_or_args (str | Iterable[str]): The package name or the
                arguments to pass to the install command.

        Raises:
            TypeError: If `pkg_or_args` is not a str or an iterable.
        """
        args: _Tuple[str, ...]
        if isinstance(pkg_or_args, str):
            _logger.debug(f"'_pip_install' called with str {pkg_or_args!r}.")
            args = (pkg_or_args,)
        elif isinstance(pkg_or_args, _Iterable):
            args = tuple(pkg_or_args)
            _logger.debug(
                f"'_pip_install' called with iterable. As tuple: {args!r}."
            )
        else:
            raise TypeError(
                f"'pkg_or_args' was of type {type(pkg_or_args)!r}."
            )

        ccargs = (self.env_exe,) + self._PIP_INSTALL + args
        _logger.debug(f"Performing pip install with command {ccargs!r}.")
        _logger.info("Launching pip to install dependencies.")
        _subprocess.check_call(ccargs, text=True)

    def find_site_dir(self) -> str:
        """Resolve the site directory of the created virtual
        environment.

        Raises:
            ValueError: If the command for determining the site dir path
                returns an unexpected object or an empt list.

        Returns:
            str: The path to the site directory of the created
                environment.
        """
        cmd = (self.env_exe,) + self._FIND_SITE_CMD
        output = _subprocess.check_output(cmd, text=True).strip()
        plist = _ast.literal_eval(output)
        _logger.debug(f"Got object {plist!r} from site cmd.")
        if not isinstance(plist, list):
            raise ValueError("The command did not produce a list.")
        if len(plist) == 0:
            raise ValueError("Cannot determine site packages directory.")
        res = plist[0]
        return res

    @classmethod
    def from_SimpleNamespace(cls, context: _SimpleNamespace) -> "EnvContext":
        """Construct the environment context from the `SimpleNamespace`
        instance provided by the base `EnvBuilder` class.

        Args:
            context (SimpleNamespace): The context describing the
                created virtual environment.

        Raises:
            AttributeError: If a field of this class cannot be found at
                the provided `SimpleNamespace`.

        Returns:
            EnvContext: The constructed instance describing the created
                virtual environment.
        """

        def get_items(field: _dataclasses.Field) -> _Tuple[str, object]:
            name = field.name
            try:
                value = getattr(context, name)
            except AttributeError:
                raise AttributeError(
                    "The virtual environment context did not provide a "
                    f"{name!r} field."
                )
            if not isinstance(value, field.type):
                raise TypeError(
                    "The virtual environment context did not provide the "
                    f"correct type for the value of the {name!r} field. "
                    f"Expected type {field.type!r}, got instance {value!r}."
                )
            return name, value

        kwargs = {
            name: v for name, v in map(get_items, _dataclasses.fields(cls))
        }

        _logger.debug(
            "Constructing an instance of %s from kwargs %r",
            cls.__qualname__, kwargs
        )

        return cls(**kwargs)  # type: ignore [arg-type]


class EnvBuilder(_venv.EnvBuilder, _conf.VenvConfigExtraDef):
    """The builder for the environment, based on the standard library
    builder. This class also derives from the config def class to
    inherit its fields. These are copied from the passed config at the
    constructor.
    """

    _REQUIREMENTS_TXT = "requirements.txt"

    def __init__(self, conf_path: str, conf: _conf.VenvConfig):
        """Create a new `EnvBuilder` for the construction of virtual
        environments.

        Args:
            conf_path (str): The path to the configuration path.
            conf (VenvConfig): The configuration for the virtual
                environment.

        Raises:
            UseSymlinksException: If the current Python version does not
                support the creation of virtual environments without
                using symlink, but this is requested in the
                configuration.
            UnsupportedArgument: If parameters are specified in `conf`
                which are not supported by the current Python version.
        """
        # Collect overrides for certain fields.
        overrides: _Dict[str, object] = dict()

        # See test_venv_creation.py and help(UseSymlinksException)
        if hasattr(_venv, "should_use_symlinks"):
            if _venv.should_use_symlinks(None):  # "if required"
                does = conf.symlinks
                if does is False:
                    raise _exceptions.UseSymlinksException(
                        "This version of Python does not support creating "
                        "virtual environments without using symlinks."
                    )
                elif does is None:
                    overrides["symlinks"] = True

        self.conf_dir = _ospath.dirname(conf_path)
        for k, v in conf.get_extra_attributes(overrides).items():
            object.__setattr__(self, k, v)

        kwargs = conf.get_base_param_dict(overrides)

        if _sys.version_info <= (3, 9):
            if conf.upgrade_deps is not False:
                raise _exceptions.UnsupportedArgument(
                    "'upgrade_deps' is only available starting from "
                    "Python 3.9. The parameter was set to "
                    f"{conf.upgrade_deps!r}."
                )
            # The field will be missing in the superclass.
            del kwargs["upgrade_deps"]

        super().__init__(**kwargs)  # type: ignore [arg-type]

    def create(self, env_dir: _Union[str, bytes, _PathLike]):
        """The function called in order to create the virtual
        environment.

        Args:
            env_dir (Union[str, bytes, PathLike]): The directory in
                which to create the virtual environment.
        """
        env_dir = _path_util.to_str_path(env_dir)
        if not _ospath.isabs(env_dir):
            env_dir = self._resolve_rel_path(env_dir)
        return super().create(env_dir)

    def post_setup(self, context: _SimpleNamespace):
        """Hook for post-setup modification of the venv.

        Args:
            context (SimpleNamespace): The context describing the
                created virtual environment.
        """
        super_res = super().post_setup(context)
        env_context = EnvContext.from_SimpleNamespace(context)

        if self.with_pip:
            if self.upgrade_pip:
                self._upgrade_pip(env_context)
            if self.wheel:
                self._install_wheel(env_context)
            if self.install_requirements:
                self._install_requirements(env_context)
            else:
                _logger.info(
                    "Skipping installation of requirements as requested."
                )
        else:
            _logger.info(
                "Skipping installation of requirements since 'pip' was "
                "not installed."
            )

        self._install_pth(env_context)

        return super_res

    def _resolve_rel_path(self, path: str) -> str:
        """Resolve a relative path relative to the directory containing
        the configuration file.

        Args:
            path (str): The path to resolve.

        Returns:
            str: The absolute path, that is, `path` relative to the
                directory containing the config file.
        """
        return _path_util.resolve_rel_path(self.conf_dir, path)

    def _remove_existing_pth_paths(
        self,
        site_dir_path: str,
        ifi: _io.BufferedRandom,
        paths: _Iterable[str]
    ) -> _Sequence[str]:
        """Remove existing .pth paths from the list of paths to install.

        Args:
            site_dir_path (str): The path to the site dir. Required to
                resolve absolute paths.
            ifi (BufferedRandom): The raw buffer of the .pth file.
            paths (Iterable[str]): The iterable of paths to install.

        Returns:
            Sequence[str]: The remaining paths to install, i.e. those of
                `paths` which are not already installed.
        """
        absify = _functools.partial(_ospath.join, site_dir_path)

        new_abs_paths = [(p, _path_util.norm_fully(absify(p))) for p in paths]

        def filter_non_paths(paths: _Iterable[str]):
            for p in paths:
                try:
                    yield _path_util.norm_fully(absify(p.rstrip("\n\r")))
                except Exception as e:
                    # The line may be code or something else that is
                    # not a path. We just ignore that since we are only
                    # interested in duplicates anyway.
                    _logger.debug(
                        "Exception with path %r", p, exc_info=e
                    )
                    continue

        ifi.seek(0, _io.SEEK_SET)
        text_ifi = _io.TextIOWrapper(ifi)
        ex_paths = filter_non_paths(text_ifi)
        result = _collection_util.filter_existing(
            new_abs_paths, ex_paths, conv=lambda k: k[1]
        )
        text_ifi.detach()

        return [k[0] for k in result]

    def _install_pth(self, context: EnvContext):
        """Install the .pth paths if necessary.

        Args:
            context (EnvContext): The context describing the created
                virtual environment.
        """
        pths = self.pth_paths
        if (pths is None) or (len(pths) == 0):
            _logger.debug(
                "No .pth paths specified. Skipping installation."
            )
            return

        _logger.info("Setting up .pth file...")
        site_dir = context.find_site_dir()

        def sanitize_path(p: str) -> str:
            if not _ospath.isabs(p):
                p = self._resolve_rel_path(p)
                p = _ospath.relpath(p, site_dir)
            _logger.debug(f"Resolved pth path {p!r}")
            return p

        paths: _Iterable[str] = map(sanitize_path, pths)
        pth_file_name = self.get_pth_file_name()
        _logger.debug(f".pth file name: {pth_file_name}")
        file = _ospath.join(site_dir, pth_file_name)

        if self.pth_lock_file_exclusive:
            open_cmd = "x+b"
        else:
            open_cmd = "a+b"

        ofi: _io.BufferedRandom
        with open(file, open_cmd) as ofi:  # type: ignore [assignment]
            if not self.pth_ignore_existing_duplicates:
                # Remove duplicates.
                paths = self._remove_existing_pth_paths(
                    site_dir, ofi, paths
                )

                lp = len(paths)
                _logger.info(
                    "After removing duplicates, %s .pth path%s "
                    "remain%s to be installed.",
                    "no" if lp == 0 else str(lp),
                    's' if lp != 1 else '',
                    's' if lp == 1 else ''
                )
                if lp == 0:
                    return

            _logger.debug(f"Writing (to) .pth file {file!r}")
            _io_util.append_lines_on_new_line(
                ofi, paths, linesep=self.pth_newline
            )

        _logger.info("Completed.")

    def _install_requirements(self, context: EnvContext):
        """Install the requirements from the requirement file(s).

        Args:
            context (EnvContext): The context describing the created
                virtual environment.

        Raises:
            FileNotFoundError: If a requirements file cannot be found.
        """
        rqfs = self.requirement_files
        abs_paths: _Sequence[str]
        if rqfs is None:
            rqf_rel = self._REQUIREMENTS_TXT
            rqf = self._resolve_rel_path(rqf_rel)
            if not _ospath.isfile(rqf):
                _logger.info(
                    f"No {rqf_rel!r} found. Skipping installation."
                )
                return
            abs_paths = (rqf,)
        else:
            if len(rqfs) == 0:
                _logger.info("No requirement files given.")
                return
            labs_paths: _List[str] = list()
            for path in rqfs:
                if not _ospath.isabs(path):
                    path = self._resolve_rel_path(path)
                if not _ospath.isfile(path):
                    _logger.warning(
                        f"The requirements file {path!r} was not found."
                    )
                    continue
                labs_paths.append(path)
            abs_paths = tuple(labs_paths)

        if len(abs_paths) == 0:
            _logger.info("No requirement files remain.")
            return

        cmd_parts = [s for path in abs_paths for s in ("-r", path)]

        _logger.info("Installing requirements...")
        context.python_m_pip_install(tuple(cmd_parts))
        _logger.info("Requirements installed.")

    def _install_wheel(self, context: EnvContext):
        """Install the wheel package to the virtual environment.

        Args:
            context (EnvContext): The context describing the created
                virtual environment.
        """
        _logger.info("Installing wheel...")
        context.python_m_pip_install("wheel")
        _logger.info("wheel installed.")

    def _upgrade_pip(self, context: EnvContext):
        """Upgrade pip in the virtual environment.

        Args:
            context (EnvContext): The context describing the created
                virtual environment.
        """
        _logger.info("Upgrading pip...")
        context.python_m_pip_install(("--upgrade", "pip"))
        _logger.info("pip upgraded...")
