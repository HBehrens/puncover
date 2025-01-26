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
puncover project.elf
...
* Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

Open the link in your browser to view the analysis.

You can also use `uvx` to run the script without installing globally:

```bash
uvx puncover project.elf

## Non-intereactive usage

For montitor firmware changes in CI it can be useful to run puncover and get out some numbers. For getting stack usage of some RTOS threads i.e.

```bash
puncover --elf_file ~/zephyrproject/zephyr/samples/modules/lvgl/demos/build/zephyr/zephyr.elf --build_dir ~/zephyrproject/zephyr/samples/modules/lvgl/demos/build/ --generate-report --report-max-static-stack-usage ready_thread --report-max-static-stack-usage shell_thread --report-max-static-stack-usage main --report-max-static-stack-usage unready_thread --report-max-static-stack-usage bg_thread_main --no-interactive
```

## Running Tests Locally

### Setup

To run the tests locally, you need to install the development dependencies. This
project uses `uv` to manage the python environment.

```bash
uv venv && source .venv/bin/activate
uv sync
```

### Running Tests

Then you can run the tests with `tox` (note that this will fail if any of the
supported python versions aren't found, see [`tox.ini`](tox.ini)):

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
PUNCOVER_VERSION=0.3.5 PYPI_TOKEN=<pypi token> ./release.sh
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
