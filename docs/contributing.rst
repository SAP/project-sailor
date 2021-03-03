.. _contributing:

============
Contributing
============

Contributions to `project "Sailor" <https://github.com/sap/project-sailor>`__ are warmly welcomed. This page gives you detailed information on steps to take when you want to:

- :ref:`report a bug <reporting_a_bug>`
- :ref:`create a feature request <create_feature_request>`
- :ref:`contribute to the code base <contributing_code>`
- :ref:`contribute to the documentation <contributing_documentation>`


.. _reporting_a_bug:

Report a bug
============
You can report a bug by `creating an issue <https://docs.github.com/en/github/managing-your-work-on-github/creating-an-issue>`__ in the `project repository <https://github.com/SAP/project-sailor>`__.
Ideally your report should include:

- short self-contained example or code snippet how to reproduce the bug
- description of the current behaviour and what is wrong with it
- description of the desired behavior, depicting how the code is expected to work

.. _create_feature_request:

Create a feature request
========================
You can request a feature by `creating an issue <https://docs.github.com/en/github/managing-your-work-on-github/creating-an-issue>`__ in the `project repository <https://github.com/SAP/project-sailor>`__.
Alternatively you can get in touch with the developers directly by reaching out to `project.sailor@sap.com <mailto:project.sailor@sap.com>`__


.. _contributing_code:

Contributing to the code base
=============================

Getting started
---------------
This section will give you the minimum requirements to starting development with project "Sailor".

Prerequisites
~~~~~~~~~~~~~
You have cloned the Github project. Every instruction assumes that you are currently in the project folder on your development machine. 

Ideally you have created a dedicated python environment for development with "Sailor". Please check the classifiers in ``setup.py`` for the currently supported python versions and use the most recent eligible version.


Installation
~~~~~~~~~~~~~
Install the dependencies by running:

.. code-block::

    pip install -r requirements.txt

Install the "Sailor" sources

.. code-block::

    pip install -e .



Additional tooling
------------------
This section describes how we support additonal use cases that may occur during development.

Dev tools
~~~~~~~~~
Install all tools required for testing and linting by running:

.. code-block::

    pip install -r .ci/requirements_ci.txt

Find the current settings and/or possible instructions to run linting/testing tools in ``setup.cfg``.


Requirements management
~~~~~~~~~~~~~~~~~~~~~~~
**requirements.txt** lists the concrete dependencies that our code is meant to be tested for. This file should never be modified manually, only through :code:`pip-compile` (see below).

**requirements.in** lists abstract dependencies.  If you would like to introduce a new package as dependency to this project:

1. please add it to **requirements.in** and run :code:`pip-compile` to update the requirements.txt
2. Add the resulting changes to your next pull request.

*pip-compile* is part of package *pip-tools* (can be installed via pip).


Building the package
~~~~~~~~~~~~~~~~~~~~
We are using a PEP517 and PEP518 compliant build tooling.

To build the project simply run:

.. code-block::

    python -m build


.. _contributing_documentation:

Contributing to the documentation
=================================
`Sphinx <https://www.sphinx-doc.org/en/master/>`__ is used to build the documentation.
All documentation files are written in `reStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`__
and can be found in the :code:`docs` folder.

Requirements
------------
You will need to install Sphinx and dependencies that we use. This can be done via pip:

.. code-block::

    pip install -r .ci/docs/requirements_docs.txt

Build
-----
Go to the :code:`docs` directory and run:

.. code-block::

    make html


The HTML is built into the :code:`docs/_build` directory. You can view the docs by simply opening **index.html** with your browser.

If you just ran ``make html`` for the **first time**, it might be that the documentation is not rendered properly (specifically the TOC for the API documentation on the left).
In this case please run once:

.. code-block::

    touch apidoc.rst
    make html SPHINXOPTS="-a"

Further builds should only require ``make html``.



Adding or removing API doc pages
--------------------------------
This step is only required when new modules/packages have been added or removed.
If you want to update the apidoc:

1. run: :code:`make apidoc`
2. (only if any packages/modules have been removed): delete the corresponding .rst files
3. commit the changes