.. image:: https://api.reuse.software/badge/github.com/SAP/project-sailor
    :target: https://api.reuse.software/badge/github.com/SAP/project-sailor

================
Project "Sailor"
================

.. inclusion-marker-do-not-remove

**Project "Sailor"** allows you to easily access data from your SAP Digital Supply Chain software products for data science projects like
predictive maintenance or master data analysis.

Once your data is available, it is your choice how to work with it. Project "Sailor" comes with several predefined functions to support you
in exploring your data. Adding to that you can create custom plots or even build your own machine learning models.
You can learn more about that on our `tutorial page <https://sap.github.io/project-sailor/tutorial.html>`__.
"Sailor" provides you with a set of functions out of the box, but most importantly it facilitates flexibility and extensibility.


Requirements
============

You need access to SAP Asset Central and the SAP IoT services in order to use "Sailor".

Since the project "Sailor" is implemented in Python you need to have Python installed. Currently we support Python >=3.8.
The required python packages are automatically installed while installing "Sailor".


Installation
============

Install the package with pip

.. code-block::

   pip install sailor


Configuration
=============

"Sailor" talks to two services: SAP Asset Central and SAP IoT.
You have two options of specifying the configuration:

1. `Environment`_
2. `YAML file`_

The above order is honoured when "Sailor" checks for the configuration.


Environment
-----------
A JSON string can be provided with the environment variable ``SAILOR_CONFIG_JSON``. Example:

.. code-block:: python

    os.environ['SAILOR_CONFIG_JSON'] = json.dumps({
        'asset_central': {
            'client_id': 'ACexampleId',
            'client_secret': 'ACexampleSecret',
            'application_url': 'https://<system>.cfapps.<landscape>.hana.ondemand.com',
            'access_token_url': 'https://authentication.<landscape>.hana.ondemand.com/oauth/token',
            'subdomain': 'account-name'
        },
        'sap_iot': {
            'client_id': 'IoTexampleId',
            'client_secret': 'IoTexampleSecret',
            'application_url': 'https://iot-ts-access-sap-<space>.cfapps.<landscape>.hana.ondemand.com',
            'export_url': 'https://coldstore-export-sap-<space>.cfapps.<landscape>.hana.ondemand.com',
            'download_url': 'https://coldstore-downloader-sap-<space>.cfapps.<landscape>.hana.ondemand.com',
            'access_token_url': 'https://authentication.<landscape>.hana.ondemand.com/oauth/token',
            'subdomain': 'account-name'
        },
    })


YAML file
---------
Specify the location of a YAML file via environment variable (e.g.: ``SAILOR_CONFIG_PATH=/home/my_sailor_config.yml``). Alternatively you can put a YAML file named ``config.yml`` next to your main script/notebook without setting the ``SAILOR_CONFIG_PATH``. Example YAML file:

.. code-block:: yaml

    asset_central:
      client_id: ACexampleId
      client_secret: ACexampleSecret
      application_url: https://<system>.cfapps.<landscape>.hana.ondemand.com
      access_token_url: https://authentication.<landscape>.hana.ondemand.com/oauth/token
      subdomain: account-name
    sap_iot:
      client_id: IoTexampleId
      client_secret: IoTexampleSecret
      application_url: https://iot-ts-access-sap-<space>.cfapps.<landscape>.hana.ondemand.com
      export_url: https://coldstore-export-sap-<space>.cfapps.sap.<landscape>.ondemand.com
      download_url: https://coldstore-downloader-sap-<space>.cfapps.<landscape>.hana.ondemand.com
      access_token_url: https://authentication.<landscape>.hana.ondemand.com/oauth/token
      subdomain: account-name




Quickstart Example
==================

The following code snippet can be used to quickly get started with "Sailor". It shows you how to read data of equipments, notifications and sensor data from your SAP backends. In addition to that there are predefined plotting functions which can be used to explore your data.

For a detailed example please visit our `tutorial page <https://sap.github.io/project-sailor/tutorial.html>`__. It will walk you through the functionality offered by project "Sailor" step by step.


.. code-block:: python

    import pandas as pd
    from sailor.assetcentral import find_equipment, find_notifications

    # find equipments and plot them
    equipment_set = find_equipment(model_name='my_model_name')
    equipment_set.plot_distribution('location_name')

    # get sensor data from equipment
    timeseries_data = equipment_set.get_indicator_data('2020-10-01 00:00:00+00:00', '2021-01-01 00:00:00+00:00')

    # find notifications and plot them
    notification_set = equipment_set.find_notifications(extended_filters=['malfunction_start_date > "2020-08-01"'])
    notification_set.plot_overview()



Limitations
===========

Currently we do not support parallel data processing frameworks.
You are bound by the limitations of the pandas DataFrame and the computing hardware running our code.

Known Issues
============

There are currently no known issues. All upcoming issues are tracked as `GitHub Issues <https://github.com/SAP/project-sailor/issues>`__ in the repository.


How to obtain support
=====================

If you encountered a bug or have a feature request, please create a `GitHub Issue <https://github.com/SAP/project-sailor/issues>`__ in the repository.
You can also get in touch with the developers directly by reaching out to `project.sailor@sap.com <mailto:project.sailor@sap.com>`__ in order to obtain support.


Contributing
============

We welcome all contributions either in form of issues, code contributions, questions or any other formats. For details please refer to the `Contributing Page <https://sap.github.io/project-sailor/contributing.html>`__ in the documentation.


Licensing
=========
Please see our `LICENSE <https://github.com/SAP/project-sailor/blob/main/LICENSE>`__ for copyright and license information. Detailed information including third-party components and their licensing/copyright information is available via the `REUSE tool <https://api.reuse.software/info/github.com/SAP/project-sailor>`__.
