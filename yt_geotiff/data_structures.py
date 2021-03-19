import glob
import numpy as np
import os
import rasterio
from rasterio.windows import from_bounds
import stat

from unyt import dimensions

from yt.data_objects.static_output import \
    Dataset
from yt.data_objects.selection_objects.data_selection_objects import \
    YTSelectionContainer
from yt.funcs import mylog
from yt.geometry.selection_routines import \
    GridSelector, \
    RegionSelector, \
    SphereSelector
from yt.frontends.ytdata.data_structures import \
    YTGridHierarchy, \
    YTGrid
from yt.utilities.parallel_tools.parallel_analysis_interface import \
    parallel_root_only
from yt.visualization.api import SlicePlot

from .fields import \
    GeoTiffFieldInfo
from .utilities import \
    left_aligned_coord_cal, \
    save_dataset_as_geotiff, \
    parse_awslandsat_metafile, \
    validate_coord_array, \
    validate_quantity, \
    log_level


class GeoTiffWindowGrid(YTGrid):
    def __init__(self, gridobj, left_edge, right_edge):

        YTSelectionContainer.__init__(self, gridobj._index.dataset, None)

        self.id = gridobj.id
        self._child_mask = gridobj._child_indices =\
            gridobj._child_index_mask = None
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

        self.LeftEdge = self.ds.arr(left_edge, 'm')
        self.RightEdge = self.ds.arr(right_edge, 'm')
        # Make sure z dimension edges are the same as parent grid.
        self.LeftEdge[2] = gridobj.LeftEdge[2]
        self.RightEdge[2] = gridobj.RightEdge[2]
        self.ActiveDimensions =\
            (gridobj.ActiveDimensions *
                (self.RightEdge - self.LeftEdge) /
                (gridobj.RightEdge - gridobj.LeftEdge)).d.astype(np.int32)
        # Inherit dx values from parent.
        self.dds = gridobj.dds

    def __repr__(self):
        ad = self.ActiveDimensions
        return f"GeoTiffWindowGrid ({ad[0]}x{ad[1]})"


class GeoTiffGrid(YTGrid):
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

    def _get_selector_mask(self, selector):
        if isinstance(selector, GridSelector):
            return super()._get_selector_mask(selector)
        wgrid = self._get_window_grid(selector)
        rvalue = wgrid._get_selector_mask(selector)
        return rvalue

    def _get_window_grid(self, selector):
        """
        Return a GeoTiffWindowGrid for a given selector.
        """

        if self._last_wgrid and hash(selector) == self._last_wgrid_id:
            return self._last_wgrid

        left_edge, right_edge = self._get_selection_window(selector)
        wgrid = GeoTiffWindowGrid(self, left_edge, right_edge)
        self._last_wgrid = wgrid
        self._last_wgrid_id = hash(selector)
        return wgrid

    def _get_selection_window(self, selector):
        """
        Calculate bounding box for selectors.
        """

        dle = self.ds.domain_left_edge.d
        dre = self.ds.domain_right_edge.d

        if isinstance(selector, SphereSelector):
            left_edge = np.array(selector.center)
            left_edge[:2] -= selector.radius
            left_edge[2] = dle[2]

            right_edge = np.asarray(selector.center)
            right_edge[:2] += selector.radius
            right_edge[2] = dre[2]

        elif isinstance(selector, RegionSelector):
            left_edge = np.array(selector.left_edge)
            right_edge = np.array(selector.right_edge)

        else:
            left_edge = dle
            right_edge = dre

        left_edge.clip(min=dle, max=dre, out=left_edge)
        right_edge.clip(min=dle, max=dre, out=right_edge)
        return left_edge, right_edge

    def _get_rasterio_window(self, selector, transform):
        """
        Calculate position, width, and height for a rasterio window read.
        """

        left_edge, right_edge = self._get_selection_window(selector)
        window = from_bounds(left_edge[0], left_edge[1],
                             right_edge[0], right_edge[1],
                             transform)
        return window

    def __repr__(self):
        ad = self.ActiveDimensions
        return f"GeoTiffGrid ({ad[0]}x{ad[1]})"


