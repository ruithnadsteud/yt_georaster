Loading Data
============

The ``yt_georaster`` extension provides support for all file types that
are loadable by ``rasterio``, including ``GeoTIFF`` and ``JPEG2000``.
For everything to work correctly, the image files must include geotagging
metadata, such as the coordinate reference system (CRS) and transform.
Consult the `rasterio documentation <https://rasterio.readthedocs.io/>`__
for more information.

The ``yt`` :func:`~yt.loaders.load` function can be used to load all
supported data. The relevant yt documentation is :ref:`here <loading-data>`.
This typically takes the form:

.. code-block:: python

   >>> import yt
   >>> ds = yt.load(filename)

To load data supported by ``yt_georaster``, just add
``import yt.extensions.georaster`` to your script.

.. code-block:: python

   >>> import yt
   >>> import yt.extensions.georaster
   >>> ds = yt.load(filename)

Loading a Single Image
----------------------

To load a file or files, provide the paths as individual arguments to
``yt.load``.

.. code-block:: python

   >>> import yt
   >>> import yt.extensions.georaster
   >>> ds = yt.load("200km_2p5m_N38E34.tif")
   yt : [INFO     ] 2021-06-29 12:37:13,171 Parameters: domain_dimensions         = [80000 80000     1]
   yt : [INFO     ] 2021-06-29 12:37:13,174 Parameters: domain_left_edge          = [3444000. 3642000.       0.] m
   yt : [INFO     ] 2021-06-29 12:37:13,174 Parameters: domain_right_edge         = [3.644e+06 3.842e+06 1.000e+00] m

Upon loading, ``yt`` will print the dimensions (i.e., the number of pixels
in x and y) and coordinates of the left and right corners of the image in
the loaded image's CRS. Because ``yt`` mainly deals with 3D data, the
dimensions will be reported with a value of 1 in the z direction and
values of 0 m and 1 m for the coordinates of the left and right corners.
Do not worry; nothing bad will happen because of this.

The values printed after loading are attributes associated with the loaded
dataset (i.e., the ``ds``). Similarly, one can access the resolution of
image.

.. code-block:: python

   >>> print (ds.domain_dimensions)
   [80000 80000     1]
   >>> print (ds.domain_right_edge.to('km'))
   [3.644e+03 3.842e+03 1.000e-03] km
   >>> print (ds.resolution)
   unyt_array([2.5, 2.5], 'm')

Note that values that should have units are returned as
`unyt_arrays <https://unyt.readthedocs.io/en/stable/>`__. See
:ref:`this discussion in yt <units>` for more information about quantities
with units.

.. _ytgr_load_multiple:

Loading Multiple Images
-----------------------

Multiple images can be loaded into the same dataset by providing each file
path to ``yt.load``.

.. code-block:: python

   >>> import yt
   >>> import yt.extensions.georaster

   >>> filenames = glob.glob("Landsat-8_sample_L2/*.TIF") + \
   ...   glob.glob("M2_Sentinel-2_test_data/*.jp2")
   >>> ds = yt.load(*filenames)
   yt : [INFO     ] 2021-06-29 13:19:24,134 Parameters: domain_dimensions         = [7581 7741    1]
   yt : [INFO     ] 2021-06-29 13:19:24,134 Parameters: domain_left_edge          = [ 361485. -116415.       0.] m
   yt : [INFO     ] 2021-06-29 13:19:24,135 Parameters: domain_right_edge         = [5.88915e+05 1.15815e+05 1.00000e+00] m

Note, the argument to ``yt.load`` is ``*filenames`` and not just
``filenames``. This expands the list into its individual items.

.. _ytgr_base_image:

The Base Image
^^^^^^^^^^^^^^

When loading multiple images, the information printed upon load is associated
with the first argument given. This image is referred to in this document as
the **base image**. All queried data will be returned in the resolution and
CRS of the base image. **Only data within the bounds of the base image can be
queried.** Printing either ``ds`` or ``ds.parameter_filename`` will tell you
what the base image is.

.. code-block:: python

   >>> print (ds)
   LC08_L2SP_171060_20210227_20210304_02_T1_QA_PIXEL
   >>> print (ds.parameter_filename)
   Landsat-8_sample_L2/LC08_L2SP_171060_20210227_20210304_02_T1_QA_PIXEL.TIF

Specifying your Coordinate Reference System
-------------------------------------------

At load you can also specify what coordinate reference system (CRS) you want to handle your dataset in.

.. code-block:: python

   >>> import yt
   >>> import yt.extensions.georaster

   >>> filenames = glob.glob("Landsat-8_sample_L2/*.TIF") + \
   ...   glob.glob("M2_Sentinel-2_test_data/*.jp2")
   >>> ds = yt.load(*filenames, crs="epsg:32736")

This should work for all projected systems. Instead of using the CRS of your base image the dataset is assigned the CRS you provide and yt will convert everything into this coordinate reference system as you query that data.
