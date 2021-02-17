.. _examples::

===============
Examples
===============

You can find several examples on how to use the sdk.


Creating custom plots
=====================

Just a placeholder to show how an example could look like.

.. code-block:: python
    
    import plotnine as p9
    from sdk.dsc.assetcentral.equipment import find_equipments, Equipment, EquipmentSet
    from sdk.dsc.utils import default_plot_theme

    equipment_set = find_equipments(equipment_model_name='DataSciencePumpModel')
    data = equipment_set[10:13].get_indicator_data('2020-09-01', '2020-10-05', aggregation_interval='PT1H', aggregation_functions=['AVG'])

    df = data.as_df(speaking_names=True).droplevel([0, 1, 3], axis=1).reset_index()
    df = df.melt(id_vars=['equipment_name', 'equipment_model_name', 'timestamp'], var_name='indicator')
    p9.ggplot(df, p9.aes(x='indicator', y='value', fill='equipment_name')) + p9.geom_violin(alpha=0.6) + default_plot_theme()


.. image:: _static/custom_plot.png
    :width: 400
    :alt: Custom Plot




Another awesome example
=======================

**TODO**