class GeoTiffHierarchy(YTGridHierarchy):
    grid = GeoTiffGrid

    def _detect_output_fields(self):
        self.field_list = []
        self.ds.field_units = self.ds.field_units or {}
        with rasterio.open(self.ds.parameter_filename, "r") as f:
            group = 'bands'
            for _i in range(1, f.count + 1):
                field_name = (group, str(_i))
                self.field_list.append(field_name)
                self.ds.field_units[field_name] = ""

    def _count_grids(self):
        self.num_grids = 1


class JPEG2000Hierarchy(GeoTiffHierarchy):
    grid = GeoTiffGrid   

    def _detect_output_fields(self):
        # check data dir of the given jp2 file and grab all similarly named files.

        # List of band files in s2 directory
        s2_band_file_list = [os.path.basename(x) \
         for x in glob.glob(self.ds.directory+'/*_***_***.jp2')]

        # Follow example for GeoTiffHierarchy to populate the field list.
        self.field_list = []
        self.ds.field_units = self.ds.field_units or {}

        # Filename dictionary
        self.ds._field_filename = {}

        # Extract s2 band name from file name.
        def get_band_name(band_file_list):
            band_file = band_file_list.split("_")
            return band_file

        band_names = [list(b) for b in zip(*map(get_band_name, s2_band_file_list))][2]

        for _i in range(len(s2_band_file_list)):
            filename = os.path.join(self.ds.directory,s2_band_file_list[_i])
            with rasterio.open(os.path.join(filename), "r") as f:
                group = 'bands'
                field_name = (group, band_names[_i] +'_'+str(round(f.res[0])))
                self.field_list.append(field_name)
                self.ds.field_units[field_name] = ""
                self.ds._field_filename.update({field_name[1]: {'filename': filename, 'resolution': f.res[0]}})


