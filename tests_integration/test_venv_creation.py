import pytest
import functools
import itertools
import os
import os.path as ospath
import subprocess
import sys
import venv

from contextlib import contextmanager
from dataclasses import dataclass, field
from pytest import FixtureRequest
from typing import Dict, Iterable, Optional, Union

from helper.temporary_helper import temp_dir
from helper.find_repo import REPO_LOCATION

import venvfromfile.__main__ as __main__
import venvfromfile._exceptions as _exceptions


REQUIREMENTS = (
    "pip-install-test==0.5",
    "typing_extensions;python_version<\"3.11\""
)
"""The requirements file line referring to the test package. See
https://pypi.org/project/pip-install-test/. typing_extensions is
required to import the _dataclasses_portability module."""


def make_config_yaml(
    directory: str,
    requirement_files: Iterable[str],
    pth_paths: Iterable[str],
    *,
    upgrade_deps: Optional[bool] = None
) -> str:
    """Construct the config file in yaml.

    Args:
        directory (str): The name of the directory for the venv.
        requirement_files (Iterable[str]): The requirement files.
        pth_paths (Iterable[str]): The .pth paths.
        upgrade_deps (bool, optional): The value to add for the
            'upgrade_deps' parameter. Defaults to None, which does not
            add this parameter.

    Returns:
        str: The text for the config file.
    """
    script = f"venv_configs:{os.linesep}  - directory: {directory}"
    if hasattr(venv, "should_use_symlinks"):
        # On MacOS symlinks might be required sometimes.
        should_use_symlinks: bool = venv.should_use_symlinks()
        if should_use_symlinks:
            script += f"{os.linesep}    symlinks: true"
    if upgrade_deps is not None:
        script += f"{os.linesep}    upgrade_deps: {str(upgrade_deps).lower()}"
    enum = f"{os.linesep}    - "
    req_text = enum.join(requirement_files)
    if req_text != '':
        script += f"{os.linesep}    requirement_files:"
        script += enum + req_text
    pth_text = enum.join(pth_paths)
    if pth_text != '':
        script += f"{os.linesep}    pth_paths:"
        script += enum + pth_text
    return script


@dataclass(eq=False, order=False, frozen=True)
class VenvHandle:
    """A handle for a virtual environment."""

    config: str
    """The text of the config file."""

    requirements_file_content: str
    """The text of the requirements file."""

    parent_dir: str
    """The directory containing the """

    config_path: str
    """The path to the config file."""

    dir_path: str
    """The path to the venv directory."""

    exists: bool = field(init=False, default=False)
    """Whether the venv has been set up."""

    env_exe: Union[str, None] = field(init=False, default=None)
    """The path to the Python executable in the venv."""

    def setup(self):
        """Construct the virtual environment.

        Raises:
            RuntimeError: If the virtual environment was already
                constructed.
        """
        if self.exists:
            raise RuntimeError(f"The venv already exists. {self!r}")
        # This could technically also be done with a check_call.
        __main__.setup_logging(True)
        ec, builders = __main__.main((self.config_path,), ret_builders=True)
        assert ec == 0, self
        object.__setattr__(self, "exists", True)
        assert len(builders) == 1
        builder = builders[0]
        context = builder.ensure_directories(self.dir_path)
        env_exe = context.env_exe
        object.__setattr__(self, "env_exe", env_exe)

    def run_env_python(self, cmd: Iterable[str]):
        """Run a Python command in the virtual environment.

        Args:
            cmd (Iterable[str]): The command.

        Raises:
            RuntimeError: If the venv was not yet constructed by calling
                `setup`.
        """
        if not self.exists:
            raise RuntimeError(f"The venv was not created yet. {self!r}")
        env_exe = self.env_exe
        if env_exe is None:
            raise AssertionError(
                "Could not determine the path to the environment "
                "executable."
            )
        cmd_w_exe = itertools.chain((env_exe,), cmd)
        proc_res: subprocess.CompletedProcess[str] = subprocess.run(
            cmd_w_exe, capture_output=True, universal_newlines=True
        )  # type: ignore [call-overload]
        rc = proc_res.returncode
        if rc != 0:
            msg = (
                f"Command {cmd!r} returned non-zero exit status {rc}. "
                f"stdout: {proc_res.stdout!r}, stderr: {proc_res.stderr!r}"
            )
            raise AssertionError(msg)


@contextmanager
def prepare_venv_handle(
    config_file_name: str,
    dirname: str,
    requirements_file_name: str,
    requirements: Iterable[str],
    pth_paths: Iterable[str],
    *,
    upgrade_deps: Optional[bool] = None
):
    """Prepare a virtual environment for construction in a temporary
    directory.

    Args:
        config_file_name (str): The name of the config file.
        dirname (str): The name of the directory containing the venv.
        requirements_file_name (str): The name of the requirements file.
        requirements (Iterable[str]): The requirement file lines.
        pth_paths (Iterable[str]): The .pth file lines.
        pth_paths (Iterable[str]): The .pth paths.
        upgrade_deps (bool, optional): The value to add for the
            'upgrade_deps' parameter. Defaults to None, which does not
            add this parameter.

    Raises:
        TypeError: If `str`s are provided instead of `Iterable[str]`s
            for `requirements` or `pth_paths`; this prevents a typo.

    Yields:
        VenvHandle: The handle for the venv.
    """
    # These two checks prevent typos.
    if isinstance(requirements, str):
        raise TypeError("'requirements' was a str.")
    if isinstance(pth_paths, str):
        raise TypeError("'pth_paths' was a str.")
    with temp_dir() as tdir:
        in_tdir = functools.partial(ospath.join, tdir)

        req = os.linesep.join(requirements)
        with open(in_tdir(requirements_file_name), "w") as ofi:
            ofi.write(req)

        config_text = make_config_yaml(
            dirname, [requirements_file_name], pth_paths,
            upgrade_deps=upgrade_deps
        )
        config_path = in_tdir(config_file_name)
        with open(config_path, "w") as ofi:
            ofi.writelines(config_text)

        venv_path = ospath.join(tdir, dirname)
        yield VenvHandle(
            config_text, req, tdir, config_path, venv_path
        )


