# yt_georaster

[![CircleCI](https://circleci.com/gh/ruithnadsteud/yt_georaster/tree/master.svg?style=shield)](https://circleci.com/gh/ruithnadsteud/yt_georaster/tree/master)
[![Coverage Status](https://coveralls.io/repos/github/ruithnadsteud/yt_georaster/badge.svg?branch=master)](https://coveralls.io/github/ruithnadsteud/yt_georaster?branch=master)
[![Documentation Status](https://readthedocs.org/projects/yt-georaster/badge/?version=latest)](https://yt-georaster.readthedocs.io/en/latest/?badge=latest)
[![yt-project](https://img.shields.io/static/v1?label="works%20with"&message="yt"&color="blueviolet")](https://yt-project.org)

``yt_georaster`` is a [yt](https://yt-project.org/>) extension for
analyzing geotagged image files that are loadable with
[rasterio](https://rasterio.readthedocs.io/). The ``yt_georaster``
extension combines ``yt`` and ``rasterio``, allowing users to query
data contained within geometric shapes, like circles, rectangles, and
arbitrary polygons saved as
[Shapefiles](https://en.wikipedia.org/wiki/Shapefile). Multiple images
with different resolutions and coordinate reference systems can be
loaded together. All queried data is transformed to the same
resolution and coordinate reference system and returned as NumPy
arrays of the same shape. Data from multiple images can also be
re-saved to a single, multiband
[GeoTIFF](https://en.wikipedia.org/wiki/GeoTIFF) file.

## Additional Resources

- source code repository: https://github.com/ruithnadsteud/yt_georaster
- online documentation: https://yt-georaster.readthedocs.io/