class GeoTiffDataset(Dataset):
    """Dataset for saved covering grids, arbitrary grids, and FRBs."""
    _index_class = GeoTiffHierarchy
    _field_info_class = GeoTiffFieldInfo
    _dataset_type = 'geotiff'
    _valid_extensions = ('.tif', '.tiff')
    _driver_type = "GTiff"
    geometry = "cartesian"
    default_fluid_type = "bands"
    fluid_types = ("bands", "index", "sentinel2")
    _periodicity = np.zeros(3, dtype=bool)
    cosmological_simulation = False
    _con_attrs = ()

    def __init__(self, filename, field_map=None):
        self.field_map = field_map
        super(GeoTiffDataset, self).__init__(
            filename, self._dataset_type, unit_system="mks")
        self.data = self.index.grids[0]

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
            self.parameters['res'] = f.res
        self.current_time = 0

        width = self.parameters['width']
        height = self.parameters['height']
        transform = self.parameters['transform']
        self.dimensionality = 3
        self.domain_dimensions = np.array([height, width, 1], dtype=np.int32)

        rast_left = np.concatenate([transform * (0, 0), [0]])
        rast_right = np.concatenate([transform * (width, height), [1]])
        # save dimensions that need to be flipped
        self._flip_axes = np.where(rast_left > rast_right)[0]
        self.domain_left_edge =\
            self.arr(np.min([rast_left, rast_right], axis=0), 'm')
        self.domain_right_edge =\
            self.arr(np.max([rast_left, rast_right], axis=0), 'm')
        self.resolution = self.arr(self.parameters['res'], 'm')

    def _set_code_unit_attributes(self):
        attrs = ('length_unit', 'mass_unit', 'time_unit',
                 'velocity_unit', 'magnetic_unit')
        si_units = ('m', 'kg', 's', 'm/s', 'T')
        base_units = np.ones(len(attrs), dtype=np.float64)
        for unit, attr, si_unit in zip(base_units, attrs, si_units):
            setattr(self, attr, self.quan(unit, si_unit))

    def set_units(self):
        super().set_units()
        res = self.parameters['res']
        for i, ax in enumerate('xy'):
            self.unit_registry.add(f"{ax}pixels", res[i], dimensions.length)

        if res[0] == res[1]:
            self.unit_registry.add("pixels", res[0], dimensions.length)
        else:
            mylog.warn("x and y pixels have different sizes.")

    def save_as(self, filename):
        # TODO: generalize this to save any dataset type as GeoTiff.
        return save_dataset_as_geotiff(self, filename)

    def __repr__(self):
        fn = self.basename
        for ext in self._valid_extensions:
            if fn.endswith(ext) or fn.endswith(ext.upper()):
                fn = fn[:-len(ext)]
                break
        return fn

    def circle(self, center, radius):
        """
        Create a circular data container.

        This is a wrapper around the sphere data container
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
            The radius of the sphere. If passed a float,
            that will be interpreted in code units. Also
            accepts a (radius, unit) tuple or unyt_quantity
            instance with units attached.

        Examples
        --------
        >>> center = ds.arr([100, 100], 'm')
        >>> cir = ds.circle(center, (1, 'km'))
        >>> vals = cir[("Bands", "1")]
        """

        cc = validate_coord_array(
            self, center, "center",
            self.domain_center[2], "code_length")
        return self.sphere(cc, radius)

    def rectangle(self, left_edge, right_edge):
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

        Examples
        --------
        >>> left_edge = ds.arr([1, 1], 'km')
        >>> right_edge = ds.arr(5, 5], 'km')
        >>> rec = ds.rectangle(left_edge, right_edge)
        >>> vals = rec[("Bands", "1")]
        """

        le = validate_coord_array(
            self, left_edge, "left_edge",
            self.domain_left_edge[2], "code_length")
        re = validate_coord_array(
            self, right_edge, "right_edge",
            self.domain_right_edge[2], "code_length")
        return self.box(le, re)

    def rectangle_from_center(self, center, width, height):
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

        Examples
        --------
        >>> center = ds.arr([5, 5], 'km')
        >>> width = ds.quan(2, 'km')
        >>> height = (1, 'km')
        >>> rec = ds.rectangle_from_center(center, width, height)
        >>> vals = rec[("Bands", "1")]
        """

        cc = validate_coord_array(
            self, center, "center",
            self.domain_center[2], "code_length")
        width = validate_quantity(self, width, "code_length")
        height = validate_quantity(self, height, "code_length")
        size = self.arr([width, height])
        left = cc[:2] - size / 2
        right = cc[:2] + size / 2
        return self.rectangle(left, right)

    def plot(self, field, data_source=None,
             center=None, width=None, height=None):
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
        >>> p = ds.plot(('bands', '1'), width=(1, 'km'))
        >>> p.save()

        >>> rec = ds.rectangle_from_center(center, width, height)
        >>> p = ds.plot(('bands', '1'), data_source=rec)
        >>> p.save()
        """
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
                data_source = self.rectangle_from_center(
                    center, width, height)
                center = data_source.center

        # construct a window data set
        wleft, wright = self.data._get_selection_window(data_source.selector)
        with log_level(40):
            wds = GeoTiffWindowDataset(self, wleft, wright)

        # construct shadow data source using window dataset
        con_args = [getattr(data_source, arg) for arg in data_source._con_args]
        type_name = data_source._type_name
        w_data_source = getattr(wds, type_name)(*con_args)

        if center is None:
            center = wds.domain_center
        if width is None:
            width = wds.domain_width[0]
        if height is None:
            height = wds.domain_width[1]

        plot_width = max(width, height)

        p = SlicePlot(wds, 'z', field, data_source=w_data_source,
                      center=center, width=plot_width)
        # make this an actual pointer so wds doesn't go out of scope
        p.ds = wds

        return p

    @classmethod
    def _is_valid(self, *args, **kwargs):
        fn = args[0]
        valid = False
        for ext in self._valid_extensions:
            if fn.endswith(ext) or fn.endswith(ext.upper()):
                valid = True
                break
        if not valid:
            return False

        with rasterio.open(fn, "r") as f:
            driver_type = f.meta["driver"]
            if driver_type == self._driver_type:
                return True
        return False

class JPEG2000Dataset(GeoTiffDataset):
    _index_class = JPEG2000Hierarchy
    _valid_extensions = ('.jp2')
    _driver_type = "JP2OpenJPEG"
    _dataset_type = "JPEG2000"

class GeoTiffWindowDataset(GeoTiffDataset):
    """
    Class used for plotting a window of data from GeoTiffDataset.
    """

    @classmethod
    def _is_valid(self, *args, **kwargs):
        return False

    def __init__(self, parent_ds, left_edge, right_edge):
        self._parent_ds = parent_ds
        self._index_class=parent_ds._index_class
        self._dataset_type=parent_ds._dataset_type
        self.domain_left_edge = parent_ds.arr(left_edge, 'm')
        self.domain_right_edge = parent_ds.arr(right_edge, 'm')
        self.domain_dimensions = \
            (parent_ds.domain_dimensions *
                (self.domain_right_edge - self.domain_left_edge) /
                (parent_ds.domain_right_edge -
                    parent_ds.domain_left_edge)).d.astype(np.int32)

        super().__init__(parent_ds.parameter_filename, parent_ds.field_map)

    def _parse_parameter_file(self):
        inh_attrs = ("current_time", "dimensionality",
                     "num_particles", "_flip_axes",
                     "resolution")
        for attr in inh_attrs:
            setattr(self, attr, getattr(self._parent_ds, attr))

        self.parameters = self._parent_ds.parameters.copy()


class LandSatGeoTiffHierarchy(GeoTiffHierarchy):
    def _detect_output_fields(self):
        self.field_list = []
        self.ds.field_units = self.ds.field_units or {}

        # get list of filekeys
        filekeys = [s for s in self.ds.parameters.keys()
                    if 'FILE_NAME_BAND_' in s]
        files = [self.ds.data_dir + self.ds.parameters[filekey]
                 for filekey in filekeys]

        group = 'bands'
        for file in files:
            band = file.split(os.path.sep)[-1].split('.')[0].split('B')[1]
            field_name = (group, band)
            self.field_list.append(field_name)
            self.ds.field_units[field_name] = ""


class LandSatGeoTiffDataSet(GeoTiffDataset):
    """"""
    _index_class = LandSatGeoTiffHierarchy

    def _parse_parameter_file(self):
        self.current_time = 0.
        self.unique_identifier = \
            int(os.stat(self.parameter_filename)[stat.ST_CTIME])

        # self.parameter_filename is the dir str
        if self.parameter_filename[-1] == '/':
            self.data_dir = self.parameter_filename
            self.mtlfile = self.data_dir +\
                self.parameter_filename[:-1]\
                .split(os.path.sep)[-1] + '_MTL.txt'
            self.angfile = self.data_dir + self.parameter_filename[:-1]\
                          .split(os.path.sep)[-1] + '_ANG.txt'
        else:
            self.data_dir = self.parameter_filename + '/'
            self.mtlfile = self.data_dir + self.parameter_filename.split(os.path.sep)[-1] + '_MTL.txt'
            self.angfile = self.data_dir + self.parameter_filename .split(os.path.sep)[-1]+ '_ANG.txt'
        # load metadata files
        self.parameters.update(parse_awslandsat_metafile(self.angfile))
        self.parameters.update(parse_awslandsat_metafile(self.mtlfile))

        # get list of filekeys
        filekeys = [s for s in self.parameters.keys() if 'FILE_NAME_BAND_' in s]
        files = [self.data_dir + self.parameters[filekey] for filekey in filekeys]
        self.parameters['count'] = len(filekeys)
        # take the parameters displayed in the filename
        self._parse_landsat_filename_data(self.parameter_filename.split(os.path.sep)[-1])

        for filename in files:
            band = filename.split(os.path.sep)[-1].split('.')[0].split('B')[1]
            # filename = self.parameters[band]
            with rasterio.open(filename, "r") as f:
                for key in f.meta.keys():
                    # skip key if already defined as a parameter
                    if key in self.parameters.keys(): continue
                    v = f.meta[key]
                    # if key == "con_args":
                    #     v = v.astype("str")
                    self.parameters[(band, key)] = v
                self._with_parameter_file_open(f)
                # self.parameters['transform'] = f.transform

            if band == '1':
                self.domain_dimensions = np.array([self.parameters[(band, 'height')],
                                                   self.parameters[(band, 'width')],
                                                   1], dtype=np.int32)
                self.dimensionality = 3
                rightedge_xy = left_aligned_coord_cal(self.domain_dimensions[0],
                                                      self.domain_dimensions[1],
                                                      self.parameters[(band, 'transform')])
                
                self.domain_left_edge = self.arr(np.zeros(self.dimensionality,
                                                           dtype=np.float64), 'm')
                self.domain_right_edge = self.arr([rightedge_xy[0],
                                                  rightedge_xy[1],
                                                  1], 'm', dtype=np.float64)

    def _parse_landsat_filename_data(self, filename):
        """
        "LXSS_LLLL_PPPRRR_YYYYMMDD_yyyymmdd_CC_TX"
        L = Landsat
        X = Sensor ("C"=OLI/TIRS combined,
                    "O"=OLI-only, "T"=TIRS-only, 
                    E"=ETM+, "T"="TM, "M"=MSS)
        SS = Satellite ("07"=Landsat 7, "08"=Landsat 8)
        LLLL = Processing correction level (L1TP/L1GT/L1GS)
        PPP = WRS path
        RRR = WRS row
        YYYYMMDD = Acquisition year, month, day
        yyyymmdd - Processing year, month, day
        CC = Collection number (01, 02, …)
        TX = Collection category ("RT"=Real-Time, "T1"=Tier 1,
                                  "T2"=Tier 2)
        """
        sensor = {"C": "OLI&TIRS combined",
                  "O": "OLI-only",
                  # "T": "TIRS-only", commenting out to fix flake8 error
                  "E": "ETM+", "T": "TM", "M": "MSS"}
        satellite = {"07": "Landsat 7",
                     "08": "Landsat 8"}
        category = {"RT": "Real-Time", "T1": "Tier 1",
                    "T2": "Tier 2"}

        self.parameters['sensor'] = sensor[filename[1]]
        self.parameters['satellite'] = satellite[filename[2:4]]
        self.parameters['level'] = filename[5:9]        
        self.parameters['wrs'] = {'path': filename[10:13],
                                  'row': filename[13:16]}
        self.parameters['acquisition_time'] = {'year': filename[17:21],
                                               'month': filename[21:23],
                                               'day': filename[23:25]}
        self.parameters['processing_time'] = {'year': filename[26:30],
                                              'month': filename[30:32],
                                              'day': filename[32:34]}
        self.parameters['collection'] = {
                                'number': filename[35:37],
                                'category': category[filename[38:40]]}

    @classmethod
    def _is_valid(self, *args, **kwargs):
        if not os.path.isdir(args[0]): return False
        if len(glob.glob(args[0]+'/L*_ANG.txt')) != 1 and\
           len(glob.glob(args[0]+'/L*_MTL.txt')) != 1: return False
        try:
            file = glob.glob(args[0]+'/*.TIF')[0] # open the first file
            with rasterio.open(file, "r") as f:
                # data_type = parse_gtif_attr(f, "dtype")
                driver_type = f.meta["driver"]
                # if data_type == "uint16":
                #     return True
                if driver_type == "GTiff":
                    return True
        except:
            pass
        return False
