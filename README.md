# venvfromfile

![Tests](https://github.com/devds96/venvfromfile/actions/workflows/tests.yml/badge.svg)

A simple runnable Python package that sets up virtual environments as
specified in a configuration file using the builtin `venv` module.


## Examples
The configuration files for the construction of virtual environments are
`.yaml` files like the following example (compare `venv_devel.yaml`
in the root directory of this repo):
```
min_version: ">=3.7"
venv_configs:
  - directory: venv@venvfromfile
    requirement_files:
    - requirements.txt
    pth_paths:
    - src
```
This constructs a virtual environment next to the configuration file if
at least Python 3.7 is used. The directory will be named
"venv@venvfromfile" and requirements from a file "requirements.txt"
which should be placed next to the configuration file will be installed
in the virtual environment.
Additionally, a file ".pth" is installed in the virtual environment
containing the path to the directory "src" relative to the configuration
file. This instructs Python to search this path for installed packages
when importing. More information on `.pth` files can be found in the
[documentation of the `site`](https://docs.python.org/3/library/site.html)
module (builtin).

Note that all relative paths specified in the configuration files are
interpreted relative to the configuration file. This includes, for
example the directory names of the virtual environment.

For further information on the available options see the classes
contained in the `conf.py` module and their fields' docstrings.

In order to construct the virtual environment specified by the file
above, the package can be invoked as
```
python -m venvfromfile filename.yaml
```
where `filename.yaml` is the file name of the configuration file.

For further information on available command line options type
```
python -m venvfromfile -h
```

Another simple example:
```
min_version: ">=3.7"
venv_configs:
  - directory: py37
    max_version: "<=3.7"
  - directory: py38_39
    min_version: ">=3.8"
    max_version: "<3.9"
```
This would construct a plain virtual environment without any
requirements in the "py37" directory if Python version 3.7 or below
is used and in the "py38_39" directory if the Python version is above
3.8 and strictly below 3.9. Note that the first comparison will only
hold for Python version 3.7 exactly, since the entire config only
applies to Python versions 3.7 and above.


## Installation
You can install this package directly from git:
```
pip install git+https://github.com/devds96/venvfromfile
```

Alternatively, clone the git repo and run in its root directory:
```
pip install .
```
