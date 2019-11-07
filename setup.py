
from setuptools import setup

def get_version(filename):
    """
    Get version from a file.
    Inspired by https://github.mabuchilab/QNET/.
    """
    with open(filename) as f:
        for line in f.readlines():
            if line.startswith("__version__"):
                return line.split("=")[1].strip()[1:-1]
    raise RuntimeError(
        "Could not get version from %s." % filename)


VERSION = get_version("geotiff/__init__.py")

setup(name="yt_geotiff",
      version=VERSION,
      description="A package for handling geotiff files and georeferenced datasets within yt.",
      author="Daniel Eastwood",
      author_email="eastwooddans@gmail.com",
      license="BSD",
      url="https://github.com/deastwoo/yt_geotiff",
      packages=["yt_geotiff"],
      keywords=["GeoTiff", "GTiff", "raster"],
      install_requires=[
          'rasterio',
          'gdal',
          'numpy',
      ],
      classifiers=[
          "Development Status :: 2 - Pre-Alpha",
          "Environment :: Console",
          "Intended Audience :: Science/Research",
          "License :: OSI Approved :: BSD License",
          "Operating System :: MacOS :: MacOS X",
          "Operating System :: POSIX :: AIX",
          "Operating System :: POSIX :: Linux",
          "Programming Language :: Python",
          "Topic :: Utilities",
          ],
      )