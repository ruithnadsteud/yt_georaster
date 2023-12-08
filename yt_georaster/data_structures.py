import functools
import math
import numpy as np
import rasterio
from rasterio import warp
from rasterio.windows import from_bounds, Window
from rasterio.crs import CRS
import re
import weakref

from unyt import dimensions

from yt.data_objects.static_output import Dataset
from yt.data_objects.selection_objects.data_selection_objects import (
    YTSelectionContainer,
)
from yt.funcs import mylog
from yt.geometry.selection_routines import (
    DiskSelector,
    GridSelector,
    RegionSelector,
    SphereSelector,
)
from yt.frontends.ytdata.data_structures import YTGridHierarchy, YTGrid
from yt.utilities.parallel_tools.parallel_analysis_interface import parallel_root_only
from yt.visualization.api import SlicePlot

from yt_georaster.polygon import YTPolygon, PolygonSelector
from yt_georaster.fields import GeoRasterFieldInfo
from yt_georaster.image_types import GeoManager
from yt_georaster.utilities import validate_coord_array, validate_quantity, log_level


class GeoRasterWindowGrid(YTGrid):
    """
    Grid representing the bounding box around a data container.

    This defines a grid spanning a subset of the total image. We
    use this to limit geometric selection to the bounding box and
    then perform a rasterio window read to get data only from this
    area.
    """

    def __init__(self, gridobj, left_edge, right_edge, window):

        YTSelectionContainer.__init__(self, gridobj._index.dataset, None)

        self.id = gridobj.id
        self._child_mask = gridobj._child_indices = gridobj._child_index_mask = None
        self.ds = gridobj._index.dataset
        self._index = gridobj._index
        self.start_index = None
        self.filename = gridobj.filename
        self._last_mask = None
        self._last_count = -1
        self._last_selector_id = None
        self._children_ids = []
        self._parent_id = -1
        self.Level = 0

        self.LeftEdge = self.ds.arr(left_edge, self.ds.parameters['units'])
        self.RightEdge = self.ds.arr(right_edge, self.ds.parameters['units'])
        # Make sure z dimension edges are the same as parent grid.
        self.LeftEdge[2] = gridobj.LeftEdge[2]
        self.RightEdge[2] = gridobj.RightEdge[2]
        ad_z = int((self.RightEdge[2] - self.LeftEdge[2])/gridobj.dds[2])
        self.ActiveDimensions = np.array(
            [window.width, window.height, ad_z],
            dtype=np.int32
        )
        # Inherit dx values from parent.
        self.dds = gridobj.dds

    def __repr__(self):
        ad = self.ActiveDimensions
        return f"GeoRasterWindowGrid ({ad[0]}x{ad[1]})"

    def _get_rasterio_window(
        self, selector, image_crs, transform, bounds_crs=None
    ):
        if bounds_crs is None:
            bounds_crs = self.ds.parameters["crs"]
        left, bottom, _ = self.LeftEdge
        right, top, _ = self.RightEdge
        if self.ds._parse_crs(bounds_crs) != self.ds._parse_crs(image_crs):
            new_bounds = warp.transform_bounds(
                bounds_crs,
                image_crs,
                left,
                bottom,
                right,
                top
            )
        else:
            new_bounds = (left.d, bottom.d, right.d, top.d)
        window = from_bounds(
            *new_bounds, transform
        )


        return window

    def _get_trimmed_rasterio_window(
            self, selector, image_crs, image_transform, bounds_crs=None
    ):
        """
        Create rasterio window which fully encompases our selector
        """
        window = self._get_rasterio_window(selector, image_crs, image_transform, bounds_crs=None)

        col_off, row_off, wwidth, wheight = window.flatten()
        # left and right edges are already rounded to enclosing pixels
        # only need to round to nearest whole pixel
        rnd_col_off = math.floor(col_off + 0.5)
        rnd_row_off = math.floor(row_off + 0.5)
        wwidth = math.floor(col_off + wwidth + 0.5) - rnd_col_off
        wheight = math.floor(row_off + wheight + 0.5) - rnd_row_off

        window = Window(rnd_col_off, rnd_row_off, wwidth, wheight)

        return window

    def _get_full_rasterio_window(
            self, selector, image_crs, image_transform, bounds_crs=None
    ):
        """
        Create rasterio window which fully encompases our selector
        """
        window = self._get_rasterio_window(selector, image_crs, image_transform, bounds_crs=None)
        
        col_off, row_off, wwidth, wheight = window.flatten()
        # need to ensure we capture all pixels that overlap selector
        # floor offsets and ceil lengths
        rnd_col_off = math.floor(col_off)
        rnd_row_off = math.floor(row_off)
        wwidth = math.ceil(col_off + wwidth) - rnd_col_off
        wheight = math.ceil(row_off + wheight) - rnd_row_off

        window = Window(rnd_col_off, rnd_row_off, wwidth, wheight)

        return window

    def _get_rasterio_window_transform(self, selector, crs, base_crs=None, full=False):
        """
        Calculate default transform, width, and height for a rasterio window read.
        """

        if base_crs is None:
            base_crs = self.ds.parameters["crs"]
        
        if full:
            base_window = self._get_full_rasterio_window(
                selector, base_crs, self.ds.parameters["transform"], bounds_crs=crs
            )
        else:
            base_window = self._get_trimmed_rasterio_window(
                selector, base_crs, self.ds.parameters["transform"], bounds_crs=crs
            )

        base_window_transform = rasterio.windows.transform(base_window, self.ds.parameters["transform"])

        return base_window_transform, base_window.width, base_window.height


