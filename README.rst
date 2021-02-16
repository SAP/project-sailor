==============
Project Sailor
==============

.. inclusion-marker-do-not-remove

README needs to be updated. You can find the link to the guidelines in our Wiki.

**TODO**: Put **DESCRIPTION** here.

- what is it?
- why does it exist?


Requirements
============

**TODO**: This section should describe the requirements, hardware and software, that are used with your sample code. This section should list any expected SAP software that is necessary to run this sample code, if applicable. Also include any other requirements that are necessary (or optional) to use this project.
Any external requirements must be hyperlinked to the site where that software, or that documentation, can be found.


Installation
============

Install the package with pip

.. code-block::

   pip install sailor


Configuration
=============

Sailor talks to two services: Asset Central and SAP IoT.
You have two options of specifying the configuration:

1. `Environment`_
2. `YAML file`_

The above order is honoured when Sailor checks for the configuration.


Environment
-----------
A JSON string can be provided with the environment variable SAILOR_CONFIG_JSON. Example:

.. code-block:: python

    os.environ['SAILOR_CONFIG_JSON'] = json.dumps({
        'asset_central': {
            'client_id': 'ACexampleId',
            'client_secret': 'ACexampleSecret',
            'application_url': 'https://asset-central.com',
            'subdomain': 'account-name'
        },
        'sap_iot': {
            'client_id': 'IoTexampleId',
            'client_secret': 'IoTexampleSecret',
            'application_url': 'https://sap-iot.com',
            'subdomain': 'account-name'
        },
    })


YAML file
---------
Specify the location of a YAML file via environment variable (e.g.: *SAILOR_CONFIG_PATH=/home/my_sailor_config.yml*). Alternatively you can put a YAML file named *config.yml* next to your main script/notebook without setting the SAILOR_CONFIG_PATH. Example YAML file:

.. code-block:: yaml

    asset_central:
      client_id: ACexampleId
      client_secret: ACexampleSecret
      application_url: https://asset-central.com
      subdomain: account-name
    sap_iot:
      client_id: IoTexampleId
      client_secret: IoTexampleSecret
      application_url: https://sap-iot.com
      subdomain: account-name




Quickstart Example
==================

.. code-block:: python

    # This is just a random placeholder
    import numpy as np
    np.arange(10)



**TODO**: Update!!! First basic functionality that should be supported:

.. code-block:: python

    from dsc.asset_central import AssetCentral

    ac = AssetCentral(credentials)

    # get a specific equi model uniquely specified by id
    # should return a custom object of class `EquipmentModel`
    euipment_model = ac.get_equipment_model(id='ID')

    # find some equipment models (might be multiple) based on some filters
    # additional filters (e.g. location, class, whatever) beyond MVP
    # should return a list of `EquipmentModel`s
    ac.find_equipment_models(name='NAME')

    # the same goes for individual equipments:
    equipment = ac.get_equipment(id='ID')
    ac.find_equipments(name='Name')

    # Find all instances belonging to a certain model
    equipments = equipment_model.get_equipments()

    # Find all Failure Modes assigned to an equipment/equipment model
    failure_modes = equipment_model.get_failure_modes()
    failure_modes = equipment.get_failure_modes()

    # Find all (or specific) notifications for an equipment
    # by default returns notifications for all failure modes,
    # but you can specify a subset of failure modes to filter
    equipment.get_notifications(failure_modes = None)

    # I think that's a good start for AC. Let's tackle IoT AE later.


*Optional: Limitations*
=======================

**TODO**: If your sample code has limitations that prevent it from working on certain hardware, or in certain software or configurations, please list those here.

Known Issues
============

**TODO**: Please list all known issues, or bugs, here. Even if the sample code is provided "as-is" any known problems should be listed.

Maybe just refer to FAQ as Link??


How to obtain support
=====================

**TODO**: This section should contain details on how the outside user can obtain support, ask questions, or post a bug report on your sample code.
For example, if your project allows and expects users to post questions or bug reports in the GitHub bug tracking system, put that information here. If your team is also monitoring another website for questions (for example, the SAP Q&A, or StackOverflow), that should also be listed.
If your project is provided "as-is", with no expected changes or support, you must state that here.

*Optional: Contributing*
========================

Install the package in editable mode
------------------------------------

For development, this will install the package into your environment with a link to the source files.

.. code-block::

    pip install -e .


Install requirements
--------------------
.. code-block::

    pip install -r requirements.txt

Requirements management
-----------------------
The concrete dependencies we develop against are pinned in `requirements.txt`. Our code has been tested to run for the versions listed in :code:`requirements.txt`. (TODO: make that happen: ~~Continuous integration ensures that we test the code against new versions automatically.~~) `requirements.txt` should never be modified manually, only through pip-compile (see below).

:code:`requirements.in` lists abstract dependencies.  If you have used a new library in this project:

1. please add it to **requirements.in** and run :code:`pip-compile` to update the requirements.txt
2. Add the resulting changes to your next pull request.

*pip-compile* is part of package *pip-tools* (can be installed via `pip install pip-tools`).


Dev tools
---------

Install all tools required for testing and linting with:

.. code-block::

    pip install -r .ci/requirements_ci.txt


Building the package
--------------------
.. code-block::

    python -m build


Building the documentation
--------------------------
**Sphinx** is used to build the documentation.

Requirements
************
You will need to install Sphinx and dependencies that we use. This can be done via pip:

.. code-block::

    pip install -r .ci/docs/requirements_docs.txt

Build
*****
Go to the docs directory and run:

.. code-block::

    make html


The HTML is built into the docs/_build directory. You can view the docs by simply opening **index.html** with your browser.

    If you just ran `make html` for the **first time**, it might be that the documentation is not rendered properly (specifically the TOC for the API documentation on the left).
    In this case please run once:

    .. code-block::

        touch apidoc.rst
        make html SPHINXOPTS="-a"

    Further builds should only require `make html`.



Adding or removing API doc pages
********************************
This step is only required when new modules/packages have been added or removed.
If you want to update the apidoc:

1. run: :code:`make apidoc`
2. (only if any packages/modules have been removed): delete the corresponding .rst files
3. commit the changes


*Optional: Upcoming Changes*
============================

**TODO**: Details on any expected changes in later versions. If your project is released "as-is", or you know of no upcoming changes, this section can be omitted.

*Optional: License*
===================

**TODO**: The governing license for the project can be referenced in the README file for the project by adding a section entitled “License” (or similar title) and including the following statement:
“This project is licensed under [License file type] except as noted otherwise in the LICENSE file.”

