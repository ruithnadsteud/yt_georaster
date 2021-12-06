"""
Utility functions for yt_georaster.



"""
import numpy as np
import rasterio
from unyt import unyt_array, unyt_quantity, uconcatenate
import yaml

from yt.utilities.logger import ytLogger


def save_as_geotiff(ds, filename, fields=None, data_source=None,
    dtype=None, nodata=None):
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
    dtype : optional, str or recognised dtype object
        The desired data type to output the data in. The data will be naively 
        converted into this type and an attempt will be made to save using this
        type. Must be an int or float based type.
    nodata : optional, int/float
        The nodata value to use when applying mask before saving and also to
        save to output geotiff metadata.

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
    >>> fields = [("LC08_L2SP_171060_20210227_20210304_02_T1", "LS_B1"),
    ...           ("T36MVE_20210315T075701", "S2_B06"),
    ...           ("T36MVE_20210315T075701", "NDWI")]
    >>> save_as_geotiff(ds, "my_data.tif", fields=fields, data_source=circle)
    """

    exts = ("tif", "tiff")
    prefix, suffix = filename.rsplit(".", 1)
    if suffix.lower() not in exts:
        raise ValueError(
            f"Invalid filename extension ({filename}), must be one of {exts}."
        )

    if nodata is None:
        nodata = ds.parameters['profile']['nodata']

    if fields is None:
        fields = ds.field_list

    if data_source is None:
        data_source = ds.all_data()

    wgrid = ds.index.grids[0]._get_window_grid(data_source.selector)

    width, height = wgrid.ActiveDimensions[:2]
    ytLogger.info(f"Saving {len(fields)} fields to {filename}.")
    ytLogger.info(
        f"Bounding box: {wgrid.LeftEdge[:2]} - "
        f"{wgrid.RightEdge[:2]} with shape {width,height}."
    )

    if dtype is None:
        dtype = ds.parameters['profile']['dtype']

    if not (np.dtype(ds.index.io._field_dtype) is np.dtype(dtype)):
        ytLogger.info(f"{filename} dtype set to {dtype}.")

    transform = ds._update_transform(
        ds.parameters["transform"], wgrid.LeftEdge, wgrid.RightEdge
    )

    # get the mask to remove data not in the container
    mask = data_source.selector.fill_mask(wgrid)[..., 0]

    field_info = {}
    with rasterio.open(
        filename,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=len(fields),
        dtype=dtype,
        nodata=nodata,
        crs=ds.parameters["crs"],
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
            data = data.T.astype(dtype)
            dst.write(data, band)

    yfn = f"{filename[:filename.rfind('.')]}_fields.yaml"
    with open(yfn, mode="w") as f:
        yaml.dump({prefix: field_info}, stream=f)
    ytLogger.info(f"Field map saved to {yfn}.")
    ytLogger.info(
        f"Save complete. Reload data with:\n"
        f'ds = yt.load("{filename}", field_map="{yfn}")'
    )

    return (filename, yfn)


def validate_coord_array(ds, coord, name, padval, def_units):
    """
    Take a length 2 or 3 array and return a length 3 array.
    If array is length 2, use padval for third value.
    """
    if not isinstance(coord, np.ndarray):
        raise ValueError(f"{name} argument must be array-like: {coord}.")

    if coord.size == 3:
        return coord
    if coord.size != 2:
        raise ValueError(f"{name} argument must be of size 2 or 3.")

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
        raise ValueError(
            "value must be a quantity, not an array. " "Use ds.quan instead of ds.arr."
        )
    if isinstance(value, unyt_quantity):
        return value
    elif isinstance(value, (tuple, list)):
        value = ds.quan(*value)
    else:
        value = ds.quan(value, units)
    return value


class log_level:
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
