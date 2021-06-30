.. _ytgr_fields:

Data Fields
===========

Data access in ``yt`` is built on the concept of :ref:`fields`. The user
creates a :ref:`geometric data container <ytgr_containers>` (e.g., a circle,
rectangle, or polygon) and queries a field (i.e., data from a specific
file or band) by name. Data is returned as arrays of all pixels inside the
container.

Fields on Disk
--------------

To see a list of all fields on disk, have a look at the ``field_list``
attribute associated with any loaded dataset.

.. code-block:: python

   >>> import yt
   >>> import yt.extensions.georaster

   >>> ds = yt.load("circle.tif")
   yt : [INFO     ] 2021-06-29 14:47:28,378 Parameters: domain_dimensions         = [1549 1549    1]
   yt : [INFO     ] 2021-06-29 14:47:28,378 Parameters: domain_left_edge          = [451965. -23535.      0.] m
   yt : [INFO     ] 2021-06-29 14:47:28,379 Parameters: domain_right_edge         = [4.98435e+05 2.29350e+04 1.00000e+00] m

   >>> print (ds.field_list)
   [('circle', 'band_1'), ('circle', 'band_2'), ('circle', 'band_3'), ('circle', 'band_4')]

Fields in ``yt`` are named with tuples, where the first item is typically
referred to as the "field type" and the second as the "field name". For a
generic rasterio-loadable image file, the field type will be the name of
the file (minus the extension) and the fields will be named "band\_" and
the band number. To see the list of available field types, check out the
``fluid_types`` attribute.

.. code-block:: python

   >>> print (ds.fluid_types)
   ('index', 'circle')

The "index" fluid type is for accessing fields associated with the position
and size of pixels, such as "x", "y", and "area".

Satellite-Specific Fields and Aliases
-------------------------------------

``yt_georaster`` can recognize naming conventions of data products from a
few different satellites. If a loaded file matches the naming conventions
of a supported satellite, the fields will be named with the field type
corresponding to the unique image identifier (usually the first part of
the filename before the name of the band) and the field names as a
combination of the satellite type, band number, and resolution. For
example, a Sentinel-2 image from band 02 with a resolution of 10 meters
will be named "S2_B02_10m".

For every band field, an alias field will be created pointing to the highest
resolution image available. In the example below, we load two Sentinel-2
images of band 2 at resolutions of 10 and 20 meters.

.. code-block:: python

   >>> filenames = glob.glob("Sentinel-2_sample_L2A/T30UVG_20200601T113331_*.jp2")
   >>> ds = yt.load(*filenames)

   >>> print (ds.fluid_types)
   ('T30UVG_20200601T113331', 'index')

   >>> print (ds.field_list)
   [('T30UVG_20200601T113331', 'S2_B01_60m'),
    ('T30UVG_20200601T113331', 'S2_B02_10m'),
    ('T30UVG_20200601T113331', 'S2_B02_20m'),
    ...
   ]

   >>> print (ds.fields.T30UVG_20200601T113331.S2_B02_10m)
   On-Disk Field (T30UVG_20200601T113331, S2_B02_10m): (units: )
   >>> print (ds.fields.T30UVG_20200601T113331.S2_B02_20m)
   On-Disk Field (T30UVG_20200601T113331, S2_B02_20m): (units: )

   >>> print (ds.fields.T30UVG_20200601T113331.S2_B02)
   Alias Field for "('T30UVG_20200601T113331', 'S2_B02_10m')" (T30UVG_20200601T113331, S2_B02): (units: )

These aliases will be made for all bands, even if only a single resolution is
available.

Landsat-8
^^^^^^^^^

Landsat-8 fields are prefaced with "L8\_". Click around enough on
`this Landsat-8 mission page
<https://www.usgs.gov/core-science-systems/nli/landsat/landsat-8?qt-science_support_page_related_con=0#>`__ and you'll find the band definitions in a pdf file.
These have been aliased as the following:

+------+-----------+
| Band | Aliases   |
+======+===========+
| B1   | visible_1 |
+------+-----------+
| B2   | visible_2 |
+------+-----------+
| B3   | visible_3 |
+------+-----------+
| B4   | red       |
+------+-----------+
| B5   | nir       |
+------+-----------+
| B6   | swir_1    |
+------+-----------+
| B7   | swir_2    |
+------+-----------+
| B8   | pan       |
+------+-----------+
| B9   | cirrus    |
+------+-----------+
| B10  | tirs_1    |
+------+-----------+
| B11  | tirs_2    |
+------+-----------+

