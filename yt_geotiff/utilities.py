"""
Utility functions for yt_geotiff.



"""
import numpy as np
import rasterio
from unyt import unyt_array, unyt_quantity, uconcatenate
import yaml

import yt.geometry.selection_routines as selector_shape
from yt.utilities.logger import ytLogger

import os

def coord_cal(xcell, ycell, transform):
    """Function to calculate the position of cell (xcell, ycell) in terms of
    longitude and latitude"""

    # note dy is -ve
    dx, rotx, xmin, roty, dy, ymax = transform[0:6]
    xp = xmin + dx/2 + dx*xcell + rotx*ycell
    yp = ymax + dy/2 + dy*ycell + roty*xcell

    return xp, yp


def left_aligned_coord_cal(xcell, ycell, transform):
    """Function to calculate the position of cell (xcell, ycell) in terms of
    distance from the top left corner using the longitude and latitude of
    the cell and the Earth radius to calculate an arc distance.
    This is required for yt as it needs to work with the distances rather than
    degrees.
    """

    dx, rotx, xmin, roty, dy, ymax = transform[0:6]
    xp, yp = coord_cal(xcell, ycell, transform)
    # convert to meters
    x_arc_dist = (xp - xmin)
    y_arc_dist = (ymax - yp)
    return x_arc_dist, y_arc_dist


def parse_awslandsat_metafile(filename, flatdict=True):
    """Function to read in metadata/parameter file and output it as a dict.
    """

    f = open(filename, 'r')
    groupkeys = []

    data = {}

    while True:

        # Get next line from file
        line = f.readline().strip().replace('"', '').replace('\n', '')

        # if line is empty
        # end of file is reached
        if not line or line == 'END':
            break
        key, value = line.split(' = ')

        # make sure we have all of value if it is an array
        while value.count('(') != value.count(')'):
            line = f.readline().strip().replace('"', '').replace('\n', '')
            value += line

        # save to data dictionary
        if key == 'GROUP':
            groupkeys.append(value)
        elif key == 'END_GROUP':
            groupkeys.pop()
        else:
            if flatdict:
                data[key] = value
            else:
                data[tuple(groupkeys + [key])] = value

    f.close()

    return data


def save_as_geotiff(ds, filename, fields=None, data_source=None):
    r"""
    Export georeferenced data to a reloadable geotiff.

    Data will be exported as a geotiff file that can be reloaded with
    yt. The output data will be resampled to the resolution of the
    dataset's base image (i.e., the first in the list of filenames
    passed to yt.load). By default, the physical bounds of the saved
    data will be the bounds of the loaded dataset (i.e., from
    domain_left_edge to domain_right_edge). Optionally, a data container
    can be provided and only data contained within the rectangular
    bounding box surrounding the container will be saved. A
    supplementary yaml file will be written with a map from GeoTiff
    band number to field names.

    Parameters
    ----------
    ds : dataset
        The georeferenced dataset to be saved.
    filename : str
        The name of the file to be written.
    fields : optional, list of tuples
        List of fields to be saved. If none provided, all on-disk
        fields will be saved.
    data_source : optional, :class:`~yt.data_objects.data_containers.YTDataContainer`
        The data container from which data will be selected for saving.
        All data contained within the rectangular bounding box (for
        example, if the data container is a sphere) will be saved. If
        none provided, all data within the dataset's domain will be saved.

    Returns
    -------
    (data_filename, filemap_filename) : tuple of strings
        The names of the data file and field map file.

    Examples
    --------

    >>> import yt
    >>> from yt.extensions.geotiff import save_as_geotiff
    >>>
    >>> fns = glob.glob("*.jp2") + glob.glob("*.TIF")
    >>> ds = yt.load(fns)
    >>>
    >>> new_fn, new_fmap = save_as_dataset(ds, "one_file_to_rule_them_all.tif")
    >>>
    >>> ds_new = yt.load(new_fn, field_map=new_fmap)

    >>> circle = ds.circle(ds.domain_center, (10, 'km'))
    >>> fields = [("bands", "LS_B1"),
    ...           ("bands", "S2_B06"),
    ...           ("band_ratios", "S2_NDWI")]
    >>> save_as_geotiff(ds, "my_data.tiff", fields=fields, data_source=circle)
    """

    exts = ("tif", "tiff")
    prefix, suffix = filename.rsplit(".", 1)
    if suffix.lower() not in exts:
        raise ValueError(
            f"Invalid filename extension ({filename}), must be one of {exts}.")

    if fields is None:
        fields = ds.field_list

    if data_source is None:
        data_source = ds.all_data()

    wgrid = ds.index.grids[0]._get_window_grid(data_source.selector)

    width, height = wgrid.ActiveDimensions[:2]
    ytLogger.info(f"Saving {len(fields)} fields to {filename}.")
    ytLogger.info(f"Bounding box: {wgrid.LeftEdge[:2]} - "
                  f"{wgrid.RightEdge[:2]} with shape {width,height}.")

    dtype = ds.index.io._field_dtype
    transform = ds._update_transform(
        ds.parameters["transform"],
        wgrid.LeftEdge,
        wgrid.RightEdge)

    # get the mask to remove data not in the container
    mask = data_source.selector.fill_mask(wgrid)[..., 0]

    field_info = {}
    with rasterio.open(filename,
                       'w',
                       driver='GTiff',
                       height=height,
                       width=width,
                       count=len(fields),
                       dtype=dtype,
                       crs=ds.parameters['crs'],
                       transform=transform,
                       ) as dst:
        for i, field in enumerate(fields):
            band = i + 1
            fname = f"band_{band}"
            ytLogger.info(f"Saving {field} to band {band}/{len(fields)}.")
            field_info[fname] = {"field_type": field[0], "field_name": field[1]}
            for attr in ["take_log", "units"]:
                field_info[fname][attr] = getattr(ds.field_info[field], attr)
            data = wgrid[field].d[..., 0]
            data[~mask] = 0
            if ds._flip_axes:
                data = np.flip(data, axis=ds._flip_axes)
            data = data.T
            dst.write(data, band)

    yfn = f"{filename[:filename.rfind('.')]}_fields.yaml"
    with open(yfn, mode="w") as f:
        yaml.dump({prefix: field_info}, stream=f)
    ytLogger.info(f"Field map saved to {yfn}.")
    ytLogger.info(f"Save complete. Reload data with:\n"
                  f"ds = yt.load(\"{filename}\", field_map=\"{yfn}\")")

    return (filename, yfn)

