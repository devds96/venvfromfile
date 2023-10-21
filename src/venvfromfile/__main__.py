"""This module serves as the entry point for the package."""

import argparse
import logging
import platform
import pydantic
import sys

from typing import Optional, Sequence

from ._dataclasses_portability import dataclass
from ._exceptions import PyVersionError, UnsupportedArgument, \
    UseSymlinksException

from . import __version__, main


DESCRIPTION = """Create a virtual environment from a config file."""


EPILOGUE = """See also the builtin venv package."""


logger = logging.getLogger(__name__)
"""The logger for this module."""


@dataclass(frozen=True, slots=True)
class Args:
    """Encapsualates the command line arguments."""

    conf_file_path: Sequence[str]
    """The path to the configuration file to load."""

    verbose: bool
    """Whether to output verbose information."""


def parse_args(args: Optional[Sequence[str]] = None) -> Args:
    """Parse the command line arguments.

    Args:
        args (Sequence[str], optional): The arguments to parse. Defaults
            to None, which uses the default of
            `ArgumentParser.parse_args`.

    Returns:
        Args: The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        "venvfromfile",
        description=DESCRIPTION,
        epilog=EPILOGUE
    )
    parser.add_argument(
        "conf_file", nargs='+',
        help="A yaml file that contains the config(s)."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="adds additional debug information to the stdout output",
        default=False
    )
    parser.add_argument(
        "--version", action="version", version=f'%(prog)s {__version__}'
    )
    options = parser.parse_args(args)
    return Args(options.conf_file, options.verbose)


def setup_logging(verbose: bool):
    """Set up the default logging when "calling" this package. In normal
    mode, the level is set to INFO and for this level only the text is
    printed. For all levels above INFO, the levelname is prepended so
    that warnings read as "WARNING: ...". In verbose mode, the default
    basic config is used and the level is set to DEBUG.

    Args:
        verbose (bool): Whether to set up verbose logging.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
        return

    class Formatter(logging.Formatter):

        def format(self, record):
            text = super().format(record)

            if record.levelno <= logging.INFO:
                return text

            return "{0}: {1}".format(record.levelname, text)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(Formatter("%(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(console)


_KNOWN_EXCEPTIONS = (
    pydantic.ValidationError,
    UseSymlinksException,
    PyVersionError
)
"""Lists known exceptions for which output of the stack is
suppressed."""


def _main() -> int:
    args = parse_args()
    setup_logging(args.verbose)
    try:
        return main(args.conf_file_path)
    except UnsupportedArgument as ua:
        logger.error(ua)
        logger.error(
            "The current running version is %s.",
            platform.python_version()
        )
        logger.debug('', exc_info=ua)
    except _KNOWN_EXCEPTIONS as e:
        # Supress the stack for known exceptions.
        logger.error(e)
        logger.debug('', exc_info=e)
    except Exception as e:
        logger.error(e, exc_info=e)
    logger.info("Aborting.")
    return -1


if __name__ == "__main__":
    ec = _main()
    if ec is None:
        ec = 0
    exit(ec)
