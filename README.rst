
.. image:: https://img.shields.io/badge/GitHub-HBehrens/puncover-8da0cb?style=flat-square&logo=github
   :alt: GitHub Link
   :target: https://github.com/HBehrens/puncover

.. image:: https://img.shields.io/github/workflow/status/HBehrens/puncover/Python%20package/master?style=flat-square
   :alt: GitHub Workflow Status (branch)
   :target: https://github.com/HBehrens/puncover/actions?query=branch%3Amaster+

.. image:: https://img.shields.io/codecov/c/github/HBehrens/puncover/master?style=flat-square
   :alt: Codecov branch
   :target: https://codecov.io/gh/HBehrens/puncover

.. image:: https://img.shields.io/pypi/v/puncover?style=flat-square
   :alt: PyPI
   :target: https://pypi.org/project/puncover

.. image:: https://img.shields.io/pypi/pyversions/puncover?style=flat-square
   :alt: PyPI - Python Version
   :target: https://pypi.org/project/puncover

.. image:: https://img.shields.io/github/license/HBehrens/puncover?color=blue&style=flat-square
   :alt: License - MIT
   :target: https://github.com/HBehrens/puncover

puncover
========

.. image:: https://raw.githubusercontent.com/HBehrens/puncover/master/images/overview.png

Analyzes C/C++ binaries for code size, static variables and stack usages. It
creates a report with disassembler and call-stack analysis per directory, file,
or function.

Installation and Usage
----------------------

Install with pip:

.. code-block:: bash

   pip install puncover

Run it by passing the binary to analyze:

.. code-block:: bash

   puncover --elf_file project.elf
   ...
   * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)

Open the link in your browser to view the analysis.

Running Tests Locally
---------------------

To run the tests locally, you need to install the development dependencies:

1. install pyenv: https://github.com/pyenv/pyenv

   ..  code-block:: bash

         curl https://pyenv.run | bash

2. install all the python environments, using this bashism (this can take a few
   minutes):

   ..  code-block:: bash

         for _py in $(<.python-version ); do pyenv install ${_py}; done

3. install the development dependencies:

   ..  code-block:: bash

      pip install -r requirements-dev.txt


Then you can run the tests with:

..  code-block:: bash

   tox
