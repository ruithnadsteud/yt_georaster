.. _ytgr_containers:

Data Containers
===============

Data access in ``yt`` is facilitated through geometric data containers. A
user defines a shape in terms of its position and size. The object created
will return data for all pixels contained within the shape. Since ``yt``
was designed primarily for 3D data, the native data containers (see
:ref:`Data-objects`) are things like spheres, cylinders, and rectangular
prisms. ``yt_georaster`` offers three 2D containers: :ref:`ytgr_circles`,
:ref:`ytgr_rectangles`, and :ref:`ytgr_polygons`. The circle and rectangle
containers are thing wrappers around the 3D cylinder and rectangular
prism containers. Data containers will return NumPy arrays of
:ref:`ytgr_fields` for all pixels inside the container. They can also be
used with :ref:`ytgr_plotting`.

There are a number of other interesting things that can be done with them.
See, for example, the links below:

- :ref:`derived-quantities`
- :ref:`filtering-data`
- :ref:`cut-regions`

Data Resampling and Transforming
--------------------------------

``yt_georaster`` supports loading images with different resolutions and
coordinate reference systems (see :ref:`ytgr_load_multiple`). When data
is queried with a data container, it is resampled to the resolution of
:ref:`ytgr_base_image` and transformed into the CRS of :ref:`ytgr_base_image`.

**Data cannot be queried outside the bounds of :ref:`ytgr_base_image`.**
However, data **can** be queried outside of secondary (i.e., not the base)
images. All pixels outside a secondary image will be returned as zeros.

.. _ytgr_circles:

Circles
-------

A :func:`~yt_georaster.data_structures.GeoRasterDataset.circle` is defined
by a center and radius.

.. code-block:: python

   >>> import yt
   >>> import yt.extensions.georaster

   >>> filenames = glob.glob("Landsat-8_sample_L2/*.TIF") + \
   ...   glob.glob("M2_Sentinel-2_test_data/*.jp2")
   >>> ds = yt.load(*filenames)
   yt : [INFO     ] 2021-06-29 13:19:24,134 Parameters: domain_dimensions         = [7581 7741    1]
   yt : [INFO     ] 2021-06-29 13:19:24,134 Parameters: domain_left_edge          = [ 361485. -116415.       0.] m
   yt : [INFO     ] 2021-06-29 13:19:24,135 Parameters: domain_right_edge         = [5.88915e+05 1.15815e+05 1.00000e+00] m

   >>> # an array with units
   >>> center = ds.arr([500, 0], "km")
   >>> # a single value with units
   >>> radius = ds.quan(10, "km")

   >>> cir = ds.circle(center, radius)

Field data is access by querying the data container like a dictionary.

.. Code-block:: python

   >>> print (cir["LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B2"])
   unyt_array([8956., 8974., 8980., ..., 7541., 7550., 7493.], '(dimensionless)')

   >>> print (cir["index", "area"].sum().to("m**2"))
   314156700.00000006 m**2

Data is returned a :ref:`unyt array <units>`, a subclass of the NumPy array
supporting symbolic units. The raw NumPy array can be accessed by appending
``.d``.

.. code-block:: python

   >>> cir["LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B2"].d
   array([8956., 8974., 8980., ..., 7541., 7550., 7493.])

.. _ytgr_rectangles:

Rectangles
----------

A :func:`~yt_georaster.data_structures.GeoRasterDataset.rectangle` is defined
by the coordinates of the left and right corners. Note, the values of the right
corner must be greater than the left corner. A
:func:`~yt_georaster.data_structures.GeoRasterDataset.rectangle_from_center`
can also be defined by a center, width, and height.

.. _ytgr_polygons:

Polygons
--------

``yt_georaster`` supports arbitrary polygons loaded from `Shapefiles
<https://en.wikipedia.org/wiki/Shapefile>`__. **Currently, the shape must
be in the CRS of the base image.** A
:class:`~yt_georaster.polygon.YTPolygon` object is created by
specifying the path to the shapefile.

.. code-block:: python

   >>> poly = ds.polygon("example_polygon_mabira_forest/mabira_forest.shp")
   >>> print (poly["LC08_L2SP_171060_20210227_20210304_02_T1", "red"])
   unyt_array([ 8324.,  8340.,  8372., ..., 10422., 10536., 10333.], '(dimensionless)')

   >>> print (poly["index", "area"].sum())
   331.2063 km**2

.. note:: The current implementation of the polygon container considers any
   cell overlapping the polygon boundary to be "contained" within the
   polygon. Polygon data containers are implemented with the ``shapely``
   package using ``within``. This can be modified to include only pixels
   whose centers are inside the polygon by using the ``intersects`` class
   method instead.

.. _ytgr_base_image_data:

Data from the Base Image
------------------------

In addition to geometric shapes, data can be queried for 2D grid representing
:ref:`ytgr_base_image`. This will return data as 2D arrays (technically, 3D
arrays with the last third dimension of size 1) corresponding to the dimensions
of the base image. This is done by accessing the ``data`` attribute.

.. code-block:: python

   >>> import glob
   >>> import yt
   >>> import yt.extensions.georaster

   >>> fns = glob.glob("M2_Sentinel-2_test_data/*.jp2")
   >>> ds = yt.load(*fns)
   yt : [INFO     ] 2021-06-30 10:34:46,490 Parameters: domain_dimensions         = [1830 1830    1]
   yt : [INFO     ] 2021-06-30 10:34:46,490 Parameters: domain_left_edge          = [ 399960. 9890200.       0.] m
   yt : [INFO     ] 2021-06-30 10:34:46,491 Parameters: domain_right_edge         = [5.0976e+05 1.0000e+07 1.0000e+00] m

   >>> print (ds.data["T36MVE_20210315T075701", "NDWI"].shape)
   yt : [INFO     ] 2021-06-30 10:34:58,748 Resampling ('T36MVE_20210315T075701', 'S2_B03_10m'): 10.0 to 60.0 m.
   yt : [INFO     ] 2021-06-30 10:35:00,706 Resampling ('T36MVE_20210315T075701', 'S2_B8A_20m'): 20.0 to 60.0 m.
   (1830, 1830, 1)
