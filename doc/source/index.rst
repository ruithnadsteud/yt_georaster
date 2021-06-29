Welcome to yt_georaster.
========================

``yt_georaster`` is a `yt <https://yt-project.org/>`__ extension for analyzing
geotagged image files that are loadable with `rasterio
<https://rasterio.readthedocs.io/>`__. The ``yt_georaster`` extension combines
``yt`` and ``rasterio``, allowing users to query data contained within geometric
shapes, like circles, rectangles, and arbitrary polygons saved as `Shapefiles
<https://en.wikipedia.org/wiki/Shapefile>`__. Multiple images with different
resolutions and coordinate reference systems can be loaded together. All queried
data is transformed to the same resolution and coordinate reference system and
returned as NumPy arrays of the same shape. Data from multiple images can also
be re-saved to a single, multiband `GeoTIFF
<https://en.wikipedia.org/wiki/GeoTIFF>`__ file.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   Help.rst
   Installation.rst
   Loading.rst
   Fields.rst
   Containers.rst
   Plotting.rst
   Saving.rst
   api_reference.rst

Search
======

* :ref:`search`
