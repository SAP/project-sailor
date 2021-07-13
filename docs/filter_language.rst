.. _filter:

Filter Language
===============

Project "Sailor" supports retrieval of objects such as :class:`~sailor.assetcentral.equipment.Equipment` or
:class:`~sailor.assetcentral.notification.Notification` from AssetCentral through functions like
:meth:`~sailor.assetcentral.equipment.find_equipment` or :meth:`~sailor.assetcentral.notification.find_notifications`.
All of these functions support a common filter language which is described below. The filter criteria are transformed
into an odata query and forwarded to the server, so only matching objects are retrieved.

All functions of this kind support two types of parameters:
 - named keyword arguments are interpreted as a simple shortcut for equality filters.
 - an argument `extended_filters` allows more complex filters such as inequality constraints or filters referring to
   another field of the object.

The names of all fields known for an object, and hence all fields which may be used for filtering can be determined
by calling the :meth:`~sailor.assetcentral.utils.AssetcentralEntity.get_available_properties` classmethod of the object, such as
``Notification.get_available_properties()`` etc. This method returns a set of all known and
and filterable fields.

Named Keyword Arguments
-----------------------
Any **named keyword argument** is applied as an equality filter.

- The **key** of the keyword argument determines the field of the object against which the filter is executed.
- If the **value** of the keyword argument is a simple object (e.g. a string, int or float), the value of the field in
  AssetCentral must be the same as the value of the argument for the filter to match. The type of the argument is
  preserved in the query.
- If the **value** of the keyword argument is an :obj:`Iterable` (e.g. a :obj:`List`), then all objects matching *any*
  of the values in the iterable are returned.
- If multiple named arguments are provided, then *all* conditions have to match.

**Examples:**

``find_notifications(short_description='MyNotification')``
will return all notifications with description 'MyNotification'.

``find_notifications(short_description=['MyNotification', 'MyOtherNotification'])``
will return all notifications which either have the description 'MyNotification' or the description 'MyOtherNotification'.

``find_notifications(short_description='MyNotification', start_date='2020-07-01')``
will return all notifications with description 'MyNotification' which also have the start date '2020-07-01'.

The following example will return all notifications with description 'MyNotification' and start date '2020-07-01' or
with description 'MyOtherNotification' and start date '2020-07-01'.

.. code-block:: python

   find_notifications(short_description=['MyNotification', 'MyOtherNotification'],
                      start_date='2020-07-01')



Extended Filters
------------------
The *extended_filters* parameter can be used to specify filters that cannot be expressed as an equality or filters
that should refer to another field of the same object.
Extended filters need to be provided as :obj:`List`. Each element in the list needs to be provided as a :obj:`str`
expression conforming to the following grammar: ``field operator (field|literal)``. Here unquoted strings are interpreted
as a field reference, while quoted strings as well as unquoted numeric values are interpreted as a literal. Both single
and double quotes may be used for quoting.

- Supported operators are ``<`` ``>`` ``<=`` ``>=`` ``!=`` ``==``.
- As with equality filters, *all* conditions need to match for a result to be returned.
- Extended filters can be freely combined with named arguments. All filter criteria need to match for a result to be returned.


**Examples:**

``find_notifications(extended_filters=['short_description != "MyNotification"'])``
will return all notifications with a description not matching 'MyNotification'.

``find_notifications(extended_filters=['malfunction_start_date > "2020-08-01"', 'malfunction_end_date <= "2020-09-01"])``
will return all notifications in a given timeframe.

``find_notifications(extended_filters=['malfunction_start_date == malfunction_end_date'])``
will return all notifications where the start date of the malfunction is equal to the end date of the malfunction.


The following example will return all notifications in a given timeframe for both pieces of equipment with 'id1' and 'id2'.

.. code-block:: python

   find_notifications(extended_filters=['malfunction_start_date > "2020-08-01"', 'malfunction_end_date <= "2020-09-01"'],
                      equipment_id=['id1', 'id2'])

