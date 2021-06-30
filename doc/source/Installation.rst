Installation
============

At present, ``yt_georaster`` can only be installed from source. To do this,
one must clone the repository and use ``pip`` or ``conda`` to install. This
process is detailed below. the ``yt_georaster`` repository lives at
`<https://github.com/ruithnadsteud/yt_georaster>`_.

Dependencies
------------

It is recommended to use a package manager, such as conda (miniconda, anaconda,
etc.) to install packages. Most of the ``yt_georaster's`` dependencies can be
installed by ``pip`` or ``conda`` automatically while installing
``yt_georaster``. There are a few notable exceptions.

yt
^^

``yt_georaster`` requires ``yt`` version 4.0, which is due to be release
imminently, but is not out yet. Thus, ``yt`` must be installed from source
in a manner similar to ``yt_georaster``. This process is detailed
:ref:`here <install-from-source>` and shown in brief below.

.. code-block:: bash

  $ git clone https://github.com/yt-project/yt
  $ cd yt
  $ pip install -e .

gdal
^^^^

The ``gdal`` library is the main dependency of ``rasterio``. Depending on your
operating system, it can be difficult to install, but there are many options,
including ``conda`` and ``pip``. If you had a particularly difficult time with
this but eventually succeeded, please consider documenting your setup here.

rasterio
^^^^^^^^

``rasterio`` is marginally easier to install than ``gdal`` and has similar
options. Add your success story here so others can benefit!

Installing from Source
----------------------

Ok, you've made it this far. Great job. To install ``yt_georaster`` from source,
do the following:

.. code-block:: bash

   $ git clone https://github.com/ruithnadsteud/yt_georaster
   $ cd yt_georaster
   $ pip install -e .

You're ready to go.