class GeoRasterGrid(YTGrid):
    """
    Grid object for GeoRasterDataset representing an entire image.
    """

    _last_wgrid = None
    _last_wgrid_id = None

    def select(self, selector, source, dest, offset):
        if isinstance(selector, GridSelector):
            return super().select(selector, source, dest, offset)
        wgrid = self._get_window_grid(selector)
        rvalue = wgrid.select(selector, source, dest, offset)
        return rvalue

    def count(self, selector):
        if isinstance(selector, GridSelector):
            return super().count(selector)
        wgrid = self._get_window_grid(selector)
        rvalue = wgrid.count(selector)
        return rvalue

    def _get_selector_mask(self, selector):
        if isinstance(selector, GridSelector):
            return super()._get_selector_mask(selector)
        wgrid = self._get_window_grid(selector)
        rvalue = wgrid._get_selector_mask(selector)
        return rvalue

    def select_icoords(self, dobj):
        if isinstance(dobj.selector, GridSelector):
            return super().select_icoords(dobj)
        wgrid = self._get_window_grid(dobj.selector)
        rvalue = wgrid.select_icoords(dobj)
        return rvalue

    def select_fcoords(self, dobj):
        if isinstance(dobj.selector, GridSelector):
            return super().select_fcoords(dobj)
        wgrid = self._get_window_grid(dobj.selector)
        rvalue = wgrid.select_fcoords(dobj)
        return rvalue

    def select_fwidth(self, dobj):
        if isinstance(dobj.selector, GridSelector):
            return super().select_fwidth(dobj)
        wgrid = self._get_window_grid(dobj.selector)
        rvalue = wgrid.select_fwidth(dobj)
        return rvalue

    def select_ires(self, dobj):
        if isinstance(dobj.selector, GridSelector):
            return super().select_ires(dobj)
        wgrid = self._get_window_grid(dobj.selector)
        rvalue = wgrid.select_ires(dobj)
        return rvalue

    def count_particles(self, dobj):
        if isinstance(dobj.selector, GridSelector):
            return super().count_particles(dobj)
        wgrid = self._get_window_grid(dobj.selector)
        rvalue = wgrid.count_particles(dobj)
        return rvalue

    def select_particles(self, dobj):
        if isinstance(dobj.selector, GridSelector):
            return super().select_particles(dobj)
        wgrid = self._get_window_grid(dobj.selector)
        rvalue = wgrid.select_particles(dobj)
        return rvalue

    def select_blocks(self, dobj):
        if isinstance(dobj.selector, GridSelector):
            return super().select_blocks(dobj)
        wgrid = self._get_window_grid(dobj.selector)
        rvalue = wgrid.select_blocks(dobj)
        return rvalue

    def _get_window_grid(self, selector):
        """
        Return a GeoRasterWindowGrid for a given selector.
        """

        if self._last_wgrid and hash(selector) == self._last_wgrid_id:
            return self._last_wgrid

        left_edge, right_edge = self._get_selection_window(selector)
        w = self._get_trimmed_rasterio_window(selector, self.ds.parameters['crs'], self.ds.parameters['transform'])
        wgrid = GeoRasterWindowGrid(self, left_edge, right_edge, w)
        self._last_wgrid = wgrid
        self._last_wgrid_id = hash(selector)
        return wgrid

    def _get_selection_window(self, selector):
        """
        Calculate bounding box for selectors.
        """

        dle = self.ds.domain_left_edge.d
        dre = self.ds.domain_right_edge.d

        if isinstance(selector, (DiskSelector, SphereSelector)):
            left_edge = np.array(selector.center)
            left_edge[:2] -= selector.radius
            left_edge[2] = dle[2]

            right_edge = np.asarray(selector.center)
            right_edge[:2] += selector.radius
            right_edge[2] = dre[2]

        elif isinstance(selector, RegionSelector):
            left_edge = np.array(selector.left_edge)
            right_edge = np.array(selector.right_edge)

        elif isinstance(selector, PolygonSelector):
            left_edge, right_edge = selector.dobj._get_bbox()
            left_edge = left_edge.d
            right_edge = right_edge.d

        else:
            left_edge = dle
            right_edge = dre
        left_edge = np.floor((left_edge - dle)/self.dds) * self.dds + dle
        right_edge = np.ceil((right_edge - dle)/self.dds) * self.dds + dle
        
        return left_edge, right_edge

    def _get_rasterio_window(
        self, selector, image_crs, image_transform, bounds_crs=None
    ):
        """
        Calculate position, width, and height for a rasterio window read.
        """

        if bounds_crs is None:
            bounds_crs = self.ds.parameters["crs"]

        left_edge, right_edge = self._get_selection_window(selector)
        left, bottom, _ = left_edge
        right, top, _ = right_edge

        if self.ds._parse_crs(bounds_crs) != self.ds._parse_crs(image_crs):
            new_bounds = warp.transform_bounds(
                bounds_crs,
                image_crs,
                left,
                bottom,
                right,
                top
            )
        else:
            new_bounds = (left.d, bottom.d, right.d, top.d)

        window = from_bounds(
            *new_bounds, image_transform
        )

        return window

    def _get_trimmed_rasterio_window(
            self, selector, image_crs, image_transform, bounds_crs=None
    ):
        """
        Create rasterio window which fully encompases our selector
        """
        window = self._get_rasterio_window(selector, image_crs, image_transform, bounds_crs=None)

        col_off, row_off, wwidth, wheight = window.flatten()
        # left and right edges are already rounded to enclosing pixels
        # only need to round to nearest whole pixel
        rnd_col_off = math.floor(col_off + 0.5)
        rnd_row_off = math.floor(row_off + 0.5)
        wwidth = math.floor(col_off + wwidth + 0.5) - rnd_col_off
        wheight = math.floor(row_off + wheight + 0.5) - rnd_row_off

        window = Window(rnd_col_off, rnd_row_off, wwidth, wheight)

        return window

    def _get_full_rasterio_window(
            self, selector, image_crs, image_transform, bounds_crs=None
    ):
        """
        Create rasterio window which fully encompases our selector
        """
        window = self._get_rasterio_window(selector, image_crs, image_transform, bounds_crs=None)
        
        col_off, row_off, wwidth, wheight = window.flatten()
        # need to ensure we capture all pixels that overlap selector
        # floor offsets and ceil lengths
        rnd_col_off = math.floor(col_off)
        rnd_row_off = math.floor(row_off)
        wwidth = math.ceil(col_off + wwidth) - rnd_col_off
        wheight = math.ceil(row_off + wheight) - rnd_row_off

        window = Window(rnd_col_off, rnd_row_off, wwidth, wheight)

        return window

    def _get_rasterio_window_transform(self, selector, crs, base_crs=None, full=False):
        """
        Calculate default transform, width, and height for a rasterio window read.
        """

        if base_crs is None:
            base_crs = self.ds.parameters["crs"]
        
        if full:
            base_window = self._get_full_rasterio_window(
                selector, base_crs, self.ds.parameters["transform"], bounds_crs=crs
            )
        else:
            base_window = self._get_trimmed_rasterio_window(
                selector, base_crs, self.ds.parameters["transform"], bounds_crs=crs
            )

        base_window_transform = rasterio.windows.transform(base_window, self.ds.parameters["transform"])

        return base_window_transform, base_window.width, base_window.height

    def __repr__(self):
        ad = self.ActiveDimensions
        return f"GeoRasterGrid ({ad[0]}x{ad[1]})"


