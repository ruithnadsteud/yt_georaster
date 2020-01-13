# yt_geotiff
A package for handling _geotiff_ files and georeferenced datasets within **yt**.

## Dependencies

Aside from **yt** itself, the following packages are required to use yt_geotiff:
- [numpy](https://docs.scipy.org/doc/numpy/reference/)
- [gdal](https://gdal.org/)
- [rasterio](https://rasterio.readthedocs.io/en/latest/)

## Capabilities

Currently this package is still in its early development stage. Once this stage is fully implemented, the package will have the following capabilities:
- Read _geotiff_ files into **yt** using the yt.load function
- Manage multiband files
- Enable the selection of sub-regions for analysis

The aim of this is to enable inspection and analysis of georeferenced data with **yt** to take advantage of its existing capabilities.