@contextmanager
def venv_handle_create(
    *,
    upgrade_deps: Optional[bool] = None
):
    """Construct the default venv for tests.

    Yields:
        VenvHandle: The handle to the created venv.
    """
    pth_test_path = ospath.join(
        REPO_LOCATION, "src", "venvfromfile"
    )

    with prepare_venv_handle(
        "spec.yaml", "venv", "requirements.txt", REQUIREMENTS,
        (pth_test_path,), upgrade_deps=upgrade_deps
    ) as handle:
        try:
            handle.setup()
        except subprocess.CalledProcessError as cpe:
            # If for example pip install fails, we also need the stdout
            # and stderr. However, when the exception is actually
            # printed by pytest, it seems that part of it is removed.
            # Therefore, we print some more info here.
            print("Additional info:", file=sys.stderr)

            def form(data: Union[str, bytes]) -> str:
                if isinstance(data, str):
                    return data
                if isinstance(data, bytes):
                    try:
                        return data.decode()
                    except Exception as ue:
                        print(
                            "! Could not decode: "
                            f"{ue.__class__.__qualname__}: {ue}",
                            file=sys.stderr
                        )
                        pass
                return repr(data)

            print('*' * 10, "stderr", '*' * 10, file=sys.stderr)
            print(form(cpe.stderr), file=sys.stderr)
            print('*' * 10, "stdout", '*' * 10, file=sys.stderr)
            print(form(cpe.stdout), file=sys.stderr)

            raise

        yield handle


@pytest.fixture(scope="class")
def venv_handle(request: FixtureRequest):
    """Construct the venv for tests.

    Yields:
        VenvHandle: The handle to the created venv.
    """
    kwargs: Dict[str, object] = dict()
    parameters = ("upgrade_deps",)
    if hasattr(request, "param"):
        param: Dict[str, object] = request.param
        for p in parameters:
            try:
                kwargs[p] = param[p]
            except KeyError:
                pass
    with venv_handle_create(**kwargs) as vh:  # type: ignore [arg-type]
        yield vh


_IMPORTABLE_SUBMODULES = (
    "_collection_util", "_dataclasses_portability", "_exceptions",
    "_io_util", "_path_util"
)
"""These are the importable submodules of the venvfromfile package.
These are all modules which do not use relative imports."""


class TestBasicVenvCreation:
    """Test the create of a virtual environment."""

    def test_import(self, venv_handle: VenvHandle):
        """Attempt to import the pip_install_test module which has been
        installed in the new venv as a requirement.
        """
        try:
            venv_handle.run_env_python(["-c", "import pip_install_test"])
        except AssertionError as ae:
            raise AssertionError(
                "Could not import pip_install_test module."
            ) from ae

    @pytest.mark.parametrize("which", _IMPORTABLE_SUBMODULES)
    def test_import_inner_modules(
        self,
        venv_handle: VenvHandle,
        which: str
    ):
        """Attempt to import certain submodules from the venvfromfile
        package which are only importable since the package as it is in
        this repo was added as a .pth path (the imported package is not
        the one which is installed in the venv).
        """
        try:
            venv_handle.run_env_python(["-c", f"import {which}"])
        except AssertionError as ae:
            raise AssertionError(
                f"Could not import module {which!r}."
            ) from ae


class TestUpgradeDeps:
    """Tests regarding the upgrade_deps parameter."""

    @pytest.mark.skipif(
        sys.version_info < (3, 9),
        reason="upgrade_deps requires Python 3.9"
    )
    @pytest.mark.parametrize(
        "venv_handle", (dict(upgrade_deps=True),), indirect=True
    )
    class TestCreation(TestBasicVenvCreation):
        """Test the creation of the virtual environments."""

        def test_meta_has_upgrade_deps(self, venv_handle: VenvHandle):
            """Ensure that the 'upgrade_deps' parameter is enabled in
            the venv convig. This serves as a "meta-test".
            """
            assert "upgrade_deps: true" in venv_handle.config

        def test_import(self, venv_handle: VenvHandle):
            """Attempt to import the pip_install_test module which has
            been installed in the new venv as a requirement.
            """
            super().test_import(venv_handle)

        @pytest.mark.parametrize("which", _IMPORTABLE_SUBMODULES)
        def test_import_inner_modules(
            self, venv_handle: VenvHandle, which: str
        ):
            """Attempt to import certain submodules from the
            venvfromfile package which are only importable since the
            package as it is in this repo was added as a .pth path (the
            imported package is not the one which is installed in the
            venv).
            """
            super().test_import_inner_modules(venv_handle, which)

    @pytest.mark.skipif(
        sys.version_info >= (3, 9),
        reason="upgrade_deps available above Python 3.9"
    )
    class TestRaisesBelow39:
        """Test that setting upgrade_deps to True below Python 3.9 leads
        to and exception.
        """

        def test_raises_below_39(self):
            """Test that setting upgrade_deps to True below Python 3.9
            leads to and exception.
            """
            with pytest.raises(
                _exceptions.UnsupportedArgument, match=".*upgrade_deps.*"
            ):
                # The call should raise.
                with venv_handle_create(upgrade_deps=True) as _:
                    pass
