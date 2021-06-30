.. _api-reference:

API Reference
=============

Functions
---------

.. autosummary::
   :toctree: generated/

   ~yt_georaster.data_structures.GeoRasterDataset.plot
   ~yt_georaster.data_structures.GeoRasterDataset.circle
   ~yt_georaster.polygon.YTPolygon
   ~yt_georaster.data_structures.GeoRasterDataset.rectangle
   ~yt_georaster.data_structures.GeoRasterDataset.rectangle_from_center
   ~yt_georaster.utilities.save_as_geotiff

Classes
-------

.. autosummary::
   :toctree: generated/

   ~yt_georaster.data_structures.GeoRasterDataset
   ~yt_georaster.data_structures.GeoRasterGrid
   ~yt_georaster.data_structures.GeoRasterHierarchy
   ~yt_georaster.data_structures.GeoRasterWindowGrid
   ~yt_georaster.data_structures.GeoRasterWindowDataset
   ~yt_georaster.fields.GeoRasterFieldInfo
   ~yt_georaster.io.IOHandlerGeoRaster

Is This Page Empty or Broken?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are reading this on readthedocs.org, this page may be empty or the
links to the various functions and classes may not be clickable. Getting
the API docs to show up requires installing ``yt_georaster``, which is
difficult to accomplish on readthedocs. Sometimes it works. Anyway, you can
build the docs locally by installing ``yt_georaster`` with the developer
requirements and using sphinx to build the docs.

.. code-block:: bash

   $ cd yt_georaster
   $ pip install -e .[dev]
   $ cd doc
   $ make html

These docs can then be found in the ``yt_georaster`` source directory in
``doc/build/html``.