class GeoRasterHierarchy(YTGridHierarchy):
    """
    Hierarchy class for GeoRasterDataset.

    This makes use of the GeoManager to identify fields.
    """

    grid = GeoRasterGrid

    def _count_grids(self):
        self.num_grids = 1

    def _detect_output_fields(self):
        self.field_list = []
        self.ds.field_units = self.ds.field_units or {}

        # The geo manager identifies files with various imagery/satellite
        # naming conventions.
        self.geo_manager = gm = GeoManager(self, field_map=self.ds.field_map)
        gm.process_files(self.ds.filename_list)

        ftypes = set(self.ds.fluid_types)
        new_ftypes = set(gm.ftypes)
        self.ds.fluid_types = tuple(ftypes.union(new_ftypes))


class GeoRasterDataset(Dataset):
    """
    Dataset class for rasterio-loadable images.
    """

    _index_class = GeoRasterHierarchy
    _field_info_class = GeoRasterFieldInfo
    _dataset_type = "GeoRaster"
    _valid_extensions = (".tif", ".tiff", ".jp2")
    _driver_types = ("GTiff", "JP2OpenJPEG")
    geometry = "cartesian"
    default_fluid_type = None
    fluid_types = ("index",)
    _periodicity = np.zeros(3, dtype=bool)
    cosmological_simulation = False
    refine_by = 2
    _con_attrs = ()

    def __init__(self, *args, field_map=None, crs=None, nodata=None,
                 scale_factor=None, resample_method=warp.Resampling.nearest):
        self.filename_list = args
        filename = args[0]
        self.scale_factor = scale_factor
        self.field_map = field_map
        self.crs = crs
        self.nodata = nodata
        self.resample_method = self._parse_resample_method(resample_method)
        
        
        super().__init__(filename, self._dataset_type, unit_system="mks")
        self.data = self.index.grids[0]
        self._added_fields = []

    def add_field(self, *args, **kwargs):
        self._added_fields.append({"args": args, "kwargs": kwargs})
        super().add_field(*args, **kwargs)

    @parallel_root_only
    def print_key_parameters(self):
        for a in [
            "domain_dimensions",
            "domain_left_edge",
            "domain_right_edge",
        ]:
            if not hasattr(self, a):
                mylog.error("Missing %s in parameter file definition!", a)
                continue
            v = getattr(self, a)
            mylog.info("Parameters: %-25s = %s", a, v)

    def _parse_parameter_file(self):
        self.num_particles = {}
        with rasterio.open(self.parameter_filename, "r") as f:
            for key in f.meta.keys():
                v = f.meta[key]
                self.parameters[key] = v
            self.parameters["res"] = f.res
            self.parameters["profile"] = f.profile
            self.parameters["bounds"] = f.bounds
        self.current_time = 0

        # overwrite crs if one is provided by user
        if self.crs is not None:
            # make sure user provided CRS is valid CRS object
            self.crs = self._parse_crs(self.crs)

            # get reprojected transform
            transform, width, height = warp.calculate_default_transform(
                self.parameters["crs"],
                self.crs,
                self.parameters["width"],
                self.parameters["height"],
                *self.parameters["bounds"],
                resolution=self.parameters["res"] # the resolution remains fixed
            )
            # update parameters
            _profile = {
                "crs": self.crs,
                "transform": transform,
                "width": width,
                "height": height
            }
            self.parameters.update(_profile)
            self.parameters["profile"].update(_profile)
            # updated bounds
            self.parameters["bounds"] = warp.transform_bounds(
                self.parameters["crs"],
                self.crs,
                *self.parameters["bounds"]
            )
        else:
            # if no crs has be provided replace None with base image CRS
            self.crs = self.parameters["crs"]

        # get units and conversion factor to metres
        self.parameters["units"] = self.parameters["crs"].linear_units
        # for non-projected crs this is unknown
        if self.parameters["units"] == 'unknown':
            mylog.warning(
                f"Dataset CRS {self.parameters['crs']} "
                "units are 'unknown'. Using meters."
            )
            self.parameters["units"] = 'm'  # just a place holder
        else:
            mylog.info(
                f"Dataset CRS {self.parameters['crs']} "
                f"units are '{self.parameters['units']}'. "
            )

        # set nodata value
        if self.nodata is not None:
            if self.parameters['nodata'] is not None:
                mylog.warning(
                    f"Overwriting nodata value {self.parameters['nodata']}"
                    f" with user defined value {self.nodata}."
                )
            self.parameters['nodata'] = self.nodata
            self.parameters['profile']['nodata'] = self.nodata

        if self.scale_factor is not None:
            self._scale_parameters()

        # set domain
        width = self.parameters["width"]
        height = self.parameters["height"]
        transform = self.parameters["transform"]
        self.dimensionality = 3
        self.domain_dimensions = np.array([width, height, 1], dtype=np.int32)

        rast_left = np.concatenate([transform * (0, 0), [0]])
        rast_right = np.concatenate([transform * (width, height), [1]])
        # save dimensions that need to be flipped
        self._flip_axes = np.where(rast_left > rast_right)[0]
        self.domain_left_edge = self.arr(
            np.min([rast_left, rast_right], axis=0),
            self.parameters["units"]
        )
        self.domain_right_edge = self.arr(
            np.max([rast_left, rast_right], axis=0),
            self.parameters["units"]
        )
        self.resolution = self.arr(
            self.parameters["res"],
            self.parameters["units"]
        )

    def _parse_resample_method(self, method_key):

        methods = {
            "average": 5,
            "bilinear": 1,
            "cubic": 2,
            "cubic_spline": 3,
            "gauss": 7,
            "lanczos": 4,
            "max": 8,
            "med": 10,
            "min": 9,
            "mode": 6,
            "nearest": 0,
            "q1": 11,
            "q3": 12,
            "rms": 14,
            "sum": 13
        }
        if isinstance(method_key, warp.Resampling):
            method = method_key
        elif method_key in list(methods.values()):
            method = warp.Resampling(method_key)
        elif method_key in list(methods.keys()):
            method = warp.Resampling(methods[method_key])
        else:
            mylog.warning("Resampling method not recognised.")
            method = warp.Resampling.nearest
        method_label = str(method).split('.')[-1]
        mylog.info(f"Resampling using '{method_label}' method.")
        return method

    def _scale_parameters(self):
        """Update transform and other parameters to take any scale_factor into account."""
        transform = self.parameters['transform']
        width = int(self.parameters['width'] * self.scale_factor)
        height = int(self.parameters['height'] * self.scale_factor)
        # scale in two dimensions separately
        scale = (
                self.parameters['width'] / width,
                self.parameters['height'] / height
        )
        mylog.info(f"Scaling dimensions: width by {1/scale[0]} and height by {1/scale[1]}.")
        self.parameters['width'] = width
        self.parameters['height'] = height
        self.parameters['transform'] = transform * transform.scale(*scale)
        self.parameters['res'] = (
            self.parameters['res'][0] * scale[0],
            self.parameters['res'][1] * scale[1]
        )
        self.parameters['profile'].update({
            "transform": self.parameters['transform'],
            "width": width,
            "height": height
        })
        

    def _setup_classes(self):
        super()._setup_classes()
        self.polygon = functools.partial(YTPolygon, ds=weakref.proxy(self))

    def polygons(self, filenames, **kwargs):
        if kwargs:
            pfunc = functools.partial(YTPolygon, ds=weakref.proxy(self), **kwargs)
        else:
            pfunc = functools.partial(YTPolygon, ds=weakref.proxy(self))
        map_results = map(pfunc, filenames)
        return tuple(map_results)

    def _set_code_unit_attributes(self):
        attrs = (
            "length_unit",
            "mass_unit",
            "time_unit",
            "velocity_unit",
            "magnetic_unit",
        )
        si_units = ("m", "kg", "s", "m/s", "T")
        base_units = np.ones(len(attrs), dtype=np.float64)
        for unit, attr, si_unit in zip(base_units, attrs, si_units):
            setattr(self, attr, self.quan(unit, si_unit))

    def set_units(self):
        super().set_units()
        res = self.parameters["res"]
        for i, ax in enumerate("xy"):
            self.unit_registry.add(f"{ax}pixels", res[i], dimensions.length)

        if res[0] == res[1]:
            self.unit_registry.add("pixels", res[0], dimensions.length)
        else:
            mylog.warn("x and y pixels have different sizes.")

    def __repr__(self):
        fn = self.basename
        for ext in self._valid_extensions:
            if re.search(f"{ext}$", fn, flags=re.IGNORECASE):
                fn = fn[: -len(ext)]
                break
        return fn


    def __str__(self):
        return self.__repr__()

    def _parse_crs(self, crs):
        """Return rasterio CRS object."""
        if not isinstance(crs, CRS):
            if isinstance(crs, int):
                # assume epsg number
                crs = CRS.from_epsg(crs)
            elif isinstance(crs, dict):
                crs = CRS.from_dict(**crs)
            else:
                crs = CRS.from_string(crs)
        return crs

    def _update_transform(self, transform, left_edge, right_edge):
        """
        Create a new rasterio transform given left and right edge coordinates.
        """

        tvals = list(transform[:6])
        for i in range(2):
            if i in self._flip_axes:
                val = right_edge[i].d
            else:
                val = left_edge[i].d
            tvals[3 * i + 2] = val
        return rasterio.Affine(*tvals)

    def circle(self, center, radius):
        """
        Create a circular data container.

        This is a wrapper around the disk data container
        that allows for specifying the center with only x
        and y values.

        Parameters
        ----------
        center : array_like of length 2 or 3
            Center of the circle. If center is of length 2,
            the third dimension is the domain center in the
            z direction. If center is of length 3, center is
            unaltered.
        radius : float, width specifier, or unyt_quantity
            The radius of the circle. If passed a float,
            that will be interpreted in code units. Also
            accepts a (radius, unit) tuple or unyt_quantity
            instance with units attached.

        Examples
        --------
        >>> center = ds.arr([100, 100], "m")
        >>> cir = ds.circle(center, (1, "km"))
        >>> vals = cir["LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B2"]
        """

        cc = validate_coord_array(
            self, center, "center", self.domain_center[2], "code_length"
        )
        normal = [0, 0, 1]
        height = self.domain_width[2] / 2
        return self.disk(cc, normal, radius, height)

    def rectangle(self, left_edge, right_edge, clip=True):
        """
        Create a rectangular data container.

        This is a wrapper around the box data container that allows
        the edges to be specified with only x and y values.

        Takes an array of two or three *left_edge* coordinates and two
        or three *right_edge* coordinates that can be anywhere in the
        domain. If the selected region extends past the edges of the
        domain, no data will be found there, though the object's
        *left_edge* or *right_edge* are not modified.

        Parameters
        ----------
        left_edge : array_like
            The left edge of the region. If array is of length 2,
            the third dimension is the domain left edge in the z
            direction. If array is of length 3, left_edge is
            unaltered.
        right_edge : array_like
            The right edge of the region. If array is of length 2,
            the third dimension is the domain right edge in the z
            direction. If array is of length 3, right_edge is
            unaltered.
        clip : optional, bool
            If True, clip the left and right edges to be contained
            within grid boundaries. If False, an exception will be
            raised if an edge is outside of the domain.
            Default: True.

        Examples
        --------
        >>> left_edge = ds.arr([1, 1], "km")
        >>> right_edge = ds.arr(5, 5], "km")
        >>> rec = ds.rectangle(left_edge, right_edge)
        >>> vals = rec["LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B2"]
        """

        le = validate_coord_array(
            self, left_edge, "left_edge", self.domain_left_edge[2], "code_length"
        )
        re = validate_coord_array(
            self, right_edge, "right_edge", self.domain_right_edge[2], "code_length"
        )

        if clip:
            le.clip(self.domain_left_edge, self.domain_right_edge, out=le)
            re.clip(self.domain_left_edge, self.domain_right_edge, out=re)

        return self.box(le, re)

    def rectangle_from_center(self, center, width, height, clip=True):
        """
        Create a rectangular data container from center, width, height.

        This is a variant of the rectangle data container that takes a
        center, width, and height instead of a left and right corner.

        Parameters
        ----------
        center : array_like of length 2 or 3
            Center of the rectangle. If center is of length 2,
            the third dimension is the domain center in the
            z direction. If center is of length 3, center is
            unaltered.
        width : float, unyt_quantity, or tuple of (float, units)
            Width of the rectangle. If no units given, "code_length"
            is assumed.
        height : float or unyt_quantity
            Height of the rectangle. If no units given, "code_length"
            is assumed.
        clip : optional, bool
            If True, clip the left and right edges to be contained
            within grid boundaries. If False, an exception will be
            raised if an edge is outside of the domain.
            Default: True.

        Examples
        --------
        >>> center = ds.arr([5, 5], "km")
        >>> width = ds.quan(2, "km")
        >>> height = (1, "km")
        >>> rec = ds.rectangle_from_center(center, width, height)
        >>> vals = rec["LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B2"]
        """

        cc = validate_coord_array(
            self, center, "center", self.domain_center[2], "code_length"
        )
        width = validate_quantity(self, width, "code_length")
        height = validate_quantity(self, height, "code_length")
        size = self.arr([width, height])
        left = cc[:2] - size / 2
        right = cc[:2] + size / 2
        return self.rectangle(left, right)

    def plot(self, field, data_source=None, center=None, width=None, height=None):
        """
        Create a spatial plot of a given field.

        Optionally, a center, width, height, or data_source
        can be provided to restrict the bounds or data plotted.

        Parameters
        ----------
        field : tuple of (field type, field name)
            The field to be plotted.
        data_source : optional, data container
            If given, only data within the container will be
            plotted. If center, width, or height not given,
            bounds will be determined from the data_source.
        center : optional, array_like
            Center of the plotted region. If not given, either
            the center of the domain or data_source will be used.
        width : optional, float, unyt_quantity, or tuple of (float, units)
            Width of the plotted region. If no units given,
            "code_length" is assumed. If not given, either
            the width of the domain or data_source will be used.
        height : optional, float, unyt_quantity, or tuple of (float, units)
            Height of the plotted region. If no units given,
            "code_length" is assumed. If not given, either
            the height of the domain or data_source will be used.

        Examples
        --------
        >>> import yt
        >>> ds = yt.load(...)
        >>> p = ds.plot(("LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B2"),
        ...             width=(1, 'km'))
        >>> p.save()

        >>> rec = ds.rectangle_from_center(center, width, height)
        >>> p = ds.plot(("LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B2"),
        ...             data_source=rec)
        >>> p.save()
        """

        if center is not None:
            center = validate_coord_array(
                self, center, "center", self.domain_center[2], "code_length"
            )
        if width is not None:
            width = validate_quantity(self, width, "code_length")
        if height is not None:
            height = validate_quantity(self, height, "code_length")

        if data_source is None:
            if width is None:
                data_source = self.all_data()
            else:
                if center is None:
                    center = self.domain_center
                if height is None:
                    height = width
                data_source = self.rectangle_from_center(center, width, height)
                center = data_source.center

        # construct a window data set using bounds from data_source
        my_source = data_source
        while hasattr(my_source, "base_object"):
            my_source = my_source.base_object
        my_selector = my_source.selector

        wleft, wright = self.data._get_selection_window(my_selector)
        w = self.data._get_trimmed_rasterio_window(
            my_selector, self.parameters['crs'], self.parameters['transform']
        )
        with log_level(40):
            wds = GeoRasterWindowDataset(self, wleft, wright, w)

        w_data_source = wds._get_window_container(data_source)

        if center is None:
            center = wds.domain_center
        if width is None:
            width = wds.domain_width[0]
        if height is None:
            height = wds.domain_width[1]

        plot_width = max(width, height)

        p = SlicePlot(
            wds, "z", field, data_source=w_data_source, center=center, width=plot_width
        )
        # make this an actual pointer so wds doesn't go out of scope
        p.ds = wds

        return p

    @classmethod
    def _is_valid(self, *args, **kwargs):
        for fn in args:
            valid = False
            for ext in self._valid_extensions:
                if re.search(f"{ext}$", fn, flags=re.IGNORECASE):
                    valid = True
                    break

            if not valid:
                return False

            with rasterio.open(fn, "r") as f:
                driver_type = f.meta["driver"]
                if driver_type not in self._driver_types:
                    return False

        return True


