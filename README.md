# yt_geotiff

[![CircleCI](https://circleci.com/gh/ruithnadsteud/yt_geotiff/tree/master.svg?style=shield)](https://circleci.com/gh/ruithnadsteud/yt_geotiff/tree/master)

A package for handling _geotiff_ files and georeferenced datasets within **yt**.

## Dependencies

Aside from **yt** itself, the following packages are required to use yt_geotiff:
- [numpy](https://docs.scipy.org/doc/numpy/reference/)
- [gdal](https://gdal.org/)
- [rasterio](https://rasterio.readthedocs.io/en/latest/)

## Developments and working examples

Key developments applied to the yt_geotiff package include the enabling of rasterio Window-reads. This Window-read feature allows for yt_geotiff users to read a sub-region of a multiband raster image analysis without having to read the entire image. Reading only an area of interest allows user to work more efficiently and circumvents the issue whereby the raster image size exceeds a computer's RAM. The function uses existing functionality in yt in order to define Window-read areas based on rectangular and circular yt data container shapes.

For the yt_geotiff working example below (also detailed in the "yt_geotiff/examples/Milestone_1_demo.ipynb" jupyter notebook) we have used the European Settlement Map (ESM 2017) N38E34 map tile available from the Copernicus Land Monitoring Service (source: https://land.copernicus.eu/pan-european/GHSL/european-settlement-map/esm-2012-release-2017-urban-green ). 

Import yt and the yt_geotiff extensions
```
>>> import yt
>>> import yt.extensions.geotiff
```

Users of yt_geotiff can load a raster image to first extract image metadata, including pixel dimensions and the coordinate reference system:
```
>>> ds = yt.load("200km_2p5m_N38E34.tif")

yt : [INFO     ] 2021-02-23 23:58:46,416 Parameters: domain_dimensions         = [80000 80000     1]
yt : [INFO     ] 2021-02-23 23:58:46,419 Parameters: domain_left_edge          = [3444000. 3642000.       0.] m
yt : [INFO     ] 2021-02-23 23:58:46,420 Parameters: domain_right_edge         = [3.644e+06 3.842e+06 1.000e+00] m
```
Generate rectangular yt data container for performing the yt_geotiff Window-read based on centre coordinates and width and height dimensions:
```
>>> width = ds.arr(2000., 'm')
>>> height = ds.arr(2000.,'m') 
>>> rectangle_centre = ds.arr([X,Y],'m')

>>> rectangular_yt_container = ds.rectangle_from_center(rectangle_centre,width,height)
```
Generate circular yt data container for performing the yt_geotiff Window-read based on centre coordinates and radius:
```
>>> radius = ds.arr(1000.,'m')
>>> circle_centre = ds.arr([X,Y],'m')

>>> circular_yt_container = ds.circle(circle_centre, radius)
```
Find the name of individual raster fields/bands:
```
>>> ds.field_list

[('bands', '1')]
```

Perform window-read using a yt data container for a single band:
```
>>> rectangular_yt_container[('bands','1')]
```
Query X, Y and radius fields of a yt data container:
```
>>> rectangular_yt_container['X']
>>> rectangular_yt_container['Y']
>>> rectangular_yt_container['radius']
```

Convert map unit (e.g. m) distance to pixel unit distance:
```
>>> distance = ds.arr(500., 'm')
>>> print('Number of pixels {0}'.format(distance.to('pixels')))

Number of pixels 2400.0 pixels
```

Use functionality in yt to create a plot of the window-read output. For example, rectangular window-read with dimensions of 2 x 2 km:
```
>>> rectangle_centre = ds.arr([X,Y],'m')

>>> p = ds.plot(('bands', '1'), height=(2., 'km'), width=(2., 'km'), center=rectangle_centre)
>>> p.set_log(('bands', '1'), False)
>>> p.set_cmap(('bands', '1'), 'B-W LINEAR')
>>> p.show()
```
Example plot using a circle data container with 1000 m radius:
```
>>> radius = ds.arr(1000.,'m')
>>> circle_centre = ds.arr([X,Y],'m')

>>> cp = ds.circle(circle_centre, radius)
               
>>> q = ds.plot([('bands','1')],cp)
>>> q.set_log(('bands', '1'), False)
>>> q.set_cmap(('bands', '1'), 'B-W LINEAR')
>>> q.show()
```
