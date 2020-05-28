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
    long_description_content_type="text/x-rst",
    url="https://github.com/hbehrens/puncover",
    download_url="https://github.com/hbehrens/puncover/tarball/%s" % __version__,
    author="Heiko Behrens",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["puncover = puncover.puncover:main"]},
    install_requires=["Flask==0.10.1"],
    tests_require=tests_require,
    test_suite="nose.collector",
    cmdclass={"clean": CleanCommand,},
    # TODO: https://github.com/HBehrens/puncover/issues/36
    #  Fix Python 3.5
    python_requires=">=3.6",
)