.. code-block:: python

   >>> filenames = glob.glob("Landsat-8_sample_L2/LC08_L2SP_171060_20210227_20210304_02_T1*.TIF")
   >>> ds = yt.load(*filenames)
   yt : [INFO     ] 2021-06-29 16:57:21,839 Parameters: domain_dimensions         = [7581 7741    1]
   yt : [INFO     ] 2021-06-29 16:57:21,839 Parameters: domain_left_edge          = [ 361485. -116415.       0.] m
   yt : [INFO     ] 2021-06-29 16:57:21,840 Parameters: domain_right_edge         = [5.88915e+05 1.15815e+05 1.00000e+00] m

   >>> print (ds.fields.LC08_L2SP_171060_20210227_20210304_02_T1.red)
   Alias Field for "('LC08_L2SP_171060_20210227_20210304_02_T1', 'L8_B4')" (LC08_L2SP_171060_20210227_20210304_02_T1, red): (units: )

Sentinel-2
^^^^^^^^^^

Sentinel-2 fields are prefaced with "S2\_". Bands are defined, for example,
`here <https://gisgeography.com/sentinel-2-bands-combinations/>`__ and
`here <https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/resolutions/spatial>`__.
These have been aliased as the following:

+------+--------------------+
| Band | Aliases            |
+======+====================+
| B01  | ultra_blue         |
+------+--------------------+
| B02  | blue               |
+------+--------------------+
| B03  | green              |
+------+--------------------+
| B04  | red                |
+------+--------------------+
| B05  | vnir_1, red_edge_1 |
+------+--------------------+
| B06  | vnir_2, red_edge_2 |
+------+--------------------+
| B07  | vnir_3             |
+------+--------------------+
| B08  | vnir_4             |
+------+--------------------+
| B8A  | vnir_5, nir        |
+------+--------------------+
| B09  | swir_1             |
+------+--------------------+
| B10  | swir_2             |
+------+--------------------+
| B11  | swir_3             |
+------+--------------------+
| B12  | swir_4             |
+------+--------------------+

.. code-block:: python

   >>> filenames = glob.glob("Sentinel-2_sample_L2A/T30UVG_20200601T113331_*.jp2")
   >>> ds = yt.load(*filenames)

   >>> print (ds.fields.T30UVG_20200601T113331.red)
   Alias Field for "('T30UVG_20200601T113331', 'S2_B04')" (T30UVG_20200601T113331, red): (units: )

Derived Fields
--------------

In addition to the fields on disk, ``yt_georaster`` defines a series of
"derived fields", which are arithmetic combinations of other existing
fields. The full list of available derived fields can be seen by
inspecting the ``derived_field_list`` attribute associated with the loaded
dataset. This list is quite long and includes things not specifically
relevant to ``yt_georaster`` (as they are defined within ``yt`` itself).
Those specific to ``yt_georaster`` are listed below. Each of the fields
below will exist for every field type that defines all the required
fields.

To see how each derived field is defined, use the ``get_source`` function.

.. code-block:: python

   >>> print (ds.fields.T30UVG_20200601T113331.NDWI.get_source())
               def _ndwi(field, data):
                   ftype = field.name[0]
                   green = data[ftype, "green"]
                   nir = data[ftype, "nir"]
                   return (green - nir) / (green + nir)

For more information defining new derived fields, see
:ref:`creating-derived-fields`. In the table below, ``<field type>``
refers to any loaded satellite data for which the required bands
are available.

+----------------------------------+----------------------------------------+
| Field                            | Description                            |
+==================================+========================================+
| ("index", "area")                | pixel area (``dx*dy``)                 |
+----------------------------------+----------------------------------------+
| (<field type>, "NDWI")           | Normalised difference water index      |
+----------------------------------+----------------------------------------+
| (<field type>, "MCI")            | Maximum chlorophyll index              |
+----------------------------------+----------------------------------------+
| (<field type>, "CDOM")           | Colored Dissolved Organic Matter       |
+----------------------------------+----------------------------------------+
| (<field type>, "EVI")            | Enhanced Vegetation Index              |
+----------------------------------+----------------------------------------+
| (<field type>, "NDVI")           | Normalised Difference Vegetation Index |
+----------------------------------+----------------------------------------+
| (<field type>, "LS_temperature") | Landsat Surface Temperature            |
+----------------------------------+----------------------------------------+
