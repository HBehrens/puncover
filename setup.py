#!/usr/bin/env python
import os

from setuptools import setup, find_packages, Command

__version__ = None  # Overwritten by executing version.py.
with open("puncover/version.py") as f:
    exec(f.read())


with open('requirements-test.txt') as f:
    tests_require = f.readlines()


class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""

    # http://stackoverflow.com/a/3780822/196350
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system("rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info")


setup(
    name="puncover",
    version=__version__,
    description="Analyses C/C++ build output for code size, static variables, and stack usage.",
    long_description=open("README.rst").read(),
    url="https://github.com/hbehrens/puncover",
    download_url="https://github.com/hbehrens/puncover/tarball/%s" % __version__,
    author="Heiko Behrens",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["puncover = puncover.puncover:main"]},
    install_requires=["Flask==0.10.1"],
    tests_require=tests_require,
    test_suite="nose.collector",
    cmdclass={"clean": CleanCommand,},
)