class GeoRasterWindowDataset(GeoRasterDataset):
    """
    Class used for plotting a window of data from GeoRasterDataset.
    """

    @classmethod
    def _is_valid(self, *args, **kwargs):
        return False

    def __init__(self, parent_ds, left_edge, right_edge, window):
        self._parent_ds = parent_ds
        self._index_class = parent_ds._index_class
        self._dataset_type = parent_ds._dataset_type
        self.domain_left_edge = parent_ds.arr(left_edge, parent_ds.parameters["units"])
        self.domain_right_edge = parent_ds.arr(right_edge, parent_ds.parameters["units"])
        self.domain_dimensions = np.array(
            [window.width, window.height, parent_ds.domain_dimensions[2]],
            dtype=np.int32
        )

        super().__init__(parent_ds.parameter_filename, field_map=parent_ds.field_map)

        for field in parent_ds._added_fields:
            self.add_field(*field["args"], **field["kwargs"])

    def _parse_parameter_file(self):
        inh_attrs = (
            "current_time",
            "dimensionality",
            "num_particles",
            "_flip_axes",
            "resolution",
            "filename_list",
        )
        for attr in inh_attrs:
            setattr(self, attr, getattr(self._parent_ds, attr, None))

        self.parameters = self._parent_ds.parameters.copy()

    def _get_window_container(self, dobj):
        """
        Generate a matching data container belonging to the window dataset.
        """

        con_args = {arg: getattr(dobj, arg) for arg in dobj._con_args}
        # if object has a base object (like a cut_region), get that first
        if "base_object" in con_args:
            base_object = self._get_window_container(con_args["base_object"])
            con_args["base_object"] = base_object

        type_name = dobj._type_name
        wobj = getattr(self, type_name)(*list(con_args.values()))
        wobj.ds = self
        return wobj
