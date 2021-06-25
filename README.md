# yt_georaster

[![CircleCI](https://circleci.com/gh/ruithnadsteud/yt_georaster/tree/master.svg?style=shield)](https://circleci.com/gh/ruithnadsteud/yt_georaster/tree/master)

A package for handling _geotiff_ files and georeferenced datasets within **yt**.

### Dependencies

Aside from **yt** itself, the following packages are required to use yt_georaster:
- [numpy](https://docs.scipy.org/doc/numpy/reference/)
- [gdal](https://gdal.org/)
- [rasterio](https://rasterio.readthedocs.io/en/latest/)

### Developments and working examples

Key developments applied to the yt_georaster package include:

- The enabling of rasterio Window-reads. This Window-read feature allows for yt_georaster users to read a sub-region of a multiband raster image analysis without having to read the entire image. Reading only an area of interest allows user to work more efficiently and circumvents the issue whereby the raster image size exceeds a computer's RAM. The function uses existing functionality in yt in order to define Window-read areas based on rectangular and circular yt data container shapes.

- Support the loading and querying of Sentinel-2 (Level 1C & L2A ESA processed products) and Landsat-8 satellite datasets. A collection of Sentinel-2 and Landsat-8 imagery can be queried and visualised within a user-defined  yt_georaster data container rectangle or circle shape.

- Imagery across different spatial resolutions, coordinate reference systems and spatial extents can be seamlessly loaded and queried. All imagery within a given collection for loading and querying wihtin yt_georaster are resampled accordingly in order to match the spatial resolution of the initial oad image (i.e. the base image).

- The library of derivable fields available for working with multi-band Earth observation data was been extended.

Example workflow jupyter notebooks (see Milestone_1_demo.ipynb and Milestone_2_demo.ipynb) provide a thorough demonstration of the above yt_georaster developments and links to sample data (see https://github.com/ruithnadsteud/yt_georaster/tree/master/examples). Below in an overview of the yt_georaster commands for executing these developments.

Import yt and the yt_georaster extensions
```
>>> import yt
>>> import yt.extensions.georaster
```

Users of yt_georaster can load a raster image to first extract image metadata, including pixel dimensions and the coordinate reference system:
```
>>> ds = yt.load("200km_2p5m_N38E34.tif")

yt : [INFO     ] 2021-02-23 23:58:46,416 Parameters: domain_dimensions         = [80000 80000     1]
yt : [INFO     ] 2021-02-23 23:58:46,419 Parameters: domain_left_edge          = [3444000. 3642000.       0.] m
yt : [INFO     ] 2021-02-23 23:58:46,420 Parameters: domain_right_edge         = [3.644e+06 3.842e+06 1.000e+00] m
```

### Constructing and querying data containers

Generate rectangular yt data container for performing the yt_georaster Window-read based on centre coordinates and width and height dimensions:
```
>>> width = ds.arr(2000., 'm')
>>> height = ds.arr(2000.,'m') 
>>> rectangle_centre = ds.arr([X,Y],'m')

>>> rectangular_yt_container = ds.rectangle_from_center(rectangle_centre,width,height)
```
Generate circular yt data container for performing the yt_georaster Window-read based on centre coordinates and radius:
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

### Raster image up/down sampling

Example function for generating a list of Sentinel-2 and Landsat-8 datasets in a given directory:
```
>>> def file_list():
    	directory= 'C:/path/to/sentinel_and_landsat_data/'
    	types = ('*.jp2', '*.TIF', '*.tiff') # the tuple of file types
    	filenames = ""
   		files_in_directory = []
    	for files in types:
        	files_in_directory.extend(glob.glob(directory+files))
    	return files_in_directory
```

Load list and read metadata of imagery files in. From reading the imagery metadata, yt calculates and outputs the image extents (left edge and right edge dimensions) in the coordinate reference system of the base image (first image in the file list):
```
>>> ds = yt.load(*files_in_directory)

yt : [INFO     ] 2021-04-30 14:53:27,127 Parameters: domain_dimensions         = [1830 1830    1]
yt : [INFO     ] 2021-04-30 14:53:27,145 Parameters: domain_left_edge          = [ 399960. 9890200.       0.] m
yt : [INFO     ] 2021-04-30 14:53:27,146 Parameters: domain_right_edge         = [5.0976e+05 1.0000e+07 1.0000e+00] m
```

List fields/bands/datasets that are available for querying and plotting in yt_georaster
```
>>> ds.field_list
```

Example plot of Sentinel-2 band 1 data (the base image) when queried using a rectangular data container defined using height, width and center coordinates. The yt_georaster extension image metadata is updated to reflect the change in image dimensions:
```
# Plot base image (Sentinel-2 Band 1: 60 m resolution)
>>> p = ds.plot(('bands', 'S2_B01'), height=(10., 'km'), width=(20., 'km'), center=ds.arr([471696,9989860],'m')) # s2
>>> p.set_log(('bands', 'S2_B01'), True)
>>> p.set_zlim(('bands', 'S2_B01'), 1000, 1500)
>>> p.set_cmap(('bands', 'S2_B01'), 'B-W LINEAR')
>>> p.annotate_title('Sentinel-2 band 1 at 60 m resolution')
>>> p.show()

yt : [INFO     ] 2021-04-30 14:53:29,015 xlim = 461696.000000 481696.000000
yt : [INFO     ] 2021-04-30 14:53:29,017 ylim = 9979860.000000 9999860.000000
yt : [INFO     ] 2021-04-30 14:53:29,019 xlim = 461696.000000 481696.000000
yt : [INFO     ] 2021-04-30 14:53:29,021 ylim = 9979860.000000 9999860.000000
yt : [INFO     ] 2021-04-30 14:53:29,023 Making a fixed resolution buffer of (('bands', 'S2_B01')) 800 by 800
```

Example plot of Sentinel-2 band 2 data when queried using a rectangular data container defined using height, width and center coordinates. NOTE: the band 2 image spatial resolution is down-sampled in yt_georaster from 20 to 60 m resolution in order to match the spatial resolution:
```
# Plot Sentinel-2 Band 2 (20 m resolution)
>>> q = ds.plot(('bands', 'S2_B05'), height=(10., 'km'), width=(20., 'km'), center=ds.arr([471696,9989860],'m'))# s2
>>> q.set_log(('bands', 'S2_B05'), True)
>>> q.set_cmap(('bands', 'S2_B05'), 'B-W LINEAR')
>>> q.annotate_title('Sentinel-2 band 5 resampled to 60 m resolution')
>>> q.show()

yt : [INFO     ] 2021-04-30 14:53:32,185 Resampling S2_B05: 20.0 to 60.0 m.
yt : [INFO     ] 2021-04-30 14:53:32,196 xlim = 461696.000000 481696.000000
yt : [INFO     ] 2021-04-30 14:53:32,197 ylim = 9979860.000000 9999860.000000
yt : [INFO     ] 2021-04-30 14:53:32,200 xlim = 461696.000000 481696.000000
yt : [INFO     ] 2021-04-30 14:53:32,201 ylim = 9979860.000000 9999860.000000
yt : [INFO     ] 2021-04-30 14:53:32,204 Making a fixed resolution buffer of (('bands', 'S2_B05')) 800 by 800
```

### Querying and creating yt derivable fields

List currently available derivable fields:
```
>>> ds.derived_field_list

[('band_ratios', 'S2_CDOM'),
 ('band_ratios', 'S2_EVI'),
 ('band_ratios', 'S2_MCI'),
 ('band_ratios', 'S2_NDWI'),
 ('bands', 'LS_B1'),
 ('bands', 'LS_B10'),
 ('bands', 'LS_B2'),
 ('bands', 'LS_B3'),
 ('bands', 'LS_B4'),
 ('bands', 'LS_B5'),
 ('bands', 'LS_B6'),
 ('bands', 'LS_B7'),
 ('bands', 'S2_B01'),
 ('bands', 'S2_B02'),
 ('bands', 'S2_B03'),
 ('bands', 'S2_B04'),
 ('bands', 'S2_B05'),
 ('bands', 'S2_B06'),
 ('bands', 'S2_B07'),
 ('bands', 'S2_B08'),
 ('bands', 'S2_B09'),
 ('bands', 'S2_B10'),
 ('bands', 'S2_B11'),
 ('bands', 'S2_B12'),
 ('bands', 'S2_B8A'),
 ('variables', 'LS_temperature')]
 ...

```

Creating a new derivable field (e.g. normalised difference vegetation index; NDVI):
```
# Define NDVI function 
>>> def _ndvi(field, data):
    return (data[('bands', 'S2_B8A')] - data[('bands', 'S2_B04')]) / \
           (data[('bands', 'S2_B8A')] + data[('bands', 'S2_B04')])

# Add NDVI to the derivable fields list
>>> ds.add_field(("band_ratios", "S2_NDVI"), function=_ndvi,
                 units="", display_name='NDVI', take_log=False, sampling_type='local')
```

Example plot script of a derivable fields:
```
>>> width = ds.quan(19, 'km')
>>> height = ds.quan(12,'km')
>>> rectangle_centre =ds.arr([471696,9989860],'m')
>>> p = ds.plot(('band_ratios', 'S2_NDVI'), height=height, width=width, center=rectangle_centre)
>>> p.set_log(('band_ratios', 'S2_NDVI'), False)
>>> p.set_cmap(('band_ratios', 'S2_NDVI'), 'RdYlGn')
>>> p.show()
```

### Saving to a new GeoTiff file

The `save_as_geotiff` function allows one to output multiple fields
into a single multi-band GeoTiff file. This can be done for either the
entire image or for a subset represented by geometric data container.

```
>>> import glob
>>> import yt
>>> from yt.extensions.georaster import save_as_geotiff
>>>
>>> fns = glob.glob("*.jp2") + glob.glob("*.TIF")
>>> ds = yt.load(*fns)
>>> ds_fn, field_map = save_as_geotiff(ds, "my_data.tif")
>>> ds_new = yt.load(ds_fn, field_map=field_map)
```

A supplementary yaml file containing a map between band numbers and
field names will also be written.

By default, all available on-disk fields will be saved, but a list,
including derived fields can provided. As well, a data container can
be provided for which data will only be saved for the rectangular
bounding box enclosing the container.

```
>>> import glob
>>> import yt
>>> from yt.extensions.georaster import save_as_geotiff
>>>
>>> fns = glob.glob("*.jp2") + glob.glob("*.TIF")
>>> ds = yt.load(*fns)
>>> circle = ds.circle(ds.domain_center, (10, 'km'))
>>> fields = [("bands", "LS_B1"),
...           ("bands", "S2_B06"),
...           ("band_ratios", "S2_NDWI"),
...           ("variables", "LS_temperature")]
>>> ds_fn, field_map = save_as_geotiff(
...        ds, "my_data.tiff",
...        fields=fields, data_source=circle)
>>> ds_new = yt.load(ds_fn, field_map=field_map)
```

### Querying and plotting polygon Window reads

Window reads can also be performed within yt_georaster based on the extents of single and multiple feature polygon shapefile (.shp) datasets.

```
>>> import yt
>>> import yt.extensions.georaster
```
Load Raster dataset (e.g., Landsat8, Band1) into yt_georaster
```
>>> landsat_data = "C:/path/to/Landsat_test_data/LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF"
>>> ds = yt.load(landsat_data
yt : [INFO     ] 2021-05-31 12:58:36,740 Parameters: domain_dimensions         = [7581 7741    1]
yt : [INFO     ] 2021-05-31 12:58:36,743 Parameters: domain_left_edge          = [ 361485. -116415.       0.] m
yt : [INFO     ] 2021-05-31 12:58:36,744 Parameters: domain_right_edge         = [5.88915e+05 1.15815e+05 1.00000e+00] m
```

Load and read a polygon shapefile into yt_georaster
```
>>> multi_shapefile = "C:/path/to/esri_shapefile/multi_feature_polygon.shp"
>>> polyon = ds.polygon(multi_shapefile)
Number of features in file: 4
```

Query Raster dataset field/band using the polygon dataset
```
>>> data_in_polygon = (poly[('bands', '1')])
```

Plotting polygon read data in yt_georaster
