import pytest

import venvfromfile.__main__ as __main__


class TestCanExecute:
    """Test if various parts of the code can properly execute. These
    tests' main purpose is to alert to incompatibilities in different
    Python versions.
    """

    def test_parse_args(self):
        """Test if the command line argument parser can be set up."""
        with pytest.raises(SystemExit) as se:
            __main__.parse_args(["--version"])
        assert se.value.code == 0

        # Exit code 2 is "incorrect usage". This seems to be hard coded
        # into the ArgumentParser class.
        with pytest.raises(SystemExit) as se:
            __main__.parse_args(["-v"])
        assert se.value.code == 2
        with pytest.raises(SystemExit) as se:
            __main__.parse_args([])
        assert se.value.code == 2

    def test_setup_logging(self):
        """Test that logging can be set up."""
        __main__.setup_logging(False)
        __main__.setup_logging(True)
