[![](https://img.shields.io/badge/GitHub-HBehrens/puncover-8da0cb?style=flat-square&logo=github)](https://github.com/HBehrens/puncover)
[![](https://img.shields.io/github/actions/workflow/status/HBehrens/puncover/ci.yml?style=flat-square&branch=master)](https://github.com/HBehrens/puncover/actions?query=branch%3Amaster+)
[![](https://img.shields.io/codecov/c/github/HBehrens/puncover/master?style=flat-square)](https://codecov.io/gh/HBehrens/puncover)
[![](https://img.shields.io/pypi/v/puncover?style=flat-square)](https://pypi.org/project/puncover)
[![](https://img.shields.io/pypi/pyversions/puncover?style=flat-square)](https://pypi.org/project/puncover)
[![](https://img.shields.io/github/license/HBehrens/puncover?color=blue&style=flat-square)](https://github.com/HBehrens/puncover)

# puncover

![](https://raw.githubusercontent.com/HBehrens/puncover/master/images/overview.png)

Analyzes C/C++ binaries for code size, static variables and stack usages. It
creates a report with disassembler and call-stack analysis per directory, file,
or function.

## Installation and Usage

Install with pip:

```bash
pip install puncover
```

Run it by passing the binary to analyze:

```bash
puncover --elf_file project.elf
...
* Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

Open the link in your browser to view the analysis.

## Running Tests Locally

### Setup

To run the tests locally, you need to install the development dependencies:

1. install pyenv: https://github.com/pyenv/pyenv

   ```bash
   curl https://pyenv.run | bash
   ```

2. install all the python environments, using this bashism (this can take a few
   minutes):

   ```bash
   for _py in $(<.python-version ); do pyenv install ${_py}; done
   ```

3. install the development dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

### Running Tests

Then you can run the tests with:

```bash
tox
```

or, to target only the current `python` on `$PATH`:

```bash
tox -e py
```

## Publishing Release

### Release Script

See `release.sh` for a script that automates the above steps. Requires
[uv](https://github.com/astral-sh/uv) to be installed. This example will work
with the PyPi tokens (now required):

```bash
PUNCOVER_VERSION=0.3.5 TWINE_PASSWORD="<pypi token>" TWINE_USERNAME=__token__ ./release.sh
```

### Manual Steps

Only for reference, the release script should take care of all of this.

<details><summary>Click to expand</summary>

1. Update the version in `puncover/__version__.py`.
2. Commit the version update:

   ```bash
   git add . && git commit -m "Bump version to x.y.z"
   ```

3. Create an annotated tag:

   ```bash
   git tag -a {-m=,}x.y.z
   ```

4. Push the commit and tag:

   ```bash
   git push && git push --tags
   ```

5. Either wait for the GitHub Action to complete and download the release
   artifact for uploading: https://github.com/HBehrens/puncover/actions OR Build
   the package locally: `python setup.py sdist bdist_wheel`

6. Upload the package to PyPI:

   ```bash
   twine upload dist/*
   ```

7. Create GitHub releases:

   - `gh release create --generate-notes x.y.z`
   - attach the artifacts to the release too: `gh release upload x.y.z dist/*`

</details>

## Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.