def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def rasterio_window_calc(selector):
    """
    This function reads information from either a sphere,
    box or region selector object and outputs the
    dimensions of a container: left edge, right edge,
    width and height.
    """

    if isinstance(selector, selector_shape.SphereSelector):

        selector_left_edge = np.array(selector.center)
        selector_left_edge[:2] -= selector.radius
        selector_right_edge = np.array(selector.center)
        selector_right_edge[:2] += selector.radius
        selector_width = selector.radius*2
        selector_height = selector_width

    elif isinstance(selector, selector_shape.RegionSelector):

        selector_left_edge = selector.left_edge
        selector_right_edge = selector.right_edge
        selector_width = selector.right_edge[0] - selector.left_edge[0]
        selector_height = selector_width

    return selector_left_edge, selector_right_edge,\
        selector_width, selector_height


def validate_coord_array(ds, coord, name, padval, def_units):
    """
    Take a length 2 or 3 array and return a length 3 array.
    If array is length 2, use padval for third value.
    """
    if not isinstance(coord, np.ndarray):
        raise ValueError(
            f"{name} argument must be array-like: {coord}.")

    if coord.size == 3:
        return coord
    if coord.size != 2:
        raise ValueError(
            f"{name} argument must be of size 2 or 3.")

    if isinstance(coord, unyt_array):
        cfunc = uconcatenate
        afunc = ds.arr
        units = coord.units
        padval = ds.arr([padval])
    elif isinstance(coord, np.ndarray):
        cfunc = np.concatenate
        afunc = np.array
        units = "code_length"

    newc = cfunc([coord, afunc(padval.to(units))])
    return newc


def validate_quantity(ds, value, units):
    """
    Take a unyt_quantity, float, or (float, string) tuple
    and return a unyt_quantity.
    """

    if hasattr(value, "units") and not isinstance(value, unyt_quantity):
        raise ValueError("value must be a quantity, not an array. "
                         "Use ds.quan instead of ds.arr.")
    if isinstance(value, unyt_quantity):
        return value
    elif isinstance(value, (tuple, list)):
        value = ds.quan(*value)
    else:
        value = ds.quan(value, units)
    return value

def s1_geocode(path, filename):
    """
    A quick example of handling transforms from gcps with rasterio.
    """
    
    """Main function."""
    # open the file
    with rasterio.open(os.path.join(path, filename)) as src:
        #meta = src.meta
        #array = src.read(1)
        gcps, crs = src.get_gcps()  # get crs and gcps
        transform = rasterio.transform.from_gcps(gcps)  # get transform
    
    
    # temp_file = "s1_"+polarisation+"_temp.tiff"
    # output_path = path_to_sen1_tiff.parent / temp_file

    return crs, transform
    # with rasterio.Env():
    #     # update the metadata
    #     new_meta = meta.copy()
    #     new_meta.update(
    #         crs=crs,
    #         transform=transform
    #     )
    #     #print("old: ", meta)
    #     #print("new: ", new_meta)
    #     # save to file
    #     with rasterio.open(output_path, "w", **new_meta) as dst:
    #         dst.write(array, 1)
    # reload that data to double check
    #with rasterio.open(output_path) as src:
    #    reloaded_meta = src.meta
    #    new_array = src.read(1)
    # does this change the data in anyway?
    #print("meta the same? ", reloaded_meta == new_meta)
    #print("data the same? ", (new_array == array).all())

def s1_polarisation(filename):
    if "vv" in filename: 
        pol = "VV"
    elif "vh" in filename:
        pol="VH"
    return pol

def s1_data_manager(path, filename):
    # Geocode S1 image      
    s1_crs, s1_transform = s1_geocode(path, filename)
    field_label = ('bands', ("S1_"+s1_polarisation(filename)))
    #self.ds.parameters['crs'] = s1_crs
    #self.ds.parameters['crs'] = s1_transform
    return field_label

class log_level():
    """
    Context manager for setting log level.
    """
    def __init__(self, minlevel, mylog=None):
        if mylog is None:
            mylog = ytLogger
        self.mylog = mylog
        self.minlevel = minlevel
        self.level = mylog.level

    def __enter__(self):
        if self.level > 10 and self.level < self.minlevel:
            self.mylog.setLevel(40)

    def __exit__(self, *args):
        self.mylog.setLevel(self.level)
