.. _filter:

Filter language
===============
There is a function in each of the `assetcentral` modules for fetching data from AssetCentral. All of these functions support the same parameters, syntax and semantics.

For example:
``find_notifications(inequality_filters=None, **kwargs)``

Parameters
----------
`inequality_filters`
   A list of expressions that specify filters with inequality operators.

`**kwargs`
   Any named keyword arguments are applied as equality filters.


Equality filters
----------------
Any **named keyword arguments** applied as equality filters. 

- The **key** of the keyword argument is checked against the value of the keyword argument in Asset Central.
- If the **value** of the keyword argument is an :obj:`Iterable` (e.g. a :obj:`List`) then all objects matching any of the values in the iterable are returned. 
- If multiple named arguments are provided then *all* conditions have to match.

**Examples:**

``find_notifications(short_description='MyNotification')``
will return all notifications with description 'MyNotification'.

``find_notifications(short_description=['MyNotification', 'MyOtherNotification'])``
will return all notifications which either have the description 'MyNotification' OR the description 'MyOtherNotification'.

``find_notifications(short_description='MyNotification', start_date='2020-07-01')``
will return all notifications with description 'MyNotification' which also have the start date '2020-07-01'.



Inequality filters
------------------
The *inequality_filters* parameter can be used to specify filters that can not be expressed as an equality. Inequality filters need to be provided as :obj:`List`.
Each element in the list needs to be provided as a :obj:`str` expression conforming to the following grammar: ``field operator (field|literal)`` where *literal* must be quoted.

- Supported operators are ``<`` ``>`` ``!=``.
- As with equality filters, *all* conditions need to match for a result to be returned.
- Inequality filters can be freely combined with named arguments. All filter criteria need to match for a result to be returned.


**Examples:**

``find_notifications(inequality_filters=['short_description != "MyNotification"'])``
will return all notifications with a description not matching 'MyNotification'.

``find_notifications(['malfunctionStartDate > "2020-08-01"', 'malfunctionEndDate <= "2020-09-01"])``
will return all notifications in a given timeframe.

The following example will return all notifications in a given timeframe for both equipments with 'id1' and 'id2'.

.. code-block:: python

   find_notifications(['malfunctionStartDate > "2020-08-01"', 'malfunctionEndDate <= "2020-09-01"'],
                     equipment_id=['id1', 'id2'])


