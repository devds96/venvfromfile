"""This module contains exceptions used in this package."""


class PyVersionError(Exception):
    """The exception for the case when the Python version of a spec file
    is incompatible with the currently running Python version.
    """
    pass


class UnsupportedArgument(PyVersionError):
    """The exception for the case that a parameter is set in a config,
    but is not supported by the Python version building the virtual
    environment.
    """
    pass


class UseSymlinksException(Exception):
    """The exception for the case that use_symlinks is set to False, but
    is necessary. See `make_config_yaml` in the test_venv_creation.py
    integration test file.
    """
    pass
